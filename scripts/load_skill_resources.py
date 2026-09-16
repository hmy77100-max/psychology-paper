"""Load explicitly selected Skill resources without directory discovery."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple, Sequence


DEFAULT_MAX_CHARS = 12_000
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ResourceResolutionError(RuntimeError):
    """A declared Skill resource cannot be resolved exactly."""


class ResourceBudgetError(RuntimeError):
    """Selected resources exceed the allowed context budget."""


class LoadedResource(NamedTuple):
    relative_path: str
    content: str


class LoadResult(NamedTuple):
    skill: str
    selectors: tuple[str, ...]
    resources: tuple[LoadedResource, ...]
    total_chars: int


def _manifest_value(manifest: object, selector: str) -> list[str]:
    value = manifest
    for part in selector.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ResourceResolutionError(f"unknown resource selector: {selector}")
        value = value[part]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ResourceResolutionError(f"resource selector is not a path list: {selector}")
    return value


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def load_skill_resources(
    *,
    skill: str,
    selectors: Sequence[str],
    max_chars: int = DEFAULT_MAX_CHARS,
    plugin_root: Path | None = None,
) -> LoadResult:
    if not SKILL_NAME.fullmatch(skill):
        raise ResourceResolutionError(f"invalid skill name: {skill}")
    if max_chars < 1:
        raise ResourceBudgetError(f"character budget must be positive: {max_chars}")

    root = (plugin_root or PLUGIN_ROOT).resolve()
    skill_root = root / "skills" / skill
    manifest_path = skill_root / "manifest.yaml"
    if not manifest_path.is_file():
        raise ResourceResolutionError(f"skill manifest is missing: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceResolutionError(f"skill manifest is invalid: {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("skill") != skill:
        raise ResourceResolutionError(f"skill manifest identity mismatch: {manifest_path}")

    selected = ("always_load", *selectors)
    declared_paths: list[str] = []
    for selector in selected:
        for raw_path in _manifest_value(manifest, selector):
            if raw_path not in declared_paths:
                declared_paths.append(raw_path)

    resources: list[LoadedResource] = []
    total_chars = 0
    for raw_path in declared_paths:
        resolved = (skill_root / raw_path).resolve()
        if not _within(resolved, root):
            raise ResourceResolutionError(
                f"declared resource escapes plugin root: {raw_path}"
            )
        if not resolved.is_file():
            display_path = raw_path.removeprefix("./")
            raise ResourceResolutionError(
                f"declared resource is missing: {display_path}"
            )
        content = resolved.read_text(encoding="utf-8")
        total_chars += len(content)
        if total_chars > max_chars:
            raise ResourceBudgetError(
                f"resource content requires {total_chars} characters; budget is {max_chars}"
            )
        resources.append(
            LoadedResource(
                relative_path=raw_path.removeprefix("./"),
                content=content,
            )
        )

    return LoadResult(
        skill=skill,
        selectors=tuple(selected),
        resources=tuple(resources),
        total_chars=total_chars,
    )


def render_text(result: LoadResult) -> str:
    sections = [
        f"--- resource: {resource.relative_path} ---\n{resource.content.rstrip()}"
        for resource in result.resources
    ]
    return "\n\n".join(sections) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load only Manifest-selected resources for one psychology-paper Skill."
    )
    parser.add_argument("--skill", required=True)
    parser.add_argument("--select", action="append", default=[])
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        result = load_skill_resources(
            skill=args.skill,
            selectors=args.select,
            max_chars=args.max_chars,
        )
    except (ResourceResolutionError, ResourceBudgetError) as exc:
        print(f"resource loader error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
