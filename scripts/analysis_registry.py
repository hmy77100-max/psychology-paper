from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from analysis_contracts import R_METHODS, analysis_context, validate_result
import json
from pathlib import Path
import sys

from project_state import extract_json_frontmatter, render_json_frontmatter


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    PLUGIN_ROOT
    / "assets"
    / "project-template"
    / ".psychology-paper"
    / "ANALYSIS_REGISTRY.md"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage psychology analysis registry state.")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--project-root", required=True)
    initialize.add_argument("--confirm-create", action="store_true")
    add = commands.add_parser("add")
    add.add_argument("--project-root", required=True)
    add.add_argument("--entry", required=True)
    add.add_argument("--confirm-adopt", action="store_true")
    initialize.add_argument("--json", action="store_true")
    add.add_argument("--json", action="store_true")
    return parser


def initialize(project_root: Path, confirmed: bool) -> int:
    if not confirmed:
        print("--confirm-create is required", file=sys.stderr)
        return 2
    project_path = project_root / ".psychology-paper" / "PROJECT.md"
    registry_path = project_root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
    if not project_path.is_file():
        print(f"Project state does not exist: {project_path}", file=sys.stderr)
        return 2
    if registry_path.exists():
        print(f"Analysis registry already exists: {registry_path}", file=sys.stderr)
        return 3

    try:
        project, project_body = extract_json_frontmatter(project_path)
        registry, registry_body = extract_json_frontmatter(TEMPLATE)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    registry["project_root"] = str(project_root)
    optional = project.get("optional_state_files")
    if not isinstance(optional, dict):
        print("optional_state_files must be an object", file=sys.stderr)
        return 2
    optional["analysis_registry"] = str(registry_path.resolve())
    registry_content = render_json_frontmatter(registry, registry_body)
    atomic_write(registry_path, registry_content, None)
    created_identity = registry_path.stat()
    try:
        atomic_write(project_path, render_json_frontmatter(project, project_body), SNAPSHOTS[project_path])
    except (OSError, Conflict):
        # Roll back only the exact bytes created by this transaction.
        if registry_path.is_file() and os.path.samestat(registry_path.stat(), created_identity) and registry_path.read_bytes() == registry_content.encode("utf-8"):
            registry_path.unlink()
        raise
    print(f"Created {registry_path}")
    return 0


REQUIRED_ENTRY_FIELDS = {
    "analysis_id",
    "research_question",
    "design_tags",
    "observation_unit",
    "field_map",
    "scoring",
    "sample",
    "model",
    "software",
    "estimation",
    "bootstrap",
    "random_seed",
    "sources",
    "formal_output",
    "manuscript_locations",
}


