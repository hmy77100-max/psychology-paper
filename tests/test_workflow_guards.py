import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
GUARDS = PLUGIN_ROOT / "scripts" / "workflow_guards.py"
ROUTER_SKILL = PLUGIN_ROOT / "skills" / "psychology-paper" / "SKILL.md"
AUDIT_SKILL = PLUGIN_ROOT / "skills" / "evidence-audit" / "SKILL.md"
WRITING_SKILL = PLUGIN_ROOT / "skills" / "manuscript-writing" / "SKILL.md"


def load_guards():
    spec = importlib.util.spec_from_file_location("workflow_guards", GUARDS)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load workflow guards: {GUARDS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowGuardTests(unittest.TestCase):
    def test_guard_cli_exposes_project_mode_decision(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(GUARDS),
                "project-mode",
                "--task", "submission_revision",
                "--scope", "full_manuscript",
                "--journal-status", "USER_CONFIRMED",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PROJECT_MODE_CONFIRMATION_REQUIRED")
        self.assertFalse(payload["writing_allowed"])

    def test_skill_entrypoints_route_through_shared_guards(self) -> None:
        self.assertIn(
            "workflow_guards.py project-mode",
            ROUTER_SKILL.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "workflow_guards.py statistical-marker",
            AUDIT_SKILL.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "workflow_guards.py body-budget",
            WRITING_SKILL.read_text(encoding="utf-8"),
        )

    def test_statistical_marker_cannot_borrow_support_from_another_analysis(self) -> None:
        guards = load_guards()
        result = guards.bind_statistical_marker(
            target_analysis_id="zero-order-correlation:private-sphere-behavior",
            target_marker=None,
            evidence_analysis_id="multiple-regression:private-sphere-behavior",
            evidence_marker="**",
        )
        self.assertEqual(result.status, "UNRESOLVED")
        self.assertIsNone(result.marker)
        self.assertFalse(result.transfer_allowed)
        self.assertIn("same named analysis", result.reason)

    def test_full_manuscript_submission_revision_requires_project_mode(self) -> None:
        guards = load_guards()
        result = guards.decide_project_mode(
            task="submission_revision",
            scope="full_manuscript",
            journal_status="USER_CONFIRMED",
            project_mode_active=False,
        )
        self.assertEqual(result.status, "PROJECT_MODE_CONFIRMATION_REQUIRED")
        self.assertFalse(result.writing_allowed)

    def test_local_sentence_edit_does_not_force_project_mode(self) -> None:
        guards = load_guards()
        result = guards.decide_project_mode(
            task="language_edit",
            scope="single_sentence",
            journal_status="USER_CONFIRMED",
            project_mode_active=False,
        )
        self.assertEqual(result.status, "LIGHTWEIGHT_MODE")
        self.assertTrue(result.writing_allowed)

    def test_over_limit_full_manuscript_candidate_must_not_expand_body(self) -> None:
        guards = load_guards()
        result = guards.calculate_body_budget(
            limit=8000,
            current=8455,
            replaced=300,
            candidate=450,
            unit="characters",
        )
        self.assertEqual(result.projected, 8605)
        self.assertEqual(result.remaining, -605)
        self.assertEqual(result.status, "COMPRESSION_REQUIRED")
        self.assertFalse(result.candidate_allowed)

    def test_compressing_candidate_is_allowed_while_still_over_limit(self) -> None:
        guards = load_guards()
        result = guards.calculate_body_budget(
            limit=8000,
            current=8455,
            replaced=600,
            candidate=450,
            unit="characters",
        )
        self.assertEqual(result.projected, 8305)
        self.assertEqual(result.remaining, -305)
        self.assertEqual(result.status, "COMPRESSION_REQUIRED")
        self.assertTrue(result.candidate_allowed)


if __name__ == "__main__":
    unittest.main()
