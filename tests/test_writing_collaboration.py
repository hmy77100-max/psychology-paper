"""Instruction contracts and resource costs, not model-quality assertions."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import load_skill_resources as loader


class WritingCollaborationTests(unittest.TestCase):
    def selected(self, skill, selector):
        manifest = json.loads((ROOT / "skills" / skill / "manifest.yaml").read_text(encoding="utf-8"))
        self.assertIn(selector, manifest["conditional_loads"], "missing focused resource")
        result = loader.load_skill_resources(skill=skill, selectors=[f"conditional_loads.{selector}"])
        return "\n".join(r.content for r in result.resources)

    def test_diagnostics_repair_without_inventing_evidence(self):
        text = self.selected("manuscript-writing", "prose_diagnostics")
        for phrase in ("Observed phrase", "Repair", "evidence-tied uncertainty", "missing support", "contribution", "no citation quota", "statistical reporting"):
            self.assertIn(phrase, text)

    def test_diagnostics_observe_voice_without_unapproved_persistence(self):
        text = self.selected("manuscript-writing", "prose_diagnostics")
        for phrase in ("sentence rhythm", "hedge placement", "author sample", "STYLE_DELTA", "explicit approval", "latest author-edited"):
            self.assertIn(phrase, text)

    def test_role_activation_and_evidence_not_vote(self):
        text = self.selected("psychology-paper", "collaboration")
        for phrase in ("explicitly invokes", "configurable", "independent agents", "majority vote", "external feedback", "unrounded", "evidence-audit"):
            self.assertIn(phrase, text)

    def test_decisions_reuse_state_without_generic_blanket_acceptance(self):
        text = self.selected("psychology-paper", "collaboration")
        for phrase in ("approved_decisions", "unresolved_issues", "supersedes", "read back", "item", "not an intentional hold", "no parallel approval log"):
            self.assertIn(phrase, text)

    def test_verification_checks_deliverables_not_discussion(self):
        text = self.selected("psychology-paper", "collaboration")
        for phrase in ("requirement", "source version", "candidate location", "verification result", "Chinese", "English", "pending", "not evidence of completion"):
            self.assertIn(phrase, text)

    def test_shared_state_records_partial_direction_without_approving_candidate(self):
        text = (ROOT / "skills/.shared/core/authorization-and-state.md").read_text(encoding="utf-8")
        for phrase in ("item-level", "supersedes", "pending candidate", "read back"):
            self.assertIn(phrase, text)

    def test_entrypoints_route_only_when_needed(self):
        for skill, selector in (("manuscript-writing", "prose_diagnostics"), ("psychology-paper", "collaboration")):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"conditional_loads.{selector}", text)
            default = loader.load_skill_resources(skill=skill, selectors=[])
            self.assertFalse(any(selector.replace("_", "-") in r.relative_path for r in default.resources))

    def test_all_diagnostic_writing_routes_fit_default_budget(self):
        manifest = json.loads((ROOT / "skills/manuscript-writing/manifest.yaml").read_text(encoding="utf-8"))
        self.assertIn("prose_diagnostics", manifest["conditional_loads"])
        for task in manifest["axes"]["task"]:
            for language in manifest["axes"]["language"]:
                for section in manifest["axes"]["section"]:
                    selectors = [f"axes.task.{task}", f"axes.language.{language}", f"axes.section.{section}", "shared_loads.candidate_format", "conditional_loads.prose_diagnostics"]
                    with self.subTest(selectors=selectors):
                        self.assertLessEqual(loader.load_skill_resources(skill="manuscript-writing", selectors=selectors).total_chars, 12000)

    def test_collaboration_and_authorization_fit_together(self):
        self.selected("psychology-paper", "collaboration")
        result = loader.load_skill_resources(skill="psychology-paper", selectors=["conditional_loads.collaboration", "shared_loads.authorization"])
        self.assertLessEqual(result.total_chars, 12000)

    def test_third_party_notice_retains_license(self):
        path = ROOT / "THIRD_PARTY_NOTICES.md"
        self.assertTrue(path.is_file(), "adaptation requires notice")
        text = path.read_text(encoding="utf-8")
        for phrase in ("AIScientists-Dev", "MIT License", "Permission is hereby granted", "AS IS"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
