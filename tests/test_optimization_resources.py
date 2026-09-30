import json
from pathlib import Path
import sys
import unittest
import tempfile
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import load_skill_resources as loader


class OptimizationResourceTests(unittest.TestCase):
    def test_keywords_and_focused_workflow_resources_exist_and_fit(self):
        cases = [
            ("manuscript-writing", ["axes.task.full-manuscript", "axes.language.chinese", "axes.section.keywords", "shared_loads.candidate_format"]),
            ("manuscript-writing", ["axes.task.section-rewrite", "axes.language.english", "axes.section.introduction", "conditional_loads.literature_support"]),
            ("manuscript-writing", ["axes.task.section-rewrite", "axes.language.chinese-to-english", "axes.section.discussion", "conditional_loads.bilingual_sync"]),
            ("journal-fit-style", ["axes.journal_status.confirmed", "axes.depth.deep", "conditional_loads.contribution_planning"]),
        ]
        for skill, selectors in cases:
            with self.subTest(skill=skill, selectors=selectors):
                result = loader.load_skill_resources(skill=skill, selectors=selectors)
                self.assertLessEqual(result.total_chars, 12000)

    def test_describe_reports_full_total_first_overflow_and_hashes(self):
        plan = loader.describe_resources(skill="evidence-audit", selectors=[
            "axes.paper_type.empirical", "axes.design_tags.survey", "axes.scope.change-impact", "axes.scope.local",
            "axes.risk_threshold.all", "conditional_loads.external_evidence", "conditional_loads.revision_options",
            "conditional_loads.quality_review"])
        self.assertGreater(plan["total_chars"], 12000)
        self.assertTrue(plan["first_overflow"])
        self.assertEqual(len(plan["manifest_sha256"]), 64)
        self.assertEqual(plan["total_chars"], sum(x["chars"] for x in plan["resources"]))

    def test_selector_error_lists_exact_values_without_automatic_retry(self):
        with self.assertRaises(loader.ResourceResolutionError) as caught:
            loader.load_skill_resources(skill="manuscript-writing", selectors=["axes.task.full_manuscript"])
        self.assertIn("axes.task.full-manuscript", str(caught.exception))

    def test_literature_and_framing_deliverables_have_required_behavior(self):
        writing = loader.load_skill_resources(skill="manuscript-writing", selectors=["conditional_loads.literature_support"])
        text = "\n".join(x.content for x in writing.resources)
        for phrase in ("supporting evidence", "research question", "hypotheses", "existing search authorization", "incremental value"):
            self.assertIn(phrase, text)

    def test_all_focused_writing_routes_fit_without_optional_resource_stacking(self):
        manifest = json.loads((ROOT / "skills/manuscript-writing/manifest.yaml").read_text(encoding="utf-8"))
        for task in manifest["axes"]["task"]:
            for language in manifest["axes"]["language"]:
                for section in manifest["axes"]["section"]:
                    selectors = [f"axes.task.{task}", f"axes.language.{language}", f"axes.section.{section}", "shared_loads.candidate_format"]
                    with self.subTest(selectors=selectors):
                        self.assertLessEqual(loader.load_skill_resources(skill="manuscript-writing", selectors=selectors).total_chars, 12000)
        self.assertLessEqual(loader.load_skill_resources(skill="manuscript-writing", selectors=["conditional_loads.revision_checks"]).total_chars, 12000)

    def test_describe_cli_does_not_print_instruction_bodies(self):
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/load_skill_resources.py"),
            "--skill", "manuscript-writing", "--select", "conditional_loads.revision_checks", "--describe"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("manifest_sha256", json.loads(result.stdout))
        self.assertNotIn("# Revision checks and records", result.stdout)

    def test_duplicate_paths_are_canonicalized_and_error_reports_full_cost(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skills" / "synthetic"
            skill.mkdir(parents=True)
            for name in ("a.md", "b.md", "c.md"):
                (skill / name).write_text("x" * 60, encoding="utf-8")
            (skill / "manifest.yaml").write_text(json.dumps({"skill": "synthetic", "always_load": ["./a.md", "a.md", "./b.md", "./c.md"]}), encoding="utf-8")
            plan = loader.describe_resources(skill="synthetic", selectors=[], plugin_root=root, max_chars=100)
            self.assertEqual(plan["total_chars"], 180)
            self.assertEqual(plan["first_overflow"], "b.md")
            with self.assertRaisesRegex(loader.ResourceBudgetError, "180.*100"):
                loader.load_skill_resources(skill="synthetic", selectors=[], plugin_root=root, max_chars=100)
        fit = loader.load_skill_resources(skill="journal-fit-style", selectors=["conditional_loads.contribution_planning"])
        text = "\n".join(x.content for x in fit.resources)
        for phrase in ("author's own view", "direct predecessors", "original argument", "outline"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
