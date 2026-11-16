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
    def test_legacy_prose_only_is_not_statistical_alignment(self):
        a=result_payload();a['statistics']={'note':'no statistics'}
        self.assertNotEqual(run_compare(a,a)['status'],'ALIGNED')

    def test_legacy_string_p_is_not_numeric_evidence(self):
        a=result_payload();a['statistics']={'p':'not-a-p-value','note':'no estimate'}
        self.assertNotEqual(run_compare(a,a)['status'],'ALIGNED')

    def test_tiny_p_values_do_not_use_broad_absolute_tolerance(self):
        a=result_payload();b=result_payload()
        a['statistics']['p']=1e-12;b['statistics']['p']=1e-8
        self.assertEqual(run_compare(a,b)['status'],'NUMERIC_DISCREPANCY')
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




class ComparisonGuardTests(unittest.TestCase):
    def test_empty_records_and_invalid_numbers_never_align(self):
        sys.path.insert(0, str(PLUGIN_ROOT / 'scripts'))
        from compare_analysis_results import compare_results
        self.assertEqual(compare_results({}, {}, tolerance=0)['status'], 'NOT_COMPARABLE')
        for number in (True, float('nan'), float('inf'), -0.1, 1.1):
            a=result_payload(); a['statistics']['p']=number
            self.assertEqual(compare_results(a,a,tolerance=0)['status'],'NOT_COMPARABLE')
        with self.assertRaises(ValueError): compare_results(result_payload(),result_payload(),tolerance=float('inf'))

    def test_missing_and_null_and_candidate_modes(self):
        sys.path.insert(0, str(PLUGIN_ROOT / 'scripts'))
        from compare_analysis_results import compare_results
        a=result_payload(); b=result_payload(); b['specification']['optional']=None
        self.assertEqual(compare_results(a,b,tolerance=0)['status'],'SPECIFICATION_MISMATCH')
        b=result_payload(scoring='different')
        result=compare_results(a,b,tolerance=0,mode='candidates')
        self.assertEqual(result['status'],'CANDIDATE_SPECIFICATION_CHANGED')
        self.assertEqual(result['adoption_status'],'CANDIDATE')

class ModernComparisonTests(unittest.TestCase):
    def test_execution_metadata_ignored_and_candidate_estimands_not_aligned(self):
        sys.path.insert(0, str(PLUGIN_ROOT / 'scripts'))
        from compare_analysis_results import compare_results
        a=result_payload();b=result_payload()
        a['specification']['execution_environment']='one';b['specification']['execution_environment']='two'
        self.assertEqual(compare_results(a,b,tolerance=0)['status'],'ALIGNED')
        a['statistics']['optional']=None
        self.assertEqual(compare_results(a,b,tolerance=0)['status'],'NUMERIC_DISCREPANCY')

class ComparisonProvenanceTests(unittest.TestCase):
    def test_shared_engine_is_not_independent_verification(self):
        sys.path.insert(0,str(PLUGIN_ROOT/'scripts'))
        from compare_analysis_results import compare_results
        a=result_payload();b=result_payload()
        a['execution_provenance']={'engine':'controlled-python'}
        b['execution_provenance']={'engine':'controlled-python'}
        self.assertEqual(compare_results(a,b,tolerance=0)['verification_level'],'SAME_ENGINE_REPRODUCTION')


if __name__ == "__main__":
    unittest.main()
