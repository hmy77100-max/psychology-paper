from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


def compare_results(
    authoritative: dict[str, Any],
    verification: dict[str, Any],
    *,
    tolerance: float,
) -> dict[str, Any]:
    base = {"authoritative_preserved": True}
    if authoritative.get("analysis_id") != verification.get("analysis_id"):
        return {
            **base,
            "status": "NOT_COMPARABLE",
            "reason": "analysis identity differs",
            "mismatched_fields": [],
            "differences": {},
        }

    auth_spec = authoritative.get("specification")
    verify_spec = verification.get("specification")
    if not isinstance(auth_spec, dict) or not isinstance(verify_spec, dict):
        return {
            **base,
            "status": "NOT_COMPARABLE",
            "reason": "analysis specification is missing",
            "mismatched_fields": [],
            "differences": {},
        }
    mismatched_fields = sorted(
        key
        for key in set(auth_spec) | set(verify_spec)
        if auth_spec.get(key) != verify_spec.get(key)
    )
    if mismatched_fields:
        return {
            **base,
            "status": "SPECIFICATION_MISMATCH",
            "reason": "analysis specification differs",
            "mismatched_fields": mismatched_fields,
            "differences": {},
        }

    auth_statistics = authoritative.get("statistics")
    verify_statistics = verification.get("statistics")
    if not isinstance(auth_statistics, dict) or not isinstance(verify_statistics, dict):
        return {
            **base,
            "status": "NOT_COMPARABLE",
            "reason": "statistics are missing",
            "mismatched_fields": [],
            "differences": {},
        }
    differences: dict[str, dict[str, Any]] = {}
    for key in sorted(set(auth_statistics) | set(verify_statistics)):
        left = auth_statistics.get(key)
        right = verify_statistics.get(key)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            equal = math.isclose(float(left), float(right), abs_tol=tolerance, rel_tol=0.0)
        else:
            equal = left == right
        if not equal:
            differences[key] = {
                "authoritative": left,
                "verification": right,
            }
    return {
        **base,
        "status": "NUMERIC_DISCREPANCY" if differences else "ALIGNED",
        "reason": "numeric results differ" if differences else "results align",
        "mismatched_fields": [],
        "differences": differences,
    }


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("analysis result must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two outputs for one analysis.")
    parser.add_argument("--authoritative", required=True)
    parser.add_argument("--verification", required=True)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.tolerance < 0:
        print("tolerance must be non-negative", file=sys.stderr)
        return 2
    try:
        result = compare_results(
            _load(args.authoritative),
            _load(args.verification),
            tolerance=args.tolerance,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
