import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
AGENT_POLICY = PLUGIN_ROOT / "AGENTS.md"


class RepositoryPolicyTests(unittest.TestCase):
    def test_skill_resources_are_resolved_from_one_authoritative_mapping(self) -> None:
        self.assertTrue(AGENT_POLICY.is_file())
        text = AGENT_POLICY.read_text(encoding="utf-8")
        self.assertIn("skills/<skill-name>/manifest.yaml", text)
        self.assertIn("scripts/load_skill_resources.py", text)
        self.assertIn("Do not guess alternate manifest names", text)
        self.assertIn("Do not enumerate directories", text)


if __name__ == "__main__":
    unittest.main()
