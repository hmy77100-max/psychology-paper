from __future__ import annotations

import argparse
import json
import re
import sys


CANDIDATE_ID = re.compile(r"^[0-9]{5}$")


def _validated_ids(values: list[str]) -> set[str]:
    invalid = [value for value in values if not CANDIDATE_ID.fullmatch(value)]
    if invalid:
        raise ValueError(f"candidate IDs must be five digits: {invalid[0]}")
    return set(values)


def allocate_candidate_id(
    *, used: list[str], revision_of: str | None = None
) -> tuple[str, bool]:
    issued = _validated_ids(used)
    if revision_of is not None:
        if not CANDIDATE_ID.fullmatch(revision_of):
            raise ValueError("revision ID must be five digits")
        if revision_of not in issued:
            raise ValueError("revision ID has not been issued in this project")
        return revision_of, True

    for number in range(10000, 100000):
        candidate = str(number)
        if candidate not in issued:
            return candidate, False
    raise ValueError("all five-digit candidate IDs have been issued")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Allocate a unique writing candidate ID.")
    parser.add_argument("--used", action="append", default=[])
    parser.add_argument("--revision-of")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidate_id, reused = allocate_candidate_id(
            used=args.used,
            revision_of=args.revision_of,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "candidate_id": candidate_id,
                "reused_for_revision": reused,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
