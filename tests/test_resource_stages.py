import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import load_skill_resources as loader

SUPPLEMENTS = ["conditional_loads.bilingual_sync", "conditional_loads.revision_checks", "conditional_loads.literature_support"]


class ResourceStageTests(unittest.TestCase):
    def api(self):
        self.assertTrue((ROOT / "scripts/resource_stages.py").is_file(), "missing deterministic stage planner")
        return importlib.import_module("resource_stages")

    def args(self, **extra):
        return dict(skill="manuscript-writing", selectors=SUPPLEMENTS, context_id="test-context-1", **extra)

    def acknowledge(self, delivery):
        receipt = copy.deepcopy(delivery["receipt_template"])
        self.assertIs(receipt["read_complete"], False)
        receipt.update(read_complete=True, output_ref="test-output-" + str(delivery["stage_id"]))
        return receipt

    def test_historical_exact_size_failure_and_staged_complete_union(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skills/manuscript-writing"
            skill.mkdir(parents=True)
            sizes = [742, 1760, 515, 531, 942, 1648, 5450, 2905]
            for i, size in enumerate(sizes):
                (skill / f"r{i}.md").write_text("x" * size, encoding="utf-8")
            manifest = {"skill": "manuscript-writing", "always_load": [f"./r{i}.md" for i in range(5)], "conditional_loads": {name.split('.')[1]: [f"./r{i+5}.md"] for i, name in enumerate(SUPPLEMENTS)}}
            (skill / "manifest.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(loader.ResourceBudgetError, "14493.*12000"):
                loader.load_skill_resources(skill="manuscript-writing", selectors=SUPPLEMENTS, plugin_root=root)
            args = self.args(plugin_root=root)
            plan = api.build_plan(**args)
            self.assertEqual(plan["total_unique_chars"], 14493)
            self.assertEqual([s["chars"] for s in plan["stages"]], [4490, 1648, 5450, 2905])
            receipts = []
            for stage in plan["stages"]:
                output = api.load_stage(**args, stage_id=stage["id"], receipts=receipts)
                self.assertEqual(output["status"], "DELIVERED_NOT_ACKNOWLEDGED")
                receipts.append(self.acknowledge(output))
            self.assertEqual(api.check_coverage(**args, receipts=receipts)["status"], "ACKNOWLEDGED")

    def test_current_failure_is_not_hidden_by_default_load(self):
        api = self.api()
        with self.assertRaises(loader.ResourceBudgetError):
            loader.load_skill_resources(skill="manuscript-writing", selectors=SUPPLEMENTS)
        plan = api.build_plan(**self.args())
        self.assertGreater(plan["total_unique_chars"], 12000)
        self.assertTrue(all(s["chars"] <= 12000 for s in plan["stages"]))
        ids = [r["path"] for s in plan["stages"] for r in s["resources"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_plan_and_delivery_are_not_read_coverage(self):
        api = self.api()
        api.build_plan(**self.args())
        self.assertEqual(api.check_coverage(**self.args(), receipts=[])["status"], "INCOMPLETE")
        first = api.load_stage(**self.args(), stage_id=0, receipts=[])
        self.assertEqual(api.check_coverage(**self.args(), receipts=[first["receipt_template"]])["status"], "INCOMPLETE")
        with self.assertRaisesRegex(api.ReceiptError, "predecessor"):
            api.load_stage(**self.args(), stage_id=1, receipts=[first["receipt_template"]])

    def test_context_root_and_resource_changes_invalidate_receipts(self):
        api = self.api()
        first = api.load_stage(**self.args(), stage_id=0, receipts=[])
        receipt = self.acknowledge(first)
        args = self.args()
        args["context_id"] = "new-context"
        with self.assertRaises(api.ReceiptError):
            api.check_coverage(**args, receipts=[receipt])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skills/manuscript-writing"
            skill.mkdir(parents=True)
            (skill / "core.md").write_text("original", encoding="utf-8")
            manifest = {"skill": "manuscript-writing", "always_load": ["core.md"]}
            (skill / "manifest.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            args = dict(skill="manuscript-writing", selectors=[], context_id="same", plugin_root=root)
            receipt = self.acknowledge(api.load_stage(**args, stage_id=0, receipts=[]))
            (skill / "core.md").write_text("changed", encoding="utf-8")
            with self.assertRaises(api.ReceiptError):
                api.check_coverage(**args, receipts=[receipt])
            (skill / "core.md").write_text("original", encoding="utf-8")
            manifest["version"] = 2
            (skill / "manifest.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(api.ReceiptError):
                api.check_coverage(**args, receipts=[receipt])

    def test_malformed_unknown_duplicate_and_unreferenced_receipts_fail_closed(self):
        api = self.api()
        receipt = self.acknowledge(api.load_stage(**self.args(), stage_id=0, receipts=[]))
        bad_cases = [None, {}, [None], [receipt, receipt]]
        for field, value in [("stage_id", 999), ("resources", []), ("output_ref", ""), ("read_complete", "true"), ("plan_id", "stale")]:
            changed = copy.deepcopy(receipt)
            changed[field] = value
            bad_cases.append([changed])
        for bad in bad_cases:
            with self.subTest(bad=bad):
                with self.assertRaises(api.ReceiptError):
                    api.check_coverage(**self.args(), receipts=bad)

    def test_oversize_indivisible_group_is_not_sliced(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skills/example"
            skill.mkdir(parents=True)
            (skill / "large.md").write_text("x" * 12001, encoding="utf-8")
            (skill / "manifest.yaml").write_text(json.dumps({"skill": "example", "always_load": ["large.md"]}), encoding="utf-8")
            with self.assertRaises(loader.ResourceBudgetError):
                api.build_plan(skill="example", selectors=[], context_id="x", plugin_root=root)

    def test_actual_full_intro_and_collaboration_state_paths_have_coverage(self):
        api = self.api()
        cases = [
            ("manuscript-writing", ["axes.task.full-manuscript", "axes.language.chinese", "axes.section.introduction", "shared_loads.candidate_format", "conditional_loads.literature_support", "conditional_loads.revision_checks"]),
            ("psychology-paper", ["conditional_loads.collaboration", "shared_loads.authorization", "shared_loads.state_rules"]),
            ("evidence-audit", ["axes.paper_type.empirical", "axes.design_tags.survey", "axes.scope.full", "axes.risk_threshold.all", "conditional_loads.methods_review", "conditional_loads.quality_review", "conditional_loads.external_evidence"]),
        ]
        for skill, selectors in cases:
            args = dict(skill=skill, selectors=selectors, context_id="integration")
            plan = api.build_plan(**args)
            original = loader.describe_resources(skill=skill, selectors=selectors)
            self.assertEqual(plan["total_unique_chars"], original["total_chars"])
            receipts = []
            for stage in plan["stages"]:
                delivery = api.load_stage(**args, stage_id=stage["id"], receipts=receipts)
                receipts.append(self.acknowledge(delivery))
            self.assertEqual(api.check_coverage(**args, receipts=receipts)["pending_stages"], [])

    def test_cli_plan_does_not_emit_bodies_and_typo_is_classified(self):
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/load_skill_resources.py"), "--skill", "manuscript-writing"]
        result = subprocess.run(command + ["--plan", "--context-id", "cli-test", "--select", SUPPLEMENTS[0]], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan_id", json.loads(result.stdout))
        self.assertNotIn("# Writing stance", result.stdout)
        bad = subprocess.run(command + ["--selectors", SUPPLEMENTS[0]], capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("ARGUMENT_ERROR", bad.stderr)

    def test_cli_resolution_receipt_and_budget_errors_have_no_traceback_or_bodies(self):
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/load_skill_resources.py"), "--skill", "manuscript-writing"]
        cases = [
            (["--plan", "--context-id", "x", "--select", "conditional_loads.unknown"], "RESOLUTION_ERROR"),
            (["--stage", "1", "--context-id", "x", "--select", SUPPLEMENTS[0]], "READ_RECEIPT_INVALID"),
            (["--select", SUPPLEMENTS[0], "--select", SUPPLEMENTS[1], "--select", SUPPLEMENTS[2]], "BUDGET_EXCEEDED"),
        ]
        for args, code in cases:
            with self.subTest(code=code):
                result = subprocess.run(command + args, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 2)
                self.assertIn(code, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_full_cli_journey_attestations_and_no_plugin_writes(self):
        self.api()
        before = {p: p.read_bytes() for p in [ROOT / "skills/manuscript-writing/manifest.yaml", ROOT / "scripts/load_skill_resources.py"]}
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/load_skill_resources.py"), "--skill", "manuscript-writing", "--context-id", "cli-journey"]
        for selector in SUPPLEMENTS:
            command.extend(["--select", selector])
        with tempfile.TemporaryDirectory(prefix="阶段回执-") as raw:
            receipt_path = Path(raw) / "reads.json"
            plan_result = subprocess.run(command + ["--plan"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(plan_result.returncode, 0, plan_result.stderr)
            plan = json.loads(plan_result.stdout)
            receipts = []
            for stage in plan["stages"]:
                receipt_path.write_text(json.dumps(receipts), encoding="utf-8")
                output = subprocess.run(command + ["--stage", str(stage["id"]), "--receipts", str(receipt_path)], capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(output.returncode, 0, output.stderr)
                delivery = json.loads(output.stdout)
                self.assertIn("--- resource:", delivery["content"])
                receipts.append(self.acknowledge(delivery))
            receipt_path.write_text(json.dumps(receipts), encoding="utf-8")
            covered = subprocess.run(command + ["--check-coverage", "--receipts", str(receipt_path)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(covered.returncode, 0, covered.stderr)
            self.assertEqual(json.loads(covered.stdout)["status"], "ACKNOWLEDGED")
            receipts.pop()
            receipt_path.write_text(json.dumps(receipts), encoding="utf-8")
            pending = subprocess.run(command + ["--check-coverage", "--receipts", str(receipt_path)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(pending.returncode, 1)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    def test_duplicate_selector_dedup_and_cross_root_invalidation(self):
        api = self.api()
        base = api.build_plan(**self.args())
        args = self.args()
        args["selectors"] = SUPPLEMENTS + [SUPPLEMENTS[0], "always_load"]
        duplicate = api.build_plan(**args)
        self.assertEqual(base["total_unique_chars"], duplicate["total_unique_chars"])
        self.assertEqual(len(base["stages"]), len(duplicate["stages"]))
        with tempfile.TemporaryDirectory() as raw:
            roots = [Path(raw) / "first", Path(raw) / "second"]
            for root in roots:
                skill = root / "skills/example"
                skill.mkdir(parents=True)
                (skill / "core.md").write_text("same", encoding="utf-8")
                (skill / "manifest.yaml").write_text(json.dumps({"skill": "example", "always_load": ["core.md"]}), encoding="utf-8")
            args = dict(skill="example", selectors=[], context_id="same", plugin_root=roots[0])
            receipt = self.acknowledge(api.load_stage(**args, stage_id=0, receipts=[]))
            args["plugin_root"] = roots[1]
            with self.assertRaises(api.ReceiptError):
                api.check_coverage(**args, receipts=[receipt])

    def test_stage_bodies_match_hashes_and_changed_selection_invalidates_receipts(self):
        api = self.api()
        receipts = []
        args = self.args()
        for stage in api.build_plan(**args)["stages"]:
            delivery = api.load_stage(**args, stage_id=stage["id"], receipts=receipts)
            expected = []
            for resource in stage["resources"]:
                body = (ROOT / resource["path"]).read_text(encoding="utf-8")
                self.assertEqual(len(body), resource["chars"])
                self.assertEqual(hashlib.sha256(body.encode("utf-8")).hexdigest(), resource["sha256"])
                expected.append(f"--- resource: {resource['path']} ---\n{body}")
            self.assertEqual(delivery["content"], "\n\n".join(expected))
            receipts.append(self.acknowledge(delivery))
        args["selectors"] = SUPPLEMENTS[:-1]
        with self.assertRaises(api.ReceiptError):
            api.check_coverage(**args, receipts=receipts)

    def test_cli_cannot_raise_stage_budget_or_mix_modes(self):
        command = [sys.executable, "-X", "utf8", str(ROOT / "scripts/load_skill_resources.py"), "--skill", "manuscript-writing"]
        for args in (["--plan"], ["--plan", "--context-id", "x", "--max-chars", "20000"],
                     ["--stage", "0", "--plan", "--context-id", "x"], ["--context-id", "x"],
                     ["--plan", "--context-id", "x", "--receipts", "unused.json"]):
            with self.subTest(args=args):
                result = subprocess.run(command + args, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 2)
                self.assertIn("ARGUMENT_ERROR", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_oversize_multifile_conditional_group_is_not_sliced(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill = root / "skills/example"
            skill.mkdir(parents=True)
            for name, size in [("core.md", 1), ("first.md", 6000), ("second.md", 6001)]:
                (skill / name).write_text("x" * size, encoding="utf-8")
            manifest = {"skill": "example", "always_load": ["core.md"],
                        "conditional_loads": {"large": ["first.md", "second.md"]}}
            (skill / "manifest.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(loader.ResourceBudgetError, "indivisible stage conditional_loads.large"):
                api.build_plan(skill="example", selectors=["conditional_loads.large"], context_id="x", plugin_root=root)


if __name__ == "__main__":
    unittest.main()
