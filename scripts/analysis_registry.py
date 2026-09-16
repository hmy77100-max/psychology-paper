from __future__ import annotations

import argparse
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
    registry_path.write_text(
        render_json_frontmatter(registry, registry_body), encoding="utf-8"
    )
    optional = project.get("optional_state_files")
    if not isinstance(optional, dict):
        registry_path.unlink(missing_ok=True)
        print("optional_state_files must be an object", file=sys.stderr)
        return 2
    optional["analysis_registry"] = str(registry_path.resolve())
    try:
        project_path.write_text(
            render_json_frontmatter(project, project_body), encoding="utf-8"
        )
    except OSError as exc:
        registry_path.unlink(missing_ok=True)
        print(str(exc), file=sys.stderr)
        return 2
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
    analyses.append(adopted)
    registry_path.write_text(render_json_frontmatter(registry, body), encoding="utf-8")
    print(f"Registered {analysis_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return initialize(Path(args.project_root).expanduser().resolve(), args.confirm_create)
    if args.command == "add":
        return add_entry(
            Path(args.project_root).expanduser().resolve(),
            Path(args.entry).expanduser().resolve(),
            args.confirm_adopt,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
