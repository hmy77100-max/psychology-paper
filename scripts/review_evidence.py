"""Read-only completeness checks for model-authored review evidence notes.

This module does not retrieve sources, verify their content, or decide whether
the author's scientific interpretation is correct.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STATUSES = (
    "ALIGNED", "BOUNDED", "CONDITIONAL", "UNRESOLVED",
    "CONTRADICTED", "OUTSIDE_EVIDENCE",
)
ACCESS_LEVELS = ("full_text", "excerpt", "abstract", "snippet", "unavailable")
RELATIONS = ("supports", "challenges", "qualifies", "context", "unresolved")
NOTE_FIELDS = (
    "issue_id", "question", "manuscript_location", "search_note",
    "counterevidence", "conclusion", "coverage_limit", "stop_reason",
)


def validate_record(record: object) -> dict:
    """Check provenance fields only; never mutate input or infer source truth."""
    errors: list[str] = []
    limitations = [
        "Record completeness is not scientific verification. Source existence, "
        "content, applicability and conclusions still require model/author review."
    ]

    def required_text(value: object, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}: non-empty text required")

    if not isinstance(record, dict):
        errors.append("record: object required")
    else:
        for field in NOTE_FIELDS:
            required_text(record.get(field), field)
        if record.get("evidence_status") not in STATUSES:
            errors.append("evidence_status: unknown status")

        sources = record.get("sources")
        if not isinstance(sources, list):
            errors.append("sources: list required")
        else:
            if not sources:
                limitations.append("No external sources recorded; external verification is not established.")
            seen: set[str] = set()
            for index, source in enumerate(sources):
                prefix = f"sources[{index}]"
                if not isinstance(source, dict):
                    errors.append(f"{prefix}: object required")
                    continue
                for field in ("source_id", "reference", "applicability"):
                    required_text(source.get(field), f"{prefix}.{field}")
                source_id = source.get("source_id")
                if isinstance(source_id, str) and source_id.strip():
                    normalized_id = source_id.strip()
                    if normalized_id in seen:
                        errors.append(f"{prefix}.source_id: duplicate identifier")
                    seen.add(normalized_id)

                access = source.get("access_level")
                if access not in ACCESS_LEVELS:
                    errors.append(f"{prefix}.access_level: unknown access level")
                if source.get("relation") not in RELATIONS:
                    errors.append(f"{prefix}.relation: unknown relation")
                if access == "unavailable":
                    # An access failure cannot supply inspected source content.
                    for field in ("locator", "observed_support"):
                        if source.get(field) != "":
                            errors.append(f"{prefix}.{field}: must be empty for unavailable source")
                else:
                    for field in ("locator", "observed_support"):
                        required_text(source.get(field), f"{prefix}.{field}")
                if access in ACCESS_LEVELS and access != "full_text":
                    limitations.append(f"{prefix}: {access} access; do not claim full-text verification.")

    return {
        "record_complete": not errors,
        "scientific_verification": False,
        "errors": errors,
        "limitations": limitations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", required=True, help="Existing JSON note path, or - for stdin")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        content = sys.stdin.read() if args.record == "-" else Path(args.record).read_text(encoding="utf-8-sig")
        result = validate_record(json.loads(content))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"evidence note error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["record_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
