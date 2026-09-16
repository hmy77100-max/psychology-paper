import re
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SHARED = PLUGIN_ROOT / "skills" / ".shared"


class SharedContractTests(unittest.TestCase):
    def test_required_shared_files_exist(self) -> None:
        required = [
            "core/authorization-and-state.md",
            "core/source-authority.md",
            "core/evidence-boundaries.md",
            "core/research-design-taxonomy.md",
            "core/terminology-ledger.md",
            "core/state-consistency.md",
            "core/change-propagation.md",
            "output/candidate-format.md",
            "output/risk-reporting.md",
            "schemas/minimal-handoff.md",
        ]
        missing = [item for item in required if not (SHARED / item).is_file()]
        self.assertEqual(missing, [])
        self.assertFalse((SHARED / "SKILL.md").exists())

    def test_patch_invariants_have_one_canonical_home(self) -> None:
        invariants = [
            "PATCH_FIRST = true",
            "FULL_REBUILD_ON_LOCAL_EDIT = false",
            "AUTO_VERSIONED_COPY = false",
            "FULL_RENDER_ONLY_AT_MILESTONE = true",
        ]
        files = list(SHARED.rglob("*.md"))
        for invariant in invariants:
            hits = [path for path in files if invariant in path.read_text(encoding="utf-8")]
            self.assertEqual(
                hits,
                [SHARED / "core" / "authorization-and-state.md"],
                invariant,
            )

    def test_state_rule_definitions_are_not_duplicated(self) -> None:
        definition_pattern = re.compile(r'"id"\s*:\s*"SC-\d{3}"')
        defining_files = [
            path
            for path in SHARED.rglob("*.md")
            if definition_pattern.search(path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(defining_files, [SHARED / "core" / "state-consistency.md"])

    def test_candidate_output_orders_are_exact(self) -> None:
        text = (SHARED / "output" / "candidate-format.md").read_text(encoding="utf-8")
        expected = [
            "English edit: Original English → Revised English → Chinese Translation",
            "Chinese edit: Original Chinese → Revised Chinese → Necessary Notes",
            "Chinese-to-English: Chinese Source → Revised English → Chinese Back-translation",
        ]
        for item in expected:
            self.assertIn(item, text)

    def test_minimal_handoff_uses_exact_ordered_keys(self) -> None:
        text = (SHARED / "schemas" / "minimal-handoff.md").read_text(encoding="utf-8")
        match = re.search(r"```text\n(.*?)\n```", text, re.DOTALL)
        self.assertIsNotNone(match)
        keys = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        self.assertEqual(
            keys,
            [
                "task",
                "source_path",
                "location",
                "scope",
                "paper_and_design_tags",
                "authoritative_source",
                "approved_constraints",
                "evidence_ceiling",
                "required_output",
                "open_issue",
                "PRIMARY_MODULE",
                "SUPPORT_MODULES",
                "STOP_CONDITION",
            ],
        )

    def test_change_propagation_separates_read_and_write_scope(self) -> None:
        text = (SHARED / "core" / "change-propagation.md").read_text(encoding="utf-8")
        self.assertIn("change-impact audit", text)
        self.assertIn("read_scope", text)
        self.assertIn("write_scope", text)
        self.assertIn("Broader reading never authorizes broader writing", text)


if __name__ == "__main__":
    unittest.main()
