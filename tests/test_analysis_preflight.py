import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = PLUGIN_ROOT / "scripts" / "analysis_preflight.py"
ROUTER_SKILL = PLUGIN_ROOT / "skills" / "psychology-paper" / "SKILL.md"
ROUTING_REFERENCE = (
    PLUGIN_ROOT / "skills" / "psychology-paper" / "references" / "task-routing.md"
)


def run_preflight(specification: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="统计预检-") as raw:
        path = Path(raw) / "spec.json"
        path.write_text(
            json.dumps(specification, ensure_ascii=False), encoding="utf-8"
        )
        result = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--spec", str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
        return json.loads(result.stdout)


class AnalysisPreflightTests(unittest.TestCase):
    def test_router_exposes_analysis_adapter_for_recalculation(self) -> None:
        self.assertIn("analysis-adapter", ROUTER_SKILL.read_text(encoding="utf-8"))
        self.assertIn("analysis-adapter", ROUTING_REFERENCE.read_text(encoding="utf-8"))

    def test_missing_design_stops_before_column_guessing(self) -> None:
        result = run_preflight({"field_map": [], "sources": []})
        self.assertEqual(result["status"], "NEEDS_DESIGN")
        self.assertFalse(result["analysis_allowed"])
        self.assertIn("研究设计", result["user_questions"][0])

    def test_inferred_field_mapping_requires_author_confirmation(self) -> None:
        result = run_preflight(
            {
                "design": {
                    "design_tags": ["survey"],
                    "observation_unit": "participant",
                    "research_question_type": "association",
                    "variables": [{"name": "private_peb", "role": "outcome"}],
                },
                "field_map": [
                    {
                        "variable": "private_peb",
                        "column": "Q17",
                        "confirmation_status": "INFERRED",
                    }
                ],
                "sources": [
                    {
                        "role": "AUTHORITATIVE",
                        "software": "SPSS",
                        "version": "29",
                    }
                ],
            }
        )
        self.assertEqual(result["status"], "NEEDS_FIELD_CONFIRMATION")
        self.assertFalse(result["analysis_allowed"])
        self.assertEqual(result["unresolved_variables"], ["private_peb"])
        self.assertTrue(
            any("未识别" in question for question in result["user_questions"])
        )

    def test_factorial_design_routes_to_interaction_capable_methods(self) -> None:
        result = run_preflight(
            {
                "design": {
                    "design_tags": ["experiment", "factorial-between-subjects"],
                    "observation_unit": "participant",
                    "research_question_type": "factorial_effects",
                    "variables": [
                        {"name": "condition_a", "role": "independent"},
                        {"name": "condition_b", "role": "independent"},
                        {"name": "donation", "role": "outcome"},
                    ],
                },
                "field_map": [
                    {
                        "variable": "condition_a",
                        "column": "A",
                        "confirmation_status": "USER_CONFIRMED",
                    },
                    {
                        "variable": "condition_b",
                        "column": "B",
                        "confirmation_status": "USER_CONFIRMED",
                    },
                    {
                        "variable": "donation",
                        "column": "Y",
                        "confirmation_status": "USER_CONFIRMED",
                    },
                ],
                "sources": [
                    {
                        "role": "AUTHORITATIVE",
                        "software": "SPSS",
                        "version": "29",
                    },
                    {
                        "role": "VERIFICATION",
                        "software": "Python",
                        "version": "3.13",
                    },
                ],
            }
        )
        self.assertEqual(result["status"], "READY_FOR_ANALYSIS")
        self.assertTrue(result["analysis_allowed"])
        self.assertIn("factorial_anova_or_linear_model", result["method_candidates"])
        self.assertIn("interaction_decomposition", result["method_candidates"])
        self.assertEqual(result["formal_software"], "SPSS")
        self.assertEqual(result["verification_software"], "Python")

    def test_two_authoritative_sources_are_rejected(self) -> None:
        result = run_preflight(
            {
                "design": {
                    "design_tags": ["survey"],
                    "observation_unit": "participant",
                    "research_question_type": "association",
                    "variables": [{"name": "score", "role": "outcome"}],
                },
                "field_map": [
                    {
                        "variable": "score",
                        "column": "score",
                        "confirmation_status": "USER_CONFIRMED",
                    }
                ],
                "sources": [
                    {"role": "AUTHORITATIVE", "software": "SPSS", "version": "29"},
                    {"role": "AUTHORITATIVE", "software": "Python", "version": "3.13"},
                ],
            }
        )
        self.assertEqual(result["status"], "SOURCE_CONFLICT")
        self.assertFalse(result["analysis_allowed"])

    def test_tabular_data_without_original_software_requires_user_choice(self) -> None:
        result = run_preflight(
            {
                "design": {
                    "design_tags": ["survey"],
                    "observation_unit": "participant",
                    "research_question_type": "association",
                    "variables": [{"name": "score", "role": "outcome"}],
                },
                "field_map": [
                    {
                        "variable": "score",
                        "column": "score",
                        "confirmation_status": "USER_CONFIRMED",
                    }
                ],
                "sources": [{"role": "DATA_ONLY", "format": "xlsx"}],
            }
        )
        self.assertEqual(result["status"], "NEEDS_FORMAL_SOFTWARE_CHOICE")
        self.assertFalse(result["analysis_allowed"])
        self.assertEqual(result["software_candidates"], ["Python", "R"])
        self.assertTrue(any("正式分析软件" in q for q in result["user_questions"]))


if __name__ == "__main__":
    unittest.main()
