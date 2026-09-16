from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Violation:
    rule_id: str
    message: str
    source_path: Path


def extract_json_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing JSON frontmatter: {path}")
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ValueError(f"Unclosed JSON frontmatter: {path}")
    data = json.loads(text[4:closing])
    if not isinstance(data, dict):
        raise ValueError(f"Frontmatter must be an object: {path}")
    return data, text[closing + 5 :]


def render_json_frontmatter(data: dict[str, Any], body: str) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return f"---\n{payload}\n---\n{body.lstrip()}"


def load_state_rules(path: Path, expected_version: int = 1) -> dict[str, Any]:
    data, _ = extract_json_frontmatter(path)
    if data.get("schema") != "psychology-paper-state-rules":
        raise ValueError(f"Unsupported rule schema: {path}")
    if data.get("version") != expected_version:
        raise ValueError(f"Unsupported rule version: {path}")
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"Rules must be a list: {path}")
    ids = [rule.get("id") for rule in rules if isinstance(rule, dict)]
    if len(ids) != len(rules) or len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError(f"Rule IDs must be unique and non-empty: {path}")
    return data


def _value_at(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _atom_matches(record: dict[str, Any], atom: dict[str, Any]) -> bool:
    actual = _value_at(record, atom["path"])
    expected = atom.get("value")
    operation = atom["op"]
    if operation == "eq":
        return actual == expected
    if operation == "ne":
        return actual != expected
    if operation == "in":
        return actual in expected
    if operation == "not_in":
        return actual not in expected
    if operation == "exists":
        return (actual is not None) is bool(expected)
    raise ValueError(f"Unsupported rule operator: {operation}")


def evaluate_rules(
    context: dict[str, Any],
    rules: dict[str, Any],
    component: str,
    source_path: Path,
) -> list[Violation]:
    violations: list[Violation] = []
    for rule in rules["rules"]:
        if component not in rule["components"]:
            continue
        target = _value_at(context, rule["scope"])
        if not isinstance(target, dict):
            continue
        all_match = all(_atom_matches(target, atom) for atom in rule.get("all", []))
        any_atoms = rule.get("any", [])
        any_match = not any_atoms or any(_atom_matches(target, atom) for atom in any_atoms)
        if all_match and any_match:
            violations.append(Violation(rule["id"], rule["message"], source_path))
    return violations
