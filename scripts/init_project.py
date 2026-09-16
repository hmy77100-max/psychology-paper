from __future__ import annotations

import argparse
from pathlib import Path
import sys

from project_state import extract_json_frontmatter, render_json_frontmatter
from workflow_guards import calculate_body_budget


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PLUGIN_ROOT / "assets" / "project-template" / ".psychology-paper" / "PROJECT.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize psychology-paper project state.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--journal")
    parser.add_argument("--body-limit", type=int)
    parser.add_argument("--body-unit")
    parser.add_argument("--body-counting-scope")
    parser.add_argument("--current-body-count", type=int)
    parser.add_argument("--confirm-create", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm_create:
        print("--confirm-create is required", file=sys.stderr)
        return 2

    project_root = Path(args.project_root).expanduser().resolve()
    manuscript = Path(args.manuscript).expanduser().resolve()
    if not project_root.is_dir():
        print(f"Project root is not a directory: {project_root}", file=sys.stderr)
        return 2
    if not manuscript.is_file():
        print(f"Manuscript is not a file: {manuscript}", file=sys.stderr)
        return 2

    state_path = project_root / ".psychology-paper" / "PROJECT.md"
    if state_path.exists():
        print(f"Project state already exists: {state_path}", file=sys.stderr)
        return 3

    state, body = extract_json_frontmatter(TEMPLATE)
    state["project_root"] = str(project_root)
    state["authoritative_manuscript"] = str(manuscript)
    state["sources"] = [
        {
            "id": "current-manuscript",
            "path": str(manuscript),
            "role": "AUTHORITATIVE",
        }
    ]
    if args.journal:
        state["journal"] = {"name": args.journal, "status": "USER_CONFIRMED"}
    budget_values = (
        args.body_limit,
        args.body_unit,
        args.body_counting_scope,
        args.current_body_count,
    )
    if any(value is not None for value in budget_values):
        if any(value is None for value in budget_values):
            print(
                "body budget requires --body-limit, --body-unit, "
                "--body-counting-scope, and --current-body-count",
                file=sys.stderr,
            )
            return 2
        try:
            budget = calculate_body_budget(
                limit=args.body_limit,
                current=args.current_body_count,
                replaced=0,
                candidate=0,
                unit=args.body_unit,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        state["body_budget"] = {
            "limit": budget.limit,
            "unit": budget.unit,
            "counting_scope": args.body_counting_scope,
            "current": budget.current,
            "status": budget.status,
        }

    state_path.parent.mkdir(parents=True, exist_ok=False)
    state_path.write_text(render_json_frontmatter(state, body), encoding="utf-8")
    print(f"Created {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
