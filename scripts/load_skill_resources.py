"""Load explicitly selected Skill resources without directory discovery."""

from __future__ import annotations

import argparse
import hashlib
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
            raise ResourceResolutionError(
                f"unknown resource selector: {selector}; valid selectors: "
                + ", ".join(_selectors(manifest))
            )
        value = value[part]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ResourceResolutionError(f"resource selector is not a path list: {selector}")
    return value


def _selectors(value: object, prefix: str = "") -> list[str]:
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return [prefix]
    if isinstance(value, dict):
        return [s for k, child in value.items()
                for s in _selectors(child, f"{prefix}.{k}" if prefix else k)]
    return []


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_resources(
    *,
    skill: str,
    selectors: Sequence[str],
    max_chars: int = DEFAULT_MAX_CHARS,
    plugin_root: Path | None = None,
) -> tuple[LoadResult, str, list[str]]:
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
    seen: set[Path] = set()
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
        if resolved in seen:
            continue
        seen.add(resolved)
        content = resolved.read_text(encoding="utf-8")
        total_chars += len(content)
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
    ), hashlib.sha256(manifest_path.read_bytes()).hexdigest(), _selectors(manifest)


def describe_resources(**kwargs) -> dict:
    """Plan exact loads, including complete costs, without printing instruction text."""
    result, manifest_hash, selectors = _resolve_resources(**kwargs)
    budget = kwargs.get("max_chars", DEFAULT_MAX_CHARS)
    cumulative = 0
    first_overflow = None
    records = []
    for resource in result.resources:
        cumulative += len(resource.content)
        if cumulative > budget and first_overflow is None:
            first_overflow = resource.relative_path
        records.append({"path": resource.relative_path, "chars": len(resource.content),
                        "sha256": hashlib.sha256(resource.content.encode("utf-8")).hexdigest()})
    return {"skill": result.skill, "selectors": result.selectors, "valid_selectors": selectors,
            "manifest_sha256": manifest_hash, "resources": records,
            "total_chars": result.total_chars, "budget": budget, "first_overflow": first_overflow}


def load_skill_resources(**kwargs) -> LoadResult:
    result, _, _ = _resolve_resources(**kwargs)
    budget = kwargs.get("max_chars", DEFAULT_MAX_CHARS)
    if result.total_chars > budget:
        cumulative = 0
        first = ""
        for resource in result.resources:
            cumulative += len(resource.content)
            if cumulative > budget:
                first = resource.relative_path
                break
        raise ResourceBudgetError(
            f"resource content requires {result.total_chars} characters; budget is {budget}; "
            f"first overflow: {first}; use --describe for the complete plan; "
            "stop this invocation, do not retry selectors or increase the budget"
        )
    return result


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
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--list-selectors", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        if args.describe or args.list_selectors:
            plan = describe_resources(skill=args.skill, selectors=args.select, max_chars=args.max_chars)
            print(json.dumps(plan["valid_selectors"] if args.list_selectors else plan, ensure_ascii=False, indent=2))
            return 0
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