def add_entry(project_root: Path, entry_path: Path, confirmed: bool) -> int:
    if not confirmed:
        print("--confirm-adopt is required", file=sys.stderr)
        return 2
    registry_path = project_root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
    if not registry_path.is_file():
        print(f"Analysis registry does not exist: {registry_path}", file=sys.stderr)
        return 2
    try:
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        registry, body = extract_json_frontmatter(registry_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(entry, dict):
        print("analysis entry must be a JSON object", file=sys.stderr)
        return 2
    missing = sorted(REQUIRED_ENTRY_FIELDS - set(entry))
    if missing:
        print("analysis entry is missing: " + ", ".join(missing), file=sys.stderr)
        return 2
    for key in ("research_question", "observation_unit", "estimation", "analysis_id", "formal_output"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            print(f"analysis entry {key} must be nonempty text", file=sys.stderr)
            return 2
    for key in ("scoring", "sample", "model", "software"):
        if not isinstance(entry.get(key), dict) or not entry[key]:
            print(f"analysis entry {key} must be a nonempty object", file=sys.stderr)
            return 2
    for key in ("design_tags", "field_map", "manuscript_locations"):
        if not isinstance(entry.get(key), list) or not entry[key]:
            print(f"analysis entry {key} must be a nonempty list", file=sys.stderr)
            return 2
    sources = entry.get("sources")
    if not isinstance(sources, list):
        print("analysis sources must be a list", file=sys.stderr)
        return 2
    authoritative = [
        source
        for source in sources
        if isinstance(source, dict) and source.get("role") == "AUTHORITATIVE"
    ]
    verification = [
        source
        for source in sources
        if isinstance(source, dict) and source.get("role") == "VERIFICATION"
    ]
    if len(authoritative) != 1:
        print("exactly one AUTHORITATIVE source is required", file=sys.stderr)
        return 2
    if len(verification) > 1:
        print("at most one VERIFICATION source is allowed", file=sys.stderr)
        return 2
    try:
        reference = validate_formal_reference(entry, project_root)
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    analyses = registry.get("analyses")
    if not isinstance(analyses, list):
        print("registry analyses must be a list", file=sys.stderr)
        return 2
    analysis_id = entry.get("analysis_id")
    if any(
        isinstance(existing, dict) and existing.get("analysis_id") == analysis_id
        for existing in analyses
    ):
        print(f"analysis ID already exists: {analysis_id}", file=sys.stderr)
        return 3
    adopted = dict(entry)
    adopted["adoption_status"] = "USER_ADOPTED"
    adopted["integrity_version"] = 1
    if entry.get("evidence_kind") == "external_analysis":
        adopted["evidence_level"] = "EXTERNAL_ARTIFACTS_REGISTERED_NUMERICS_UNVERIFIED"
        adopted["discrepancy_status"] = "NOT_ASSESSED"
    adopted["formal_output_ref"] = reference
    if 'analysis_context' in reference:
        adopted['analysis_context']=reference['analysis_context']
    analyses.append(adopted)
    if hashlib.sha256(Path(reference["path"]).read_bytes()).hexdigest() != reference["sha256"]:
        raise Conflict("Formal output changed during adoption")
    if entry.get("evidence_kind") == "external_analysis":
        try:
            unchanged = validate_external_reference(entry, project_root) == reference
        except (OSError, ValueError, TypeError) as exc:
            raise Conflict(f"External analysis artifacts changed during adoption: {exc}") from exc
        if not unchanged:
            raise Conflict("External analysis artifacts changed during adoption")
    atomic_write(registry_path, render_json_frontmatter(registry, body), SNAPSHOTS[registry_path])
    print(f"Registered {analysis_id}")
    return 0


class Conflict(Exception):
    pass

SNAPSHOTS = {}

def atomic_write(path, content, expected):
    current = path.read_bytes() if path.exists() else None
    if current != expected:
        raise Conflict(f"State changed during update: {path}")
    fd, name = tempfile.mkstemp(prefix=".analysis-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        current = path.read_bytes() if path.exists() else None
        if current != expected:
            raise Conflict(f"State changed during update: {path}")
        if expected is None:
            # Exclusive publication cannot replace a concurrently created file.
            os.link(name, path)
        else:
            os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

EXTERNAL_SPEC_FIELDS = ("research_question", "design_tags", "observation_unit", "field_map", "scoring", "sample", "model", "software", "estimation", "bootstrap", "random_seed", "input_hash")

def validate_external_reference(entry, root):
    """Bind author-selected external artifacts; do not interpret numeric correctness."""
    for key in ("spec_hash", "input_hash"):
        value = entry.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"external {key} must be SHA256")
    scientific = {key: entry.get(key) for key in EXTERNAL_SPEC_FIELDS}
    digest = hashlib.sha256(json.dumps(scientific, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if entry.get("spec_hash") != digest:
        raise ValueError("external scientific specification hash mismatch")
    software = entry.get("software")
    if not isinstance(software, dict) or any(not isinstance(software.get(k), str) or not software[k].strip() for k in ("name", "version")):
        raise ValueError("external software name and version required")
    for source in entry.get("sources", []):
        if source.get("role") == "AUTHORITATIVE" and (source.get("software") != software["name"] or source.get("version") != software["version"]):
            raise ValueError("external AUTHORITATIVE software/version mismatch")
    verifier = next((source for source in entry.get("sources", []) if source.get("role") == "VERIFICATION"), None)
    if entry.get("discrepancy_status", "NOT_ASSESSED") != "NOT_ASSESSED":
        raise ValueError("external discrepancy_status must be NOT_ASSESSED")
    sources_by_id = {}
    if verifier:
        for source in entry["sources"]:
            if any(not isinstance(source.get(k), str) or not source[k].strip() for k in ("source_id", "software", "version")):
                raise ValueError("source_id, software and version required for multiple sources")
            if source["source_id"] in sources_by_id:
                raise ValueError("source_id must be unique")
            sources_by_id[source["source_id"]] = source
    artifacts = entry.get("external_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) < 2:
        raise ValueError("external author-attested output and original syntax/code artifacts required")
    refs = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("role") not in ("output", "syntax"):
            raise ValueError("external artifact role must be output or syntax")
        source = sources_by_id.get(artifact.get("source_id")) if verifier else None
        if verifier and source is None:
            raise ValueError("external artifact source_id missing or unknown")
        expected_software = source["software"] if source else software["name"]
        expected_version = source["version"] if source else software["version"]
        if artifact.get("software") != expected_software or artifact.get("version") != expected_version:
            raise ValueError("external artifact software/version mismatch")
        if not isinstance(artifact.get("path"), str) or not artifact["path"].strip():
            raise ValueError("external artifact path required")
        path = Path(artifact["path"])
        path = (root / path).resolve() if not path.is_absolute() else path.resolve()
        content = path.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if not content or artifact.get("sha256") != actual:
            raise ValueError("external artifact missing content or SHA256 mismatch")
        ref = {"role": artifact["role"], "path": str(path), "sha256": actual, "software": expected_software, "version": expected_version}
        if verifier: ref["source_id"] = source["source_id"]
        refs.append(ref)
    outputs = [ref for ref in refs if ref["role"] == "output"]
    if not outputs or not any(ref["role"] == "syntax" for ref in refs) or len({ref["path"] for ref in refs}) != len(refs):
        raise ValueError("distinct output and original syntax/code required")
    formal = Path(entry["formal_output"])
    formal = (root / formal).resolve() if not formal.is_absolute() else formal.resolve()
    output = next((ref for ref in outputs if ref["path"] == str(formal)), None)
    if output is None: raise ValueError("formal_output must identify an output artifact")
    if verifier:
        formal_id = next(source["source_id"] for source in entry["sources"] if source["role"] == "AUTHORITATIVE")
        if output["source_id"] != formal_id or not any(ref["role"] == "syntax" and ref["source_id"] == formal_id for ref in refs):
            raise ValueError("formal output and syntax must bind AUTHORITATIVE source")
        verification = entry.get("verification_output")
        if not isinstance(verification, str) or not verification.strip():
            raise ValueError("verification_output required for VERIFICATION source")
        verification_path = Path(verification)
        verification_path = (root / verification_path).resolve() if not verification_path.is_absolute() else verification_path.resolve()
        if not any(ref["role"] == "output" and ref["path"] == str(verification_path) and ref["source_id"] == verifier["source_id"] for ref in refs):
            raise ValueError("verification_output must bind VERIFICATION output artifact")
    reference = {"path": str(formal), "sha256": output["sha256"], "analysis_id": entry["analysis_id"], "spec_hash": digest,
                 "input_hash": entry["input_hash"], "artifacts": refs,
                 "evidence_level": "EXTERNAL_ARTIFACTS_REGISTERED_NUMERICS_UNVERIFIED", "origin_status": "AUTHOR_ATTESTED"}
    if verifier:
        reference["sources"] = entry["sources"]
        reference["verification_output"] = str(verification_path)
        reference["discrepancy_status"] = "NOT_ASSESSED"
        reference["verification_process_status"] = "UNVERIFIED_CODE_REGISTERED" if any(ref["role"] == "syntax" and ref["source_id"] == verifier["source_id"] for ref in refs) else "UNVERIFIED_CODE_NOT_PROVIDED"
    if "formal_output_ref" in entry and entry["formal_output_ref"] != reference:
        raise ValueError("external saved artifact reference mismatch")
    return reference

def validate_formal_reference(entry, root):
    for key in ("analysis_id", "spec_hash", "input_hash", "formal_output"):
        if not isinstance(entry.get(key), str) or not entry[key].strip():
            raise ValueError(f"{key} must be nonempty text")
    required_source_fields = ("role", "software") if entry.get("evidence_kind") == "external_analysis" else ("source_id", "role", "software")
    for source in entry.get("sources", []):
        if not isinstance(source, dict) or any(not isinstance(source.get(k), str) or not source[k].strip() for k in required_source_fields):
            raise ValueError("source_id, role and software must be nonempty text")
        if source["role"] not in {"AUTHORITATIVE", "VERIFICATION", "DATA_ONLY", "CANDIDATE", "DERIVED"}:
            raise ValueError("unsupported source role")
    if entry.get("evidence_kind") == "external_analysis":
        return validate_external_reference(entry, root)
    if entry.get("evidence_kind") not in (None, "controlled_run"):
        raise ValueError("unsupported evidence_kind")
    raw = Path(entry["formal_output"])
    path = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
    content = path.read_bytes()
    run = json.loads(content)
    errors = validate_result(run)
    if errors: raise ValueError("invalid formal_output: " + json.dumps(errors))
    for key in ("analysis_id", "spec_hash", "input_hash"):
        if entry[key] != run[key]: raise ValueError(f"formal_output {key} mismatch")
    scientific = run["scientific_spec"]
    design = scientific.get("design", {})
    for key in ("field_map", "scoring", "sample", "model"):
        if key not in scientific or entry.get(key) != scientific[key]:
            raise ValueError(f"formal_output scientific metadata mismatch: {key}")
    for key in ("design_tags", "observation_unit"):
        if not isinstance(design, dict) or key not in design or entry.get(key) != design[key]:
            raise ValueError(f"formal_output design mismatch: {key}")
    method = scientific["model"].get("method")
    if method in R_METHODS:
        boot=scientific['inference'].get('bootstrap')
        if entry.get('bootstrap')!=boot or entry.get('random_seed')!=(boot.get('seed') if boot else None):
            raise ValueError('formal_output bootstrap/random_seed mismatch')
        if method=='mediation' or method in ('cfa','sem'):estimation=scientific['model']['estimator']
        elif method.endswith('_mixed'):estimation=scientific['model']['estimation']
        elif method.endswith('_anova'):estimation='ANOVA-'+scientific['model']['ss_type']
        else:estimation='OLS' if method=='linear_regression' or (method=='moderation' and scientific['model']['family']=='linear') else 'ML'
        allowed_estimations={estimation}
    else:
        for key in ('bootstrap','random_seed'):
            if entry.get(key) not in (None,'NOT_APPLICABLE'):raise ValueError(f'formal_output {key} is not applicable to controlled methods')
    if method in ("descriptive", "scale_score"):
        allowed_estimations = {"NOT_APPLICABLE", "descriptive"}
    elif method not in R_METHODS:
        alternative = scientific.get("inference", {}).get("alternative")
        allowed_estimations = {"two-sided", "two-tailed"} if alternative == "two-sided" else {alternative}
    if not isinstance(entry.get("estimation"), str) or entry["estimation"] not in allowed_estimations:
        raise ValueError("formal_output estimation does not match executed method and alternative")
    audit = run.get("sample_audit", {})
    effective_n = audit.get("effective_n") if isinstance(audit, dict) else None
    if type(effective_n) is not int or effective_n != run["results"][0].get("n"):
        raise ValueError("formal_output sample audit and results n mismatch")
    if "n" in entry["sample"] and (type(entry["sample"]["n"]) is not int or entry["sample"]["n"] != effective_n):
        raise ValueError("formal_output sample n mismatch")
    provenance = run["execution_provenance"]
    engines = {"python": provenance["python"]} if isinstance(provenance, dict) and isinstance(provenance.get("python"), str) else {}
    if isinstance(provenance, dict) and isinstance(provenance.get("engine"), str):
        engines[provenance["engine"].casefold()] = provenance.get("version")
    software = entry.get("software", {})
    name = software.get("name") if isinstance(software, dict) else None
    if not isinstance(name, str) or name.casefold() not in engines or software.get("version") != engines[name.casefold()]:
        raise ValueError("formal_output software does not match execution provenance")
    for source in entry["sources"]:
        if source["role"] == "AUTHORITATIVE" and (source["software"].casefold() != name.casefold() or ("version" in source and source["version"] != engines[name.casefold()])):
            raise ValueError("AUTHORITATIVE software does not match execution provenance")
    digest = hashlib.sha256(content).hexdigest()
    saved = entry.get("formal_output_ref")
    if saved is not None and (not isinstance(saved, dict) or saved.get("sha256") != digest or saved.get("run_id") != run["run_id"] or saved.get("path") != str(path)):
        raise ValueError("formal_output reference hash or identity mismatch")
    context=analysis_context(run)
    if 'analysis_context' in entry and entry['analysis_context']!=context:
        raise ValueError('analysis context must preserve the recorded origin')
    if saved and 'analysis_context' in saved and saved['analysis_context']!=context:
        raise ValueError('saved analysis context differs from original run')
    return {"path": str(path), "sha256": digest, "run_id": run["run_id"], "analysis_context":context,
            "analysis_id": run["analysis_id"], "spec_hash": run["spec_hash"], "input_hash": run["input_hash"]}


def main(argv: list[str] | None = None) -> int:
    import contextlib
    import io
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    output, errors = io.StringIO(), io.StringIO()
    code = 2
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
        lock = root / ".psychology-paper" / "analysis.lock"
        owned = False
        try:
            confirmed = args.confirm_create if args.command == "init" else args.confirm_adopt
            if not confirmed:
                raise ValueError("--confirm-create is required" if args.command == "init" else "--confirm-adopt is required")
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                raise Conflict(f"Analysis state locked: {lock}")
            owned = True
            os.close(fd)
            SNAPSHOTS.clear()
            for name in ("PROJECT.md", "ANALYSIS_REGISTRY.md"):
                path = lock.parent / name
                SNAPSHOTS[path] = path.read_bytes() if path.exists() else None
            if args.command == "init":
                code = initialize(root, args.confirm_create)
            else:
                code = add_entry(root, Path(args.entry).expanduser().resolve(), args.confirm_adopt)
        except (Conflict, FileExistsError) as exc:
            print(str(exc), file=sys.stderr)
            code = 3
        except (OSError, ValueError, TypeError) as exc:
            print(str(exc), file=sys.stderr)
            code = 2
        finally:
            if owned: lock.unlink()
    if args.json:
        print(json.dumps({"ok": code == 0, "status": "COMPLETED" if code == 0 else "CONFLICT" if code == 3 else "REJECTED", "exit_code": code, "message": (output.getvalue() + errors.getvalue()).strip()}))
    else:
        print(output.getvalue(), end="")
        print(errors.getvalue(), end="", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
