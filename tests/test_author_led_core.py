"""Author-control and loading contracts; not claims about model writing quality."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import load_skill_resources as loader


class AuthorLedCoreTests(unittest.TestCase):
    def test_method_families_are_conditional_bounded_and_deduplicated(self):
        default = loader.load_skill_resources(skill="analysis-adapter", selectors=[])
        self.assertLessEqual(default.total_chars, 2498)
        self.assertEqual(len(default.resources), 1)
        families = {
            "anova": ("factorial_anova", "repeated_anova", "mixed_anova"),
            "regression": ("linear_regression", "binomial_regression", "poisson_regression"),
            "mixed": ("linear_mixed", "binomial_mixed", "poisson_mixed"),
            "mediation_moderation": ("mediation", "moderation"),
            "sem": ("cfa", "sem"),
        }
        for family, names in families.items():
            with self.subTest(family=family):
                selector = "conditional_loads.method_" + family
                loaded = loader.load_skill_resources(skill="analysis-adapter", selectors=[selector, selector])
                self.assertEqual(len(loaded.resources), 2)
                resource = loaded.resources[-1]
                self.assertLessEqual(len(resource.content), 3000)
                for name in names:
                    self.assertIn("`" + name + "`", resource.content)

    def test_analysis_context_preserves_timing_and_search_history(self):
        loaded = loader.load_skill_resources(skill="analysis-adapter", selectors=["conditional_loads.registry"])
        text = "\n".join(r.content for r in loaded.resources)
        for field in ("inferential_status", "analysis_role", "basis_ref", "search_set_id", "parent_analysis_id"):
            self.assertIn(field, text)
        for status in ("EXPLORATORY", "UNDETERMINED", "attempted", "completed", "failed", "adopted"):
            self.assertIn(status, text)

    def test_analysis_learning_is_optional_once_and_within_existing_load_budget(self):
        # Resource integration/cost only; scientific usefulness is judged by the author.
        default = loader.load_skill_resources(skill="analysis-adapter", selectors=[])
        selector = "conditional_loads.method_learning"
        selected = loader.load_skill_resources(skill="analysis-adapter", selectors=[selector])
        repeated = loader.load_skill_resources(skill="analysis-adapter", selectors=[selector, selector])
        self.assertEqual(len(default.resources), 1)
        self.assertEqual(len(selected.resources), len(default.resources) + 1)
        self.assertEqual(selected.resources, repeated.resources)
        self.assertEqual(selected.total_chars, repeated.total_chars)
        self.assertLessEqual(default.total_chars, 2300,
                             "merge existing core wording to make room for the discovery cue")
        self.assertLessEqual(selected.total_chars, 6400,
                             "keep method details conditional without a new loading layer")

    def test_conditional_resources_do_not_restore_formal_only_gate(self):
        routing=(ROOT/'skills/psychology-paper/references/task-routing.md').read_text(encoding='utf-8')
        methods=(ROOT/'skills/evidence-audit/references/methods-review.md').read_text(encoding='utf-8')
        compare=(ROOT/'skills/analysis-adapter/references/source-comparison.md').read_text(encoding='utf-8')
        self.assertNotIn('lock one formal source, then produce',routing)
        self.assertNotIn('without a separate request',methods)
        self.assertNotIn('estimator, software, settings, seed, and output location',compare)

    def test_writing_and_review_do_not_block_read_only_method_support(self):
        writing = (ROOT/'skills/manuscript-writing/SKILL.md').read_text(encoding='utf-8')
        review = (ROOT/'skills/evidence-audit/SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('Suggest a method or candidate analysis only in response to the author request.', writing)
        self.assertNotIn('no automatic editing or analysis handoff', review)

    def test_analysis_entry_does_not_duplicate_loaded_intent_definitions(self):
        text=(ROOT/'skills/analysis-adapter/SKILL.md').read_text(encoding='utf-8')
        self.assertNotIn('`METHOD_REVIEW`: discuss and learn methods',text)

    def test_router_writing_and_audit_share_one_bounded_library_reminder(self):
        expected = (ROOT / "skills/.shared/core/author-led-writing.md").resolve()
        for skill in ("psychology-paper", "manuscript-writing", "evidence-audit"):
            with self.subTest(skill=skill):
                loaded = loader.load_skill_resources(skill=skill, selectors=[])
                matches = [r for r in loaded.resources
                           if (ROOT / "skills" / skill / r.relative_path).resolve() == expected]
                self.assertEqual(len(matches), 1, "direct and routed entry must include the shared author core once")
                self.assertLessEqual(len(matches[0].content), 350)
                self.assertRegex(matches[0].content, r"同一篇[^。\n]*主动问[^。\n]*个人文献库")
                self.assertRegex(matches[0].content, r"(?:同意|确认|授权)后才保存")

    def test_default_core_cost_does_not_grow_by_stacking(self):
        for skill, baseline in (("psychology-paper", 1709), ("manuscript-writing", 4856)):
            with self.subTest(skill=skill):
                self.assertLess(loader.load_skill_resources(skill=skill, selectors=[]).total_chars,
                                baseline, "consolidate old rules rather than append another layer")

    def test_discussion_does_not_force_evidence_first_or_a_four_step_paragraph(self):
        loaded = loader.load_skill_resources(skill="manuscript-writing", selectors=["axes.section.discussion"])
        text = "\n".join(r.content for r in loaded.resources)
        self.assertNotIn("Lead with evidence before interpretation", text)
        self.assertNotIn("For each issue:", text)

    def test_caveats_have_no_global_one_location_quota(self):
        loaded = loader.load_skill_resources(skill="manuscript-writing", selectors=[])
        self.assertNotIn("one manuscript home", "\n".join(r.content for r in loaded.resources))

    def test_authorized_scientific_wording_is_not_an_automatic_audit_handoff(self):
        text = (ROOT / "skills/manuscript-writing/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("if so, stop and request an evidence audit", text)


if __name__ == "__main__":
    unittest.main()
