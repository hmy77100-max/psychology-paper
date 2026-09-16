import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_IDS = PLUGIN_ROOT / "scripts" / "candidate_ids.py"
AUTHORIZATION = (
    PLUGIN_ROOT / "skills" / ".shared" / "core" / "authorization-and-state.md"
)
CANDIDATE_FORMAT = (
    PLUGIN_ROOT / "skills" / ".shared" / "output" / "candidate-format.md"
)
FULL_MANUSCRIPT = (
    PLUGIN_ROOT
    / "skills"
    / "manuscript-writing"
    / "static"
    / "fragments"
    / "tasks"
    / "full-manuscript.md"
)
WRITING_WORKFLOW = (
    PLUGIN_ROOT
    / "skills"
    / "manuscript-writing"
    / "static"
    / "core"
    / "workflow.md"
)
WRITING_SKILL = PLUGIN_ROOT / "skills" / "manuscript-writing" / "SKILL.md"


class WritingSafetyTests(unittest.TestCase):
    def test_new_candidate_id_cannot_repeat_an_existing_artifact_id(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CANDIDATE_IDS),
                "--used", "10000",
                "--used", "41726",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertRegex(payload["candidate_id"], r"^\d{5}$")
        self.assertNotIn(payload["candidate_id"], {"10000", "41726"})
        self.assertFalse(payload["reused_for_revision"])

    def test_revision_keeps_the_original_candidate_id(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CANDIDATE_IDS),
                "--used", "41726",
                "--revision-of", "41726",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONUTF8": "1"},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["candidate_id"], "41726")
        self.assertTrue(payload["reused_for_revision"])

    def test_approval_language_uses_generic_intents_and_advances(self) -> None:
        text = AUTHORIZATION.read_text(encoding="utf-8")
        self.assertIn("APPROVE_CURRENT_AND_ADVANCE", text)
        self.assertIn("下一步", text)
        self.assertIn("generic intent", text)
        self.assertIn("user-specific", text)

    def test_full_manuscript_order_is_body_then_abstract_then_keywords(self) -> None:
        text = FULL_MANUSCRIPT.read_text(encoding="utf-8")
        self.assertIn("Body sections → Abstract → Keywords", text)

    def test_user_facing_output_is_natural_language_and_preview_is_short(self) -> None:
        text = CANDIDATE_FORMAT.read_text(encoding="utf-8")
        self.assertIn("Do not expose internal field names", text)
        self.assertIn("300 Chinese characters", text)

    def test_literature_dependent_writing_stops_for_user_choice(self) -> None:
        text = WRITING_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("literature decision gate", text)
        self.assertIn("use only the current manuscript literature", text)
        self.assertIn("search for candidate literature", text)
        self.assertIn("write approved new literature", text)

    def test_evidence_caveat_is_not_repeated_across_sections(self) -> None:
        text = WRITING_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("one manuscript home", text)
        self.assertIn("do not repeat the full audit explanation", text)

    def test_writing_skill_allocates_candidate_ids(self) -> None:
        text = WRITING_SKILL.read_text(encoding="utf-8")
        self.assertIn("candidate_ids.py", text)


if __name__ == "__main__":
    unittest.main()
