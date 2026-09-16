import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
INIT = PLUGIN_ROOT / "scripts" / "init_project.py"
VALIDATE = PLUGIN_ROOT / "scripts" / "validate_project.py"
RULES = PLUGIN_ROOT / "skills" / ".shared" / "core" / "state-consistency.md"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        check=False,
    )


def read_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError("state file lacks frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError("state file frontmatter is unclosed")
    return json.loads(text[4:end]), text[end + 5:]


def write_frontmatter(path: Path, state: dict[str, object], body: str) -> None:
    path.write_text(
        "---\n" + json.dumps(state, ensure_ascii=False, indent=2) + "\n---\n" + body,
        encoding="utf-8",
    )


class ProjectToolTests(unittest.TestCase):
    def test_init_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="心理学项目-") as raw:
            root = Path(raw)
            manuscript = root / "当前稿件.txt"
            manuscript.write_text("test", encoding="utf-8")
            result = run_script(
                INIT,
                "--project-root", str(root),
                "--manuscript", str(manuscript),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--confirm-create is required", result.stderr)
            self.assertFalse((root / ".psychology-paper" / "PROJECT.md").exists())

    def test_init_creates_state_without_touching_manuscript(self) -> None:
        with tempfile.TemporaryDirectory(prefix="心理学项目-") as raw:
            root = Path(raw)
            manuscript = root / "当前稿件.txt"
            original = "不得修改的正文"
            manuscript.write_text(original, encoding="utf-8")
            result = run_script(
                INIT,
                "--project-root", str(root),
                "--manuscript", str(manuscript),
                "--confirm-create",
                "--journal", "Journal of Environmental Psychology",
            )
            self.assertIsInstance(result.stdout, str)
            self.assertIsInstance(result.stderr, str)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(manuscript.read_text(encoding="utf-8"), original)
            state_path = root / ".psychology-paper" / "PROJECT.md"
            self.assertTrue(state_path.exists())
            state, _ = read_frontmatter(state_path)
            self.assertEqual(state["authoritative_manuscript"], str(manuscript.resolve()))
            self.assertEqual(state["journal"]["status"], "USER_CONFIRMED")
            self.assertEqual(
                state["body_budget"],
                {
                    "limit": None,
                    "unit": None,
                    "counting_scope": None,
                    "current": None,
                    "status": "UNSET",
                },
            )
            self.assertEqual(state["issued_candidate_ids"], [])
            validation = run_script(VALIDATE, "--project-root", str(root))
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
            self.assertIn("Project state valid", validation.stdout)

    def test_init_refuses_to_overwrite_existing_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manuscript = root / "paper.txt"
            manuscript.write_text("paper", encoding="utf-8")
            args = (
                "--project-root", str(root),
                "--manuscript", str(manuscript),
                "--confirm-create",
            )
            self.assertEqual(run_script(INIT, *args).returncode, 0)
            second = run_script(INIT, *args)
            self.assertEqual(second.returncode, 3)
            self.assertIn("already exists", second.stderr)

    def test_init_records_confirmed_journal_body_budget(self) -> None:
        with tempfile.TemporaryDirectory(prefix="正文预算-") as raw:
            root = Path(raw)
            manuscript = root / "投稿稿.txt"
            manuscript.write_text("paper", encoding="utf-8")
            result = run_script(
                INIT,
                "--project-root", str(root),
                "--manuscript", str(manuscript),
                "--confirm-create",
                "--journal", "心理与行为研究",
                "--body-limit", "8000",
                "--body-unit", "characters",
                "--body-counting-scope", "main_text",
                "--current-body-count", "8455",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            state, _ = read_frontmatter(root / ".psychology-paper" / "PROJECT.md")
            self.assertEqual(
                state["body_budget"],
                {
                    "limit": 8000,
                    "unit": "characters",
                    "counting_scope": "main_text",
                    "current": 8455,
                    "status": "COMPRESSION_REQUIRED",
                },
            )

    def test_validator_uses_shared_rule_sc_001(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manuscript = root / "paper.txt"
            manuscript.write_text("paper", encoding="utf-8")
            self.assertEqual(
                run_script(
                    INIT,
                    "--project-root", str(root),
                    "--manuscript", str(manuscript),
                    "--confirm-create",
                ).returncode,
                0,
            )
            state_path = root / ".psychology-paper" / "PROJECT.md"
            state, body = read_frontmatter(state_path)
            state["current_action"] = {
                "decision_status": "CANDIDATE",
                "write_permission": "WRITE_ALLOWED",
                "source_role": "AUTHORITATIVE",
                "evidence_status": "ALIGNED",
                "evidence_boundary_applied": True,
                "patch_status": "NOT_APPLIED",
                "patch_receipt_present": False,
                "required_verification_complete": False,
                "new_patch_requested": False,
                "check_status": "NOT_APPLICABLE",
                "risk_level": "R4",
                "issue_resolved": True,
                "explicit_output_target": True,
            }
            write_frontmatter(state_path, state, body)
            result = run_script(VALIDATE, "--project-root", str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("SC-001", result.stdout)
            self.assertIn(str(RULES.resolve()), result.stdout)

    def test_validator_rejects_duplicate_candidate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manuscript = root / "paper.txt"
            manuscript.write_text("paper", encoding="utf-8")
            self.assertEqual(
                run_script(
                    INIT,
                    "--project-root", str(root),
                    "--manuscript", str(manuscript),
                    "--confirm-create",
                ).returncode,
                0,
            )
            state_path = root / ".psychology-paper" / "PROJECT.md"
            state, body = read_frontmatter(state_path)
            state["issued_candidate_ids"] = ["41726", "41726"]
            write_frontmatter(state_path, state, body)
            result = run_script(VALIDATE, "--project-root", str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("issued_candidate_ids", result.stdout)

    def test_state_rules_have_stable_unique_ids_and_supported_operators(self) -> None:
        rules, _ = read_frontmatter(RULES)
        rule_list = rules["rules"]
        ids = [rule["id"] for rule in rule_list]
        self.assertEqual(ids, [f"SC-{index:03d}" for index in range(1, 9)])
        self.assertEqual(len(ids), len(set(ids)))
        supported = {"eq", "ne", "in", "not_in", "exists"}
        for rule in rule_list:
            for atom in rule.get("all", []) + rule.get("any", []):
                self.assertIn(atom["op"], supported, rule["id"])


if __name__ == "__main__":
    unittest.main()
