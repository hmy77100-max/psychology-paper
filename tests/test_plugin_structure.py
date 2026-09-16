import json
import re
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTED_SKILLS = [
    "psychology-paper",
    "journal-fit-style",
    "evidence-audit",
    "manuscript-writing",
    "analysis-adapter",
]
PLAN = PLUGIN_ROOT / "docs" / "superpowers" / "plans" / "2026-09-11-psychology-paper-stage-1a.md"


def referenced_paths(value: object) -> list[str]:
    if isinstance(value, str) and value.startswith(("./", "../")):
        return [value]
    if isinstance(value, list):
        return [item for child in value for item in referenced_paths(child)]
    if isinstance(value, dict):
        return [item for child in value.values() for item in referenced_paths(child)]
    return []


class PluginStructureTests(unittest.TestCase):
    def test_plugin_manifest_declares_stage_1a_skill_root(self) -> None:
        manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "psychology-paper")
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("apps", manifest)
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("hooks", manifest)

    def test_stage_2_analysis_keeps_other_deferred_modules_closed(self) -> None:
        forbidden = [
            "document-patcher",
            "literature-map",
            "review-revision",
            "submission-check",
        ]
        for name in forbidden:
            self.assertFalse((PLUGIN_ROOT / "skills" / name).exists(), name)

    def test_implemented_skills_have_valid_entry_files(self) -> None:
        for name in IMPLEMENTED_SKILLS:
            skill_dir = PLUGIN_ROOT / "skills" / name
            skill_path = skill_dir / "SKILL.md"
            manifest_path = skill_dir / "manifest.yaml"
            agent_path = skill_dir / "agents" / "openai.yaml"
            self.assertTrue(skill_path.is_file(), skill_path)
            self.assertTrue(manifest_path.is_file(), manifest_path)
            self.assertTrue(agent_path.is_file(), agent_path)
            text = skill_path.read_text(encoding="utf-8")
            frontmatter = re.search(r"\A---\n(.*?)\n---", text, re.DOTALL)
            self.assertIsNotNone(frontmatter, skill_path)
            self.assertIn(f"name: {name}", frontmatter.group(1))
            description = re.search(r"^description:\s*(.+)$", frontmatter.group(1), re.MULTILINE)
            self.assertIsNotNone(description, skill_path)
            self.assertGreaterEqual(len(description.group(1).strip()), 40)

    def test_manifest_paths_resolve(self) -> None:
        for name in IMPLEMENTED_SKILLS:
            skill_dir = PLUGIN_ROOT / "skills" / name
            manifest_path = skill_dir / "manifest.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["skill"], name)
            for raw_path in referenced_paths(manifest):
                resolved = (skill_dir / raw_path).resolve()
                self.assertTrue(resolved.is_file(), f"{manifest_path}: {raw_path}")

    def test_exact_current_skill_set_exists(self) -> None:
        observed = sorted(
            path.name
            for path in (PLUGIN_ROOT / "skills").iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        self.assertEqual(observed, sorted(IMPLEMENTED_SKILLS))

    def test_shared_resources_use_plugin_ignored_directory(self) -> None:
        self.assertTrue((PLUGIN_ROOT / "skills" / ".shared").is_dir())
        self.assertFalse((PLUGIN_ROOT / "skills" / "_shared").exists())

    def test_all_skill_markdown_is_reachable_and_links_resolve(self) -> None:
        production = set((PLUGIN_ROOT / "skills").rglob("*.md"))
        reachable: set[Path] = set()
        queue: list[Path] = []
        for name in IMPLEMENTED_SKILLS:
            skill_dir = PLUGIN_ROOT / "skills" / name
            queue.append(skill_dir / "SKILL.md")
            manifest = json.loads((skill_dir / "manifest.yaml").read_text(encoding="utf-8"))
            queue.extend((skill_dir / raw).resolve() for raw in referenced_paths(manifest))

        link_pattern = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)(?:#[^)]+)?\)")
        while queue:
            path = queue.pop().resolve()
            if path in reachable:
                continue
            self.assertTrue(path.is_file(), path)
            reachable.add(path)
            for raw in link_pattern.findall(path.read_text(encoding="utf-8")):
                linked = (path.parent / raw).resolve()
                self.assertTrue(linked.is_file(), f"{path}: {raw}")
                queue.append(linked)

        self.assertEqual(production - reachable, set())

    def test_stage_1a_documentation_and_license_exist(self) -> None:
        self.assertTrue((PLUGIN_ROOT / "README.md").is_file())
        self.assertTrue((PLUGIN_ROOT / "LICENSE").is_file())

    def test_generated_python_cache_is_ignored(self) -> None:
        patterns = (PLUGIN_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("__pycache__/", patterns)
        self.assertIn("*.py[cod]", patterns)

    def test_readme_uses_real_project_tool_arguments(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("init_project.py --project-root", readme)
        self.assertIn("--manuscript", readme)
        self.assertIn("validate_project.py --project-root", readme)
        self.assertNotIn("init_project.py --root", readme)
        self.assertNotIn("validate_project.py --root", readme)

    def test_readme_exposes_stage_2_analysis_without_claiming_manuscript_writes(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("analysis-adapter", readme)
        self.assertIn("analysis_preflight.py", readme)
        self.assertIn("analysis_registry.py", readme)
        self.assertIn("does not modify source data or manuscript files", readme)
        self.assertNotIn("It does not write into a manuscript, recalculate data", readme)

    def test_publishable_docs_do_not_expose_a_local_windows_profile(self) -> None:
        local_profile_prefix = "C:" + "\\Users"
        for path in [PLUGIN_ROOT / "README.md", PLAN]:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(local_profile_prefix, text, path)

    def test_public_repository_metadata_is_consistent(self) -> None:
        repository_url = "https://github.com/hmy77100-max/psychology-paper"
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(manifest.get("repository"), repository_url)
        self.assertIn(f"git clone {repository_url}.git", readme)

    def test_readme_documents_only_the_approved_distribution_modes(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("private GitHub repository", readme)
        self.assertIn("public GitHub repository", readme)
        self.assertIn("another computer with Codex", readme)
        self.assertIn("codex plugin marketplace add", readme)
        self.assertIn("codex plugin add psychology-paper@", readme)
        self.assertNotIn("standalone application", readme)
        self.assertNotIn("hosted web service", readme)

    def test_windows_official_validation_commands_force_utf8(self) -> None:
        lines = PLAN.read_text(encoding="utf-8").splitlines()
        commands = [
            line.strip()
            for line in lines
            if line.strip().startswith("python ")
            and ("quick_validate.py" in line or "validate_plugin.py" in line)
        ]
        self.assertGreaterEqual(len(commands), 5)
        for command in commands:
            self.assertTrue(command.startswith("python -X utf8 "), command)

    def test_plan_validates_standalone_plugin_from_repository_root(self) -> None:
        commands = [
            line.strip()
            for line in PLAN.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("python ") and "validate_plugin.py" in line
        ]
        self.assertGreaterEqual(len(commands), 2)
        for command in commands:
            self.assertTrue(command.endswith('"."'), command)

    def test_plan_hygiene_scan_starts_at_repository_root(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("Path('.').rglob('*')", plan)
        self.assertNotIn("Path('psychology-paper').rglob('*')", plan)

    def test_plan_keeps_skill_and_test_paths_intact(self) -> None:
        plan = PLAN.read_text(encoding="utf-8")
        self.assertIn("./skills/psychology-paper/", plan)
        self.assertIn("test_shared_contracts.py", plan)
        self.assertNotIn("skills/./", plan)
        self.assertNotIn("test.shared_contracts.py", plan)


if __name__ == "__main__":
    unittest.main()
