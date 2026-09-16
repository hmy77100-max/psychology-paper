from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

from project_state import evaluate_rules, extract_json_frontmatter, load_state_rules


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RULE_PATH = PLUGIN_ROOT / "skills" / ".shared" / "core" / "state-consistency.md"
ALLOWED_OPTIONAL_FILES = {"journal_profile", "analysis_registry", "style_delta"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate psychology-paper project state.")
    parser.add_argument("--project-root", required=True)
    return parser


def _absolute_or_project_path(raw_path: str, project_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def validate_state(state: dict[str, Any], project_root: Path) -> list[str]:
    errors: list[str] = []
    if state.get("schema") != "psychology-paper-project":
        errors.append("Unsupported project schema")
    if state.get("schema_version") != 1:
        errors.append("Unsupported project schema version")

    configured_root = state.get("project_root")
    if not configured_root:
        errors.append("project_root is empty")
    else:
        resolved_root = _absolute_or_project_path(str(configured_root), project_root)
        if resolved_root != project_root:
            errors.append("project_root does not match the validated directory")

    manuscript_value = state.get("authoritative_manuscript")
    manuscript: Path | None = None
    if not manuscript_value:
        errors.append("authoritative_manuscript is empty")
    else:
        manuscript = _absolute_or_project_path(str(manuscript_value), project_root)
        if not manuscript.is_absolute() or not manuscript.is_file():
            errors.append("authoritative_manuscript is not an existing file")

    sources = state.get("sources")
    authoritative_sources: list[dict[str, Any]] = []
    if not isinstance(sources, list):
        errors.append("sources must be a list")
    else:
        authoritative_sources = [
            source
            for source in sources
            if isinstance(source, dict) and source.get("role") == "AUTHORITATIVE"
        ]
        if len(authoritative_sources) != 1:
            errors.append("exactly one AUTHORITATIVE source is required")
        elif manuscript is not None:
            source_path = _absolute_or_project_path(
                str(authoritative_sources[0].get("path", "")), project_root
            )
            if source_path != manuscript:
                errors.append("AUTHORITATIVE source path does not match authoritative_manuscript")

    optional_files = state.get("optional_state_files")
    analysis_registry_path: Path | None = None
    if not isinstance(optional_files, dict):
        errors.append("optional_state_files must be an object")
    else:
        for key, value in optional_files.items():
            if value is None:
                continue
            if key not in ALLOWED_OPTIONAL_FILES:
                errors.append(f"Unsupported optional state file: {key}")
                continue
            optional_path = _absolute_or_project_path(str(value), project_root)
            if not optional_path.is_file():
                errors.append(f"optional state file does not exist: {key}")
            elif key == "analysis_registry":
                analysis_registry_path = optional_path

    if analysis_registry_path is not None:
        try:
            registry, _ = extract_json_frontmatter(analysis_registry_path)
        except (OSError, ValueError) as exc:
            errors.append(f"analysis registry is invalid: {exc}")
        else:
            if registry.get("schema") != "psychology-paper-analysis-registry":
                errors.append("analysis registry schema is unsupported")
            if registry.get("schema_version") != 1:
                errors.append("analysis registry version is unsupported")
            analyses = registry.get("analyses")
            if not isinstance(analyses, list):
                errors.append("analysis registry analyses must be a list")
            else:
                ids = [
                    entry.get("analysis_id")
                    for entry in analyses
                    if isinstance(entry, dict)
                ]
                if len(ids) != len(analyses) or any(not value for value in ids):
                    errors.append("analysis registry entries require analysis_id")
                elif len(ids) != len(set(ids)):
                    errors.append("analysis registry analysis_id values must be unique")
                for entry in analyses:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("adoption_status") != "USER_ADOPTED":
                        errors.append("analysis registry contains an unadopted entry")
                    sources = entry.get("sources")
                    if not isinstance(sources, list):
                        errors.append("analysis registry entry sources must be a list")
                        continue
                    authoritative = [
                        source
                        for source in sources
                        if isinstance(source, dict)
                        and source.get("role") == "AUTHORITATIVE"
                    ]
                    verification = [
                        source
                        for source in sources
                        if isinstance(source, dict)
                        and source.get("role") == "VERIFICATION"
                    ]
                    if len(authoritative) != 1:
                        errors.append(
                            "analysis registry entry requires exactly one AUTHORITATIVE source"
                        )
                    if len(verification) > 1:
                        errors.append(
                            "analysis registry entry allows at most one VERIFICATION source"
                        )

    body_budget = state.get("body_budget")
    if not isinstance(body_budget, dict):
        errors.append("body_budget must be an object")
    else:
        status = body_budget.get("status")
        if status not in {"UNSET", "WITHIN_LIMIT", "COMPRESSION_REQUIRED"}:
            errors.append("body_budget status is unsupported")
        values = (
            body_budget.get("limit"),
            body_budget.get("unit"),
            body_budget.get("counting_scope"),
            body_budget.get("current"),
        )
        if status == "UNSET" and any(value is not None for value in values):
            errors.append("an UNSET body_budget cannot contain configured values")
        if status != "UNSET":
            limit, unit, counting_scope, current = values
            if not isinstance(limit, int) or limit < 0:
                errors.append("body_budget limit must be a non-negative integer")
            if not isinstance(current, int) or current < 0:
                errors.append("body_budget current must be a non-negative integer")
            if not isinstance(unit, str) or not unit:
                errors.append("body_budget unit is required")
            if not isinstance(counting_scope, str) or not counting_scope:
                errors.append("body_budget counting_scope is required")

    candidate_ids = state.get("issued_candidate_ids")
    if not isinstance(candidate_ids, list):
        errors.append("issued_candidate_ids must be a list")
    else:
        if len(candidate_ids) != len(set(candidate_ids)):
            errors.append("issued_candidate_ids must not contain duplicates")
        if any(
            not isinstance(candidate_id, str)
            or len(candidate_id) != 5
            or not candidate_id.isdigit()
            for candidate_id in candidate_ids
        ):
            errors.append("issued_candidate_ids must contain only five-digit strings")

    return errors


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(args.project_root).expanduser().resolve()
    state_path = project_root / ".psychology-paper" / "PROJECT.md"
    try:
        rules = load_state_rules(RULE_PATH)
        state, _ = extract_json_frontmatter(state_path)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    errors = validate_state(state, project_root)
    violations = evaluate_rules(
        state,
        rules,
        component="project-validator",
        source_path=RULE_PATH.resolve(),
    )
    for violation in violations:
        errors.append(
            f"{violation.rule_id}: {violation.message} [source: {violation.source_path}]"
        )

    if errors:
        for error in errors:
            print(error)
        return 1
    print("Project state valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
