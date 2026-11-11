"""Author-control and loading contracts; not claims about model writing quality."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import load_skill_resources as loader


class AuthorLedCoreTests(unittest.TestCase):
    def test_direct_and_routed_writing_share_one_bounded_core(self):
        expected = (ROOT / "skills/.shared/core/author-led-writing.md").resolve()
        for skill in ("psychology-paper", "manuscript-writing"):
            with self.subTest(skill=skill):
                loaded = loader.load_skill_resources(skill=skill, selectors=[])
                matches = [r for r in loaded.resources
                           if (ROOT / "skills" / skill / r.relative_path).resolve() == expected]
                self.assertEqual(len(matches), 1, "direct and routed entry must include the shared author core once")
                self.assertLessEqual(len(matches[0].content), 350)

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
