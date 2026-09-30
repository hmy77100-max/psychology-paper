"""Read-only checks and proposed transitions for author-led revision.

These checks bind real files, not caller-supplied 'valid' flags. They do not
judge scientific truth, infer approval from words, or write manuscript/state.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

from project_state import extract_json_frontmatter, evaluate_rules, load_state_rules
from validate_project import validate_state, RULE_PATH
from workflow_guards import calculate_body_budget

LABELS = {
    "chinese": ("中文原文", "修改后中文", "必要说明"),
    "english": ("Original English", "Revised English", "Chinese Translation"),
    "chinese-to-english": ("中文原文", "修改后英文", "中文回译"),
}
LATE = {"abstract", "keywords", "title"}
ACCEPTED = {"APPROVED", "RETAINED"}
UNKNOWN = {"", "unknown", "unresolved", "unset", "待确认"}


def resolve(raw, root):
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("A declared file path is required")
    p = Path(raw).expanduser()
    return (p if p.is_absolute() else root / p).resolve()


def snapshot(ref, root):
    if not isinstance(ref, dict):
        raise ValueError("A file reference with path and sha256 is required")
    data = resolve(ref.get("path"), root).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if ref.get("sha256") != digest:
        raise ValueError("File version changed: " + str(ref.get("path")))
    return data, digest


def text_of(data):
    return data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def count_text(text, unit):
    if unit == "words":
        return len(text.split())
    if unit == "characters":
        return sum(not c.isspace() for c in text)
    raise ValueError("Supported units are words or characters; record the counting convention")


def candidate_parts(record, root):
    data, _ = snapshot(record["artifact"], root)
    text = text_of(data).strip()
    labels = LABELS.get(record.get("mode"))
    if labels is None:
        raise ValueError("Unsupported candidate language mode")
    # Plain TXT headings are stable and also let authors edit with any editor.
    all_labels = set(x for group in LABELS.values() for x in group)
    heading = re.compile(r"^(?:#{1,3} )?(" + "|".join(re.escape(x) for x in sorted(all_labels)) + r")\s*$", re.M)
    matches = list(heading.finditer(text))
    if tuple(m.group(1) for m in matches) != labels:
        raise ValueError("Candidate must contain the three required headings once, in order")
    parts = [text[m.end():matches[i + 1].start() if i < 2 else len(text)].strip()
             for i, m in enumerate(matches)]
    if any(not p for p in parts):
        raise ValueError("All three candidate parts must be non-empty")
    return parts


def unit_source(record, root):
    _, source_hash = snapshot(record["source"], root)
    extraction = record["extraction"]
    data, _ = snapshot(extraction, root)
    if extraction.get("source_sha256") != source_hash:
        raise ValueError("Extraction is not bound to the current authoritative source")
    text = text_of(data)
    unit = record["unit"]
    if not all(isinstance(unit.get(k), str) and unit[k].strip() for k in ("id", "section", "function", "closure")):
        raise ValueError("Logical unit needs id, section, function and closure rationale")
    spans = unit.get("spans")
    if not isinstance(spans, list) or not spans:
        raise ValueError("Exact source spans are required")
    previous = 0
    parts = []
    for span in spans:
        if (not isinstance(span, list) or len(span) != 2 or
                any(type(n) is not int for n in span)):
            raise ValueError("Source spans require two integer offsets")
        start, end = span
        if not 0 <= previous <= start < end <= len(text):
            raise ValueError("Source spans must be ordered, non-overlapping and within extraction")
        previous = end
        parts.append(text[start:end])
    return "\n\n".join(parts).strip()


def validate_candidate(record, root):
    try:
        source = unit_source(record, root)
        parts = candidate_parts(record, root)
        if parts[0] != source:
            raise ValueError("Original passage does not exactly match the full logical unit")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
        return [str(exc)]
    return []


def load_project(root):
    return extract_json_frontmatter(root / ".psychology-paper" / "PROJECT.md")[0]


def preflight(root):
    """Read standard state, approved profile, authority and counted baseline."""
    errors = []
    try:
        state = load_project(root)
        errors.extend(validate_state(state, root))
        errors.extend(v.message for v in evaluate_rules(state, load_state_rules(RULE_PATH),
                      component="project-validator", source_path=RULE_PATH))
        flow = state.get("revision", {})
        units = flow.get("units", [])
        if not isinstance(units, list) or not units or any(not isinstance(u, dict) or not u.get("id") or not u.get("section") for u in units):
            errors.append("A non-empty logical-unit plan with IDs and sections is required")
        elif len({u["id"] for u in units}) != len(units):
            errors.append("Logical-unit IDs must be unique")
        if type(flow.get("content_revision")) is not int or flow["content_revision"] < 0:
            errors.append("A non-negative content revision is required")
        source = {"path": state["authoritative_manuscript"], "sha256": state.get("source_sha256")}
        _, digest = snapshot(source, root)
        journal = state.get("journal", {})
        if journal.get("status") != "USER_CONFIRMED":
            errors.append("Target journal is not confirmed")
        profile, _ = extract_json_frontmatter(resolve(state["optional_state_files"].get("journal_profile"), root))
        if profile.get("status") != "approved" or profile.get("journal_name") != journal.get("name"):
            errors.append("An approved matching journal profile is required")
        budget = state["body_budget"]
        rule = profile.get("body_budget", {})
        for key in ("limit", "unit", "counting_scope"):
            value = budget.get(key)
            if value != rule.get(key) or str(value).lower() in UNKNOWN or value is None:
                errors.append("Journal budget mismatch or unknown: " + key)
        if not rule.get("source_url") or not rule.get("verified_on"):
            errors.append("Journal budget needs its source and verification date")
        baseline = budget.get("baseline", {})
        data, _ = snapshot(baseline, root)
        if baseline.get("source_sha256") != digest or baseline.get("adoption_status") != "USER_ADOPTED":
            errors.append("Counted baseline must be adopted and bound to the authoritative source")
        if budget.get("baseline_status") != "CURRENT":
            errors.append("Refresh the approved mainline baseline before another candidate")
        if count_text(text_of(data), budget["unit"]) != budget.get("current"):
            errors.append("Current count does not match the actual counted baseline")
        framing = state.get("framing", {})
        if framing.get("status") != "AUTHOR_CONFIRMED" or not framing.get("statement") or not framing.get("author_response"):
            errors.append("Author's working contribution/outline direction is not confirmed")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
        errors.append(str(exc))
    return errors


def check_stage(state, section, explicit_override=""):
    if explicit_override:
        return []  # exact author instruction is supplied, never inferred from page order
    if section not in {"abstract", "keywords"}:
        return []
    flow = state.get("revision", {})
    units = flow.get("units", [])
    body = [u for u in units if u.get("section") not in LATE]
    current = state.get("source_sha256")
    if not body or any(u.get("status") not in ACCEPTED or u.get("source_sha256") != current for u in body):
        return ["Complete and obtain author decisions for all body logical units first"]
    if section == "keywords":
        abstracts = [u for u in units if u.get("section") == "abstract"]
        if not abstracts or any(u.get("status") not in ACCEPTED or
            u.get("body_revision") != flow.get("content_revision") or u.get("source_sha256") != current for u in abstracts):
            return ["Keywords require an abstract synchronized to the current approved body"]
    return []


def propose_decision(root, record, intent, utterance, explicit_override=""):
    """The model maps unrestricted author language; this function checks scope."""
    if not isinstance(utterance, str) or not utterance.strip():
        return {"status": "INVALID", "errors": ["Author's actual response is required"]}
    if intent not in {"APPROVE_CURRENT", "RETAIN_CURRENT", "PARTIAL", "REJECT", "DEFER", "ADVANCE_ONLY"}:
        return {"status": "INVALID", "errors": ["Map the author's meaning to a supported intent"]}
    try:
        state = load_project(root)
        if intent == "ADVANCE_ONLY":
            errors = validate_candidate(record, root)
            if errors:
                return {"status": "INVALID_CANDIDATE", "errors": errors}
        if intent in {"PARTIAL", "REJECT", "DEFER", "ADVANCE_ONLY"}:
            return {"status": "REVISION_REQUIRED" if intent == "PARTIAL" else intent, "errors": [], "proposed_state": state}
        errors = validate_candidate(record, root)
        if errors:
            return {"status": "INVALID_CANDIDATE", "errors": errors}
        units = state.get("revision", {}).get("units", [])
        matches = [u for u in units if u.get("id") == record["unit"]["id"]]
        if len(matches) != 1:
            raise ValueError("Candidate must name exactly one planned logical unit")
        target = matches[0]
        if any(target.get(k) != record["unit"].get(k) for k in ("section", "function", "closure", "spans")):
            raise ValueError("Candidate range or function differs from the planned unit")
        artifact_hash = record["artifact"]["sha256"]
        intended_status = "APPROVED" if intent == "APPROVE_CURRENT" else "RETAINED"
        same_authority = record["source"]["sha256"] == state.get("source_sha256") and resolve(record["source"]["path"], root) == resolve(state["authoritative_manuscript"], root)
        if same_authority and target.get("approved_artifact_sha256") == artifact_hash and target.get("source_sha256") == record["source"]["sha256"] and target.get("status") == intended_status:
            return {"status": "ALREADY_APPROVED", "errors": [], "proposed_state": state}
        errors = preflight(root) + check_stage(state, target["section"], explicit_override)
        if not same_authority:
            errors.append("Candidate source differs from project authority")
        if errors:
            return {"status": "PREFLIGHT_REQUIRED", "errors": errors}
        proposed = copy.deepcopy(state)
        target = next(u for u in proposed["revision"]["units"] if u["id"] == target["id"])
        source, revised, _ = candidate_parts(record, root)
        budget = proposed["body_budget"]
        # Count only text declared to be inside the confirmed journal scope.
        counted = target.get("counted_in_budget", target["section"] not in LATE)
        if counted and record["extraction"]["sha256"] != budget["baseline"]["sha256"]:
            return {"status": "PREFLIGHT_REQUIRED", "errors": ["Counted candidate must be extracted from the current adopted baseline"]}
        if intent == "APPROVE_CURRENT" and counted:
            projection = calculate_body_budget(limit=budget["limit"], current=budget["current"],
                replaced=count_text(source, budget["unit"]), candidate=count_text(revised, budget["unit"]), unit=budget["unit"])
            if not projection.candidate_allowed:
                return {"status": "COMPRESSION_REQUIRED", "errors": ["Candidate expands an over-limit manuscript"]}
            budget.update(current=projection.projected, status=projection.status, baseline_status="REFRESH_REQUIRED")
        target.update(status="APPROVED" if intent == "APPROVE_CURRENT" else "RETAINED",
            source_sha256=state["source_sha256"], approved_artifact_sha256=artifact_hash,
            author_response=utterance, author_stage_request=explicit_override,
            body_revision=proposed["revision"]["content_revision"])
        if intent == "APPROVE_CURRENT" and target["section"] not in LATE and source != revised:
            proposed["revision"]["content_revision"] += 1
            for unit in proposed["revision"]["units"]:
                if unit["section"] in {"abstract", "keywords"}:
                    unit.update(status="PENDING", body_revision=None)
        if intent == "APPROVE_CURRENT" and target["section"] == "abstract" and source != revised:
            for unit in proposed["revision"]["units"]:
                if unit["section"] == "keywords":
                    unit.update(status="PENDING", body_revision=None)
        return {"status": "PROPOSED", "errors": [], "proposed_state": proposed,
                "write_allowed": False, "scientific_verification": False}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
        return {"status": "INVALID", "errors": [str(exc)]}


def sync_status(record, root):
    result = {"write_allowed": False, "translation_verified": False}
    if record.get("authorized") is not True:
        return {**result, "status": "AUTHORIZATION_REQUIRED"}
    try:
        _, digest = snapshot(record["chinese"], root)
        if not record.get("unit_id") or record.get("chinese_status") not in {"CANDIDATE", "APPROVED"}:
            raise ValueError("Corresponding logical unit and Chinese adoption state are required")
        english = record.get("english")
        if english is not None:
            snapshot(english, root)
        return {**result, "status": "CURRENT" if english is not None and digest == record.get("english_based_on_sha256") else "UPDATE_CANDIDATE",
                "chinese_sha256": digest, "candidate_status": "CANDIDATE"}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {**result, "status": "UNRESOLVED", "errors": [str(exc)]}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["candidate", "preflight", "stage", "decision", "sync"])
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--record", help="JSON path or - for stdin; read-only")
    parser.add_argument("--intent")
    parser.add_argument("--section")
    parser.add_argument("--author-response")
    parser.add_argument("--explicit-stage-request", default="")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    try:
        if args.command == "preflight":
            result = {"errors": preflight(root)}
        elif args.command == "stage":
            if not args.section:
                raise ValueError("--section is required")
            result = {"errors": preflight(root) + check_stage(load_project(root), args.section, args.explicit_stage_request),
                      "author_stage_request": args.explicit_stage_request}
        else:
            if not args.record:
                raise ValueError("--record is required")
            record = json.loads(sys.stdin.read() if args.record == "-" else resolve(args.record, root).read_text(encoding="utf-8-sig"))
            if not isinstance(record, dict):
                raise ValueError("Record must be a JSON object")
            if args.command == "candidate": result = {"errors": validate_candidate(record, root)}
            elif args.command == "sync": result = sync_status(record, root)
            else: result = propose_decision(root, record, args.intent, args.author_response, args.explicit_stage_request)
        result.update(read_only=True, scientific_verification=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("errors") else 0
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(json.dumps({"errors": [str(exc)], "read_only": True}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
