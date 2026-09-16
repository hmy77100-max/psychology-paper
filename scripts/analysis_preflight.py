from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def _result(
    status: str,
    *,
    analysis_allowed: bool,
    user_questions: list[str] | None = None,
    unresolved_variables: list[str] | None = None,
    method_candidates: list[str] | None = None,
    formal_software: str | None = None,
    verification_software: str | None = None,
    software_candidates: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "analysis_allowed": analysis_allowed,
        "user_questions": user_questions or [],
        "unresolved_variables": unresolved_variables or [],
        "method_candidates": method_candidates or [],
        "formal_software": formal_software,
        "verification_software": verification_software,
        "software_candidates": software_candidates or [],
    }


def _design_is_complete(design: object) -> bool:
    if not isinstance(design, dict):
        return False
    required = ("design_tags", "observation_unit", "research_question_type", "variables")
    if any(not design.get(key) for key in required):
        return False
    variables = design.get("variables")
    return isinstance(variables, list) and all(
        isinstance(variable, dict) and variable.get("name") and variable.get("role")
        for variable in variables
    )


def _method_candidates(design: dict[str, Any]) -> list[str]:
    tags = set(design.get("design_tags", []))
    question = design.get("research_question_type")
    if question == "factorial_effects" or "factorial-between-subjects" in tags:
        return ["factorial_anova_or_linear_model", "interaction_decomposition"]
    if "repeated-measures" in tags or "mixed-design" in tags:
        return ["repeated_measures_or_mixed_effects"]
    if "longitudinal" in tags:
        return ["longitudinal_or_mixed_effects"]
    if question == "association":
        return ["correlation_or_regression"]
    if question in {"indirect_effect", "mediation"}:
        return ["regression_indirect_effect_or_sem"]
    if question == "group_difference":
        return ["t_test_or_linear_model"]
    return ["method_requires_user_confirmation"]


def evaluate_preflight(specification: dict[str, Any]) -> dict[str, Any]:
    design = specification.get("design")
    if not _design_is_complete(design):
        return _result(
            "NEEDS_DESIGN",
            analysis_allowed=False,
            user_questions=["请提供或确认研究设计，再核对数据字段。"],
        )

    assert isinstance(design, dict)
    field_map = specification.get("field_map")
    mappings = {
        mapping.get("variable"): mapping
        for mapping in field_map
        if isinstance(mapping, dict) and mapping.get("variable")
    } if isinstance(field_map, list) else {}
    unresolved = [
        variable["name"]
        for variable in design["variables"]
        if variable["name"] not in mappings
        or mappings[variable["name"]].get("confirmation_status") != "USER_CONFIRMED"
    ]
    if unresolved:
        return _result(
            "NEEDS_FIELD_CONFIRMATION",
            analysis_allowed=False,
            unresolved_variables=unresolved,
            user_questions=[
                "请确认这些理论变量与数据字段的对应关系：" + "、".join(unresolved) + "。",
                "是否还有未识别的重要字段、分组变量或重复测量层级？",
            ],
        )

    sources = specification.get("sources")
    sources = sources if isinstance(sources, list) else []
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
    data_only = [
        source
        for source in sources
        if isinstance(source, dict) and source.get("role") == "DATA_ONLY"
    ]
    if not authoritative and data_only and all(
        str(source.get("format", "")).lower() in {"csv", "xlsx", "xls"}
        for source in data_only
    ):
        return _result(
            "NEEDS_FORMAL_SOFTWARE_CHOICE",
            analysis_allowed=False,
            software_candidates=["Python", "R"],
            user_questions=[
                "现有材料只有透明表格数据。请选择 Python 或 R 作为正式分析软件。"
            ],
        )
    if len(authoritative) != 1 or len(verification) > 1:
        return _result(
            "SOURCE_CONFLICT",
            analysis_allowed=False,
            user_questions=["请指定一个正式分析来源，并至多指定一个独立复核来源。"],
        )

    return _result(
        "READY_FOR_ANALYSIS",
        analysis_allowed=True,
        method_candidates=_method_candidates(design),
        formal_software=authoritative[0].get("software"),
        verification_software=(verification[0].get("software") if verification else None),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preflight a psychology analysis specification.")
    parser.add_argument("--spec", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.spec).expanduser().resolve()
    try:
        specification = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(specification, dict):
        print("analysis specification must be a JSON object", file=sys.stderr)
        return 2
    print(json.dumps(evaluate_preflight(specification), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
