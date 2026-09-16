import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
INIT_PROJECT = PLUGIN_ROOT / "scripts" / "init_project.py"
REGISTRY = PLUGIN_ROOT / "scripts" / "analysis_registry.py"
VALIDATE_PROJECT = PLUGIN_ROOT / "scripts" / "validate_project.py"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        check=False,
    )


def read_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    return json.loads(text[4:end])


class AnalysisRegistryTests(unittest.TestCase):
    def _project(self, root: Path) -> tuple[Path, str]:
        manuscript = root / "paper.txt"
        original = "authoritative manuscript"
        manuscript.write_text(original, encoding="utf-8")
        result = run_script(
            INIT_PROJECT,
            "--project-root", str(root),
            "--manuscript", str(manuscript),
            "--confirm-create",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return manuscript, original

    def test_registry_creation_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            result = run_script(REGISTRY, "init", "--project-root", str(root))
            self.assertEqual(result.returncode, 2)
            self.assertIn("--confirm-create is required", result.stderr)
            self.assertFalse(
                (root / ".psychology-paper" / "ANALYSIS_REGISTRY.md").exists()
            )

    def test_registry_initialization_updates_project_state_not_manuscript(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            manuscript, original = self._project(root)
            result = run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            registry_path = root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            self.assertTrue(registry_path.is_file())
            registry = read_frontmatter(registry_path)
            self.assertEqual(registry["schema"], "psychology-paper-analysis-registry")
            self.assertEqual(registry["analyses"], [])
            project = read_frontmatter(root / ".psychology-paper" / "PROJECT.md")
            self.assertEqual(
                project["optional_state_files"]["analysis_registry"],
                str(registry_path.resolve()),
            )
            self.assertEqual(manuscript.read_text(encoding="utf-8"), original)

    def test_result_is_not_registered_without_user_adoption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            self.assertEqual(
                run_script(
                    REGISTRY,
                    "init",
                    "--project-root", str(root),
                    "--confirm-create",
                ).returncode,
                0,
            )
            entry_path = root / "candidate.json"
            entry_path.write_text(
                json.dumps(self._valid_entry(), ensure_ascii=False), encoding="utf-8"
            )
            result = run_script(
                REGISTRY,
                "add",
                "--project-root", str(root),
                "--entry", str(entry_path),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--confirm-adopt is required", result.stderr)
            registry = read_frontmatter(
                root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            )
            self.assertEqual(registry["analyses"], [])

    def test_adopted_result_with_one_formal_source_is_registered(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            entry_path = root / "adopted.json"
            entry_path.write_text(
                json.dumps(self._valid_entry(), ensure_ascii=False), encoding="utf-8"
            )
            result = run_script(
                REGISTRY,
                "add",
                "--project-root", str(root),
                "--entry", str(entry_path),
                "--confirm-adopt",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            registry = read_frontmatter(
                root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            )
            self.assertEqual(len(registry["analyses"]), 1)
            self.assertEqual(registry["analyses"][0]["adoption_status"], "USER_ADOPTED")

    def test_adopted_result_rejects_two_formal_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            entry = self._valid_entry()
            entry["sources"].append(
                {"role": "AUTHORITATIVE", "software": "Python", "version": "3.13"}
            )
            entry_path = root / "conflict.json"
            entry_path.write_text(json.dumps(entry), encoding="utf-8")
            result = run_script(
                REGISTRY,
                "add",
                "--project-root", str(root),
                "--entry", str(entry_path),
                "--confirm-adopt",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("exactly one AUTHORITATIVE source", result.stderr)

    def test_project_validation_rejects_unadopted_registry_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            registry_path = root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            text = registry_path.read_text(encoding="utf-8")
            end = text.find("\n---\n", 4)
            registry = json.loads(text[4:end])
            entry = self._valid_entry()
            entry["adoption_status"] = "CANDIDATE"
            registry["analyses"] = [entry]
            registry_path.write_text(
                "---\n"
                + json.dumps(registry, ensure_ascii=False, indent=2)
                + "\n---\n"
                + text[end + 5 :],
                encoding="utf-8",
            )
            result = run_script(
                VALIDATE_PROJECT, "--project-root", str(root)
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("analysis registry contains an unadopted entry", result.stdout)

    @staticmethod
    def _valid_entry() -> dict[str, object]:
        return {
            "analysis_id": "study-1-correlation-private-peb",
            "research_question": "Association between psychological distance and private PEB",
            "design_tags": ["survey"],
            "observation_unit": "participant",
            "field_map": {"predictor": "distance", "outcome": "private_peb"},
            "scoring": "confirmed composite scores",
            "sample": {"n": 207, "exclusions": "author-confirmed rules"},
            "model": "Pearson correlation",
            "software": {"name": "SPSS", "version": "29"},
            "estimation": "two-tailed",
            "bootstrap": None,
            "random_seed": None,
            "sources": [
                {"role": "AUTHORITATIVE", "software": "SPSS", "version": "29"}
            ],
            "formal_output": "output/study-1-correlation.spv",
            "manuscript_locations": ["Study 1 Results", "Table 1"],
        }


if __name__ == "__main__":
    unittest.main()
