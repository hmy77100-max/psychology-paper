import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
COMPARE = PLUGIN_ROOT / "scripts" / "compare_analysis_results.py"
ANALYSIS_SKILL = PLUGIN_ROOT / "skills" / "analysis-adapter" / "SKILL.md"


def run_compare(authoritative: dict[str, object], verification: dict[str, object]):
    with tempfile.TemporaryDirectory(prefix="统计比较-") as raw:
        root = Path(raw)
        auth_path = root / "authoritative.json"
        verify_path = root / "verification.json"
        auth_path.write_text(json.dumps(authoritative), encoding="utf-8")
        verify_path.write_text(json.dumps(verification), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(COMPARE),
                "--authoritative", str(auth_path),
                "--verification", str(verify_path),
                "--tolerance", "0.0001",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
        return json.loads(result.stdout)


def result_payload(
    analysis_id: str = "study-3-three-way",
    scoring: str = "two-item sum",
    n: int = 115,
    f_value: float = 5.139,
) -> dict[str, object]:
    return {
        "analysis_id": analysis_id,
        "specification": {
            "data": "experiment3.xlsx",
            "scoring": scoring,
            "sample_n": n,
            "model": "2x2x2 factorial ANOVA",
            "covariates": [],
            "estimator": "ordinary least squares",
        },
        "statistics": {"F": f_value, "df1": 1, "df2": 107, "p": 0.025},
    }


class AnalysisComparisonTests(unittest.TestCase):
    def test_analysis_skill_invokes_comparison_guard_for_two_sources(self) -> None:
        self.assertIn(
            "compare_analysis_results.py",
            ANALYSIS_SKILL.read_text(encoding="utf-8"),
        )

    def test_different_analysis_ids_are_not_comparable(self) -> None:
        result = run_compare(
            result_payload(analysis_id="correlation-private"),
            result_payload(analysis_id="regression-private"),
        )
        self.assertEqual(result["status"], "NOT_COMPARABLE")
        self.assertEqual(result["reason"], "analysis identity differs")
        self.assertTrue(result["authoritative_preserved"])

    def test_different_scoring_or_sample_is_a_specification_mismatch(self) -> None:
        result = run_compare(
            result_payload(),
            result_payload(scoring="three-item sum", n=116),
        )
        self.assertEqual(result["status"], "SPECIFICATION_MISMATCH")
        self.assertEqual(set(result["mismatched_fields"]), {"scoring", "sample_n"})
        self.assertTrue(result["authoritative_preserved"])

    def test_same_specification_reports_numeric_discrepancy_without_selection(self) -> None:
        result = run_compare(result_payload(), result_payload(f_value=6.233))
        self.assertEqual(result["status"], "NUMERIC_DISCREPANCY")
        self.assertIn("F", result["differences"])
        self.assertTrue(result["authoritative_preserved"])
        self.assertNotIn("selected_result", result)

    def test_same_specification_within_tolerance_is_aligned(self) -> None:
        result = run_compare(result_payload(), result_payload(f_value=5.13904))
        self.assertEqual(result["status"], "ALIGNED")
        self.assertEqual(result["differences"], {})


if __name__ == "__main__":
    unittest.main()
