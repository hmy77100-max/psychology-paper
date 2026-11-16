import json
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_ROOT = PLUGIN_ROOT / "tests" / "scenarios"
REQUIRED_KEYS = {
    "id",
    "request",
    "project_state",
    "expected_primary_module",
    "expected_scope",
    "required_actions",
    "forbidden_actions",
    "expected_state_effect",
    "manual_rubric",
    "tags",
}
ALLOWED_EXTRA_KEYS = {"expected_output_sections"}
OUTPUT_ORDERS = {
    "english": ["Original English", "Revised English", "Chinese Translation"],
    "chinese": ["Original Chinese", "Revised Chinese", "Necessary Notes"],
    "chinese-to-english": [
        "Chinese Source",
        "Revised English",
        "Chinese Back-translation",
    ],
}


def load_scenarios() -> list[dict[str, object]]:
    scenarios: list[dict[str, object]] = []
    for path in sorted(SCENARIO_ROOT.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get('schema')=='psychology-paper-golden-24':
            # The rubric is richer than a routing scenario; do not weaken the
            # exact legacy contract for unrelated files.
            payload=[{k:v for k,v in case.items() if k in REQUIRED_KEYS | ALLOWED_EXTRA_KEYS}
                     for case in payload['cases']]
        if not isinstance(payload, list):
            raise AssertionError(f"Scenario file must contain a list: {path}")
        scenarios.extend(payload)
    return scenarios


class ScenarioContractTests(unittest.TestCase):
    def test_design_opportunity_cases_keep_naive_prompt_and_author_acceptance_record(self):
        # Checks the recorded author decision; never executes or grades a business case.
        scenarios = {s['id']: s for s in load_scenarios()}
        for case_id in ('ROUTE-014', 'ROUTE-015'):
            with self.subTest(case_id=case_id):
                self.assertTrue(case_id in scenarios, 'missing proposed case: ' + case_id)
                case = scenarios[case_id]
                self.assertEqual(case['request'], '帮我改这篇论文')
                self.assertEqual(case['project_state']['simulation_status'], 'AUTHOR_ACCEPTED')
                self.assertEqual(case['project_state']['business_judge'], 'AUTHOR')
                self.assertEqual(case['project_state']['initial_inputs'], ['synthetic_manuscript'])

    def test_fixed_golden_quota_and_input_separation(self):
        payload=json.loads((SCENARIO_ROOT/'golden-24.json').read_text(encoding='utf-8'))
        cases=payload['cases']
        self.assertEqual([c['id'] for c in cases],[f'G{i:02d}' for i in range(1,25)])
        for group in payload['metadata']['groups'].values(): self.assertEqual(len(group),4)
        for case in cases:
            self.assertTrue(case['source_basis'])
            self.assertTrue(case['failure_criteria'])
            for name in case['inputs']:
                self.assertTrue((PLUGIN_ROOT/name).is_file(), name)
    def test_routing_scenarios_exist_and_have_required_fields(self) -> None:
        self.assertTrue((SCENARIO_ROOT / "routing.json").is_file())
        scenarios = load_scenarios()
        self.assertGreaterEqual(len(scenarios), 10)
        for scenario in scenarios:
            self.assertTrue(REQUIRED_KEYS.issubset(scenario), scenario.get("id"))
            self.assertEqual(set(scenario) - REQUIRED_KEYS, ALLOWED_EXTRA_KEYS & set(scenario))
            self.assertIsInstance(scenario["required_actions"], list)
            self.assertIsInstance(scenario["forbidden_actions"], list)
            self.assertTrue(scenario["manual_rubric"])

    def test_scenario_ids_are_unique(self) -> None:
        ids = [scenario["id"] for scenario in load_scenarios()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_routing_guards_cover_both_error_directions(self) -> None:
        tags = {tag for scenario in load_scenarios() for tag in scenario["tags"]}
        self.assertIn("under_escalation_guard", tags)
        self.assertIn("over_escalation_guard", tags)

    def test_failure_report_regressions_have_behavioral_scenarios(self) -> None:
        tags = {tag for scenario in load_scenarios() for tag in scenario["tags"]}
        required = {
            "approval_and_advance",
            "full_manuscript_project_gate",
            "journal_body_budget",
            "author_chosen_sequence",
            "literature_decision_gate",
            "unique_candidate_id",
            "natural_language_output",
            "bounded_next_step_preview",
            "deduplicated_evidence_boundary",
            "analysis_adapter_route",
        }
        self.assertTrue(required.issubset(tags), required - tags)

    def test_writing_scenarios_lock_all_output_orders(self) -> None:
        path = SCENARIO_ROOT / "manuscript-writing.json"
        self.assertTrue(path.is_file())
        scenarios = json.loads(path.read_text(encoding="utf-8"))
        observed = {
            scenario["project_state"].get("language_mode"): scenario.get(
                "expected_output_sections"
            )
            for scenario in scenarios
            if scenario["project_state"].get("language_mode") in OUTPUT_ORDERS
        }
        self.assertEqual(observed, OUTPUT_ORDERS)
        full = [scenario for scenario in scenarios if "full_manuscript" in scenario["tags"]]
        self.assertGreaterEqual(len(full), 1)
        self.assertTrue(
            any("chunk by logical unit" in scenario["required_actions"] for scenario in full)
        )
        self.assertTrue(
            any(
                "generate the full three-part manuscript at once"
                in scenario["forbidden_actions"]
                for scenario in full
            )
        )
        self.assertTrue(any("author_chosen_sequence" in scenario["tags"] for scenario in full))


if __name__ == "__main__":
    unittest.main()
