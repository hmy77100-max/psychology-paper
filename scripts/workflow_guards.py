from __future__ import annotations

import argparse
import json
import sys
from typing import NamedTuple


class StatisticalMarkerDecision(NamedTuple):
    status: str
    marker: str | None
    transfer_allowed: bool
    reason: str


class ProjectModeDecision(NamedTuple):
    status: str
    writing_allowed: bool


class BodyBudgetDecision(NamedTuple):
    limit: int
    current: int
    replaced: int
    candidate: int
    projected: int
    remaining: int
    unit: str
    status: str
    candidate_allowed: bool


def bind_statistical_marker(
    *,
    target_analysis_id: str,
    target_marker: str | None,
    evidence_analysis_id: str,
    evidence_marker: str | None,
) -> StatisticalMarkerDecision:
    """Allow a significance marker only when evidence names the same analysis."""
    if target_analysis_id != evidence_analysis_id:
        return StatisticalMarkerDecision(
            status="UNRESOLVED",
            marker=target_marker,
            transfer_allowed=False,
            reason=(
                "A statistical marker must be supported by the same named analysis; "
                "do not transfer it from another model or table."
            ),
        )
    return StatisticalMarkerDecision(
        status="ALIGNED",
        marker=evidence_marker,
        transfer_allowed=True,
        reason="The marker and supporting value refer to the same named analysis.",
    )


def decide_project_mode(
    *,
    task: str,
    scope: str,
    journal_status: str,
    project_mode_active: bool,
) -> ProjectModeDecision:
    """Return the workflow gate after intent has been mapped to controlled labels."""
    if project_mode_active:
        return ProjectModeDecision("PROJECT_MODE_ACTIVE", True)

    project_tasks = {
        "full_manuscript_revision",
        "submission_revision",
        "submission_preparation",
        "reanalysis",
        "reviewer_response",
    }
    project_scopes = {"full_manuscript", "cross_section", "cross_session"}
    if task in project_tasks or scope in project_scopes:
        return ProjectModeDecision("PROJECT_MODE_CONFIRMATION_REQUIRED", False)

    return ProjectModeDecision("LIGHTWEIGHT_MODE", True)


def calculate_body_budget(
    *,
    limit: int,
    current: int,
    replaced: int,
    candidate: int,
    unit: str,
) -> BodyBudgetDecision:
    """Project manuscript length before accepting a full-manuscript candidate."""
    values = {
        "limit": limit,
        "current": current,
        "replaced": replaced,
        "candidate": candidate,
    }
    for name, value in values.items():
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if not unit:
        raise ValueError("unit is required")

    projected = current - replaced + candidate
    if projected < 0:
        raise ValueError("replaced content cannot exceed the current body count")
    remaining = limit - projected
    over_limit = projected > limit
    status = "COMPRESSION_REQUIRED" if over_limit else "WITHIN_LIMIT"

    # When the existing manuscript already exceeds the limit, a candidate may
    # advance only if it does not add more text to the replaced passage.
    candidate_allowed = not over_limit or candidate <= replaced
    return BodyBudgetDecision(
        limit=limit,
        current=current,
        replaced=replaced,
        candidate=candidate,
        projected=projected,
        remaining=remaining,
        unit=unit,
        status=status,
        candidate_allowed=candidate_allowed,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run psychology-paper workflow guards.")
    commands = parser.add_subparsers(dest="command", required=True)

    marker = commands.add_parser("statistical-marker")
    marker.add_argument("--target-analysis-id", required=True)
    marker.add_argument("--target-marker")
    marker.add_argument("--evidence-analysis-id", required=True)
    marker.add_argument("--evidence-marker")

    project = commands.add_parser("project-mode")
    project.add_argument("--task", required=True)
    project.add_argument("--scope", required=True)
    project.add_argument("--journal-status", required=True)
    project.add_argument("--project-mode-active", action="store_true")

    budget = commands.add_parser("body-budget")
    budget.add_argument("--limit", type=int, required=True)
    budget.add_argument("--current", type=int, required=True)
    budget.add_argument("--replaced", type=int, required=True)
    budget.add_argument("--candidate", type=int, required=True)
    budget.add_argument("--unit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "statistical-marker":
            result = bind_statistical_marker(
                target_analysis_id=args.target_analysis_id,
                target_marker=args.target_marker,
                evidence_analysis_id=args.evidence_analysis_id,
                evidence_marker=args.evidence_marker,
            )
        elif args.command == "project-mode":
            result = decide_project_mode(
                task=args.task,
                scope=args.scope,
                journal_status=args.journal_status,
                project_mode_active=args.project_mode_active,
            )
        else:
            result = calculate_body_budget(
                limit=args.limit,
                current=args.current,
                replaced=args.replaced,
                candidate=args.candidate,
                unit=args.unit,
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result._asdict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
