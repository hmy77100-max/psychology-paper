import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LOADER_PATH = PLUGIN_ROOT / "scripts" / "load_skill_resources.py"
IMPLEMENTED_SKILLS = (
    "psychology-paper",
    "journal-fit-style",
    "evidence-audit",
    "manuscript-writing",
)
DIRECT_MARKDOWN_RESOURCE_LINK = re.compile(
    r"\]\((?!https?://|file:|/|[A-Za-z]:[\\/])[^)]+\.md(?:#[^)]+)?\)",
    re.IGNORECASE,
)


def import_loader():
    if not LOADER_PATH.is_file():
        raise AssertionError(f"resource loader is missing: {LOADER_PATH}")
    spec = importlib.util.spec_from_file_location("load_skill_resources", LOADER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot import resource loader: {LOADER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResourceLoaderTests(unittest.TestCase):
    def test_entrypoint_guard_recognizes_bare_relative_markdown_links(self) -> None:
        self.assertIsNotNone(
            DIRECT_MARKDOWN_RESOURCE_LINK.search(
                "Read [rules](static/core/routing-principles.md)."
            )
        )
        self.assertIsNone(
            DIRECT_MARKDOWN_RESOURCE_LINK.search(
                "Use [loader](../../scripts/load_skill_resources.py)."
            )
        )

    def test_skill_entrypoints_use_only_the_deterministic_loader_for_resources(self) -> None:
        for skill in IMPLEMENTED_SKILLS:
            entry = PLUGIN_ROOT / "skills" / skill / "SKILL.md"
            text = entry.read_text(encoding="utf-8")
            self.assertIn("../../scripts/load_skill_resources.py", text, skill)
            self.assertIn(f"--skill {skill}", text, skill)
            self.assertIsNone(DIRECT_MARKDOWN_RESOURCE_LINK.search(text), skill)

    def test_cli_loads_exact_groups_from_an_arbitrary_chinese_working_directory(self) -> None:
        self.assertTrue(LOADER_PATH.is_file(), LOADER_PATH)
        with tempfile.TemporaryDirectory() as temp_dir:
            cwd = Path(temp_dir) / "任意论文目录"
            cwd.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(LOADER_PATH),
                    "--skill",
                    "psychology-paper",
                    "--select",
                    "conditional_loads.project_mode",
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("routing-principles.md", completed.stdout)
        self.assertIn("authorization.md", completed.stdout)
        self.assertIn("project-mode.md", completed.stdout)
        self.assertNotIn("error-recovery.md", completed.stdout)
        self.assertNotIn("task-routing.md", completed.stdout)

    def test_loader_reads_only_manifest_selected_resources_without_traversal(self) -> None:
        loader = import_loader()
        with patch.object(Path, "rglob", side_effect=AssertionError("recursive traversal used")), patch.object(
            Path, "glob", side_effect=AssertionError("directory glob used")
        ):
            result = loader.load_skill_resources(
                skill="manuscript-writing",
                selectors=["axes.section.discussion"],
                max_chars=12_000,
            )

        names = [resource.relative_path for resource in result.resources]
        self.assertIn("static/fragments/sections/discussion.md", names)
        self.assertNotIn("static/fragments/sections/introduction.md", names)
        self.assertNotIn("static/fragments/sections/results.md", names)

    def test_unknown_selector_fails_without_fuzzy_matching(self) -> None:
        loader = import_loader()
        with self.assertRaisesRegex(loader.ResourceResolutionError, "unknown resource selector"):
            loader.load_skill_resources(
                skill="psychology-paper",
                selectors=["conditional_loads.discussion"],
                max_chars=12_000,
            )

    def test_missing_declared_resource_is_a_bounded_integrity_failure(self) -> None:
        loader = import_loader()
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_root = Path(temp_dir)
            skill_root = plugin_root / "skills" / "example-skill"
            skill_root.mkdir(parents=True)
            (skill_root / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "schema": "psychology-paper-skill-manifest",
                        "version": 1,
                        "skill": "example-skill",
                        "always_load": ["./static/core/missing.md"],
                    }
                ),
                encoding="utf-8",
            )
            unrelated = plugin_root / "somewhere-else" / "missing.md"
            unrelated.parent.mkdir()
            unrelated.write_text("wrong fallback", encoding="utf-8")

            with patch.object(Path, "rglob", side_effect=AssertionError("recursive traversal used")), patch.object(
                Path, "glob", side_effect=AssertionError("directory glob used")
            ):
                with self.assertRaisesRegex(
                    loader.ResourceResolutionError,
                    r"declared resource is missing.*static/core/missing\.md",
                ):
                    loader.load_skill_resources(
                        skill="example-skill",
                        selectors=[],
                        max_chars=12_000,
                        plugin_root=plugin_root,
                    )

    def test_character_budget_blocks_output_before_large_context_is_returned(self) -> None:
        loader = import_loader()
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_root = Path(temp_dir)
            skill_root = plugin_root / "skills" / "example-skill"
            resource = skill_root / "static" / "core" / "large.md"
            resource.parent.mkdir(parents=True)
            resource.write_text("x" * 101, encoding="utf-8")
            (skill_root / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "schema": "psychology-paper-skill-manifest",
                        "version": 1,
                        "skill": "example-skill",
                        "always_load": ["./static/core/large.md"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(loader.ResourceBudgetError, "101.*100"):
                loader.load_skill_resources(
                    skill="example-skill",
                    selectors=[],
                    max_chars=100,
                    plugin_root=plugin_root,
                )

    def test_resource_cannot_escape_the_plugin_root(self) -> None:
        loader = import_loader()
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin_root = Path(temp_dir) / "plugin"
            skill_root = plugin_root / "skills" / "example-skill"
            skill_root.mkdir(parents=True)
            outside = plugin_root.parent / "outside.md"
            outside.write_text("outside", encoding="utf-8")
            (skill_root / "manifest.yaml").write_text(
                json.dumps(
                    {
                        "schema": "psychology-paper-skill-manifest",
                        "version": 1,
                        "skill": "example-skill",
                        "always_load": ["../../../outside.md"],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(loader.ResourceResolutionError, "escapes plugin root"):
                loader.load_skill_resources(
                    skill="example-skill",
                    selectors=[],
                    max_chars=12_000,
                    plugin_root=plugin_root,
                )


if __name__ == "__main__":
    unittest.main()
