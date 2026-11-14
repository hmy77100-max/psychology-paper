"""Synthetic, read-only fixtures for reuse of explicitly read resource bodies."""

import copy
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
stages = importlib.import_module("resource_stages")
loader = importlib.import_module("load_skill_resources")


class ResourceReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shared = self.root / "skills" / ".shared"
        shared.mkdir(parents=True)
        (shared / "voice.md").write_text("shared author guidance", encoding="utf-8")
        for name in ("route", "writing"):
            folder = self.root / "skills" / name
            folder.mkdir()
            (folder / "core.md").write_text(name + " core", encoding="utf-8")
            (folder / "extra.md").write_text(name + " new evidence", encoding="utf-8")
            (folder / "manifest.yaml").write_text(json.dumps({
                "skill": name,
                "always_load": ["../.shared/voice.md", "./core.md"],
                "conditional_loads": {"extra": ["./extra.md"]},
            }), encoding="utf-8")

    def args(self, skill="route", selectors=None, **changes):
        result = dict(skill=skill, selectors=selectors or [],
                      context_id="synthetic-read-context", plugin_root=self.root)
        result.update(changes)
        return result

    def ack(self, delivery):
        receipt = copy.deepcopy(delivery["receipt_template"])
        self.assertIs(receipt["read_complete"], False)
        receipt.update(read_complete=True, output_ref="synthetic-explicit-read")
        return receipt

    def read(self, args=None, receipts=None, stage_id=0):
        return stages.load_stage(**(args or self.args()), stage_id=stage_id,
                                 receipts=receipts or [])

    def test_cross_module_outputs_only_unread_complete_resources(self):
        first = self.ack(self.read())
        target = self.args("writing")
        output = self.read(target, [first])
        self.assertEqual(output["receipt_template"]["schema"], "resource-read-receipt-v2")
        self.assertEqual(first["source"]["skill"], "route")
        self.assertNotIn("shared author guidance", output["content"])
        self.assertIn("writing core", output["content"])
        self.assertEqual(output["chars"], len("writing core"))
        self.assertEqual(output["reused_chars"], len("shared author guidance"))
        self.assertEqual([r["path"] for r in output["receipt_template"]["resources"]],
                         ["skills/writing/core.md"])
        self.assertEqual(stages.check_coverage(**target, receipts=[first])["status"], "INCOMPLETE")
        second = self.ack(output)
        self.assertEqual(stages.check_coverage(**target, receipts=[first, second])["status"],
                         "ACKNOWLEDGED")

    def test_same_plan_repeated_read_outputs_no_body_or_new_receipt(self):
        receipt = self.ack(self.read())
        output = self.read(receipts=[receipt])
        self.assertEqual(output["status"], "ALREADY_ACKNOWLEDGED")
        self.assertEqual(output["content"], "")
        self.assertEqual(output["chars"], 0)
        self.assertIsNone(output["receipt_template"])

    def test_expanding_selectors_reuses_core_and_reads_new_resource(self):
        receipt = self.ack(self.read())
        expanded = self.args(selectors=["conditional_loads.extra"])
        self.assertEqual(self.read(expanded, [receipt])["chars"], 0)
        output = self.read(expanded, [receipt], stage_id=1)
        self.assertIn("route new evidence", output["content"])
        self.assertNotIn("shared author guidance", output["content"])
        self.assertEqual(stages.check_coverage(**expanded, receipts=[receipt])["pending_stages"], [1])
        extra = self.ack(output)
        self.assertEqual(stages.check_coverage(**expanded, receipts=[receipt, extra])["status"],
                         "ACKNOWLEDGED")

    def test_partial_receipt_does_not_inherit_reused_resources(self):
        original = self.ack(self.read())
        target = self.args("writing")
        partial = self.ack(self.read(target, [original]))
        coverage = stages.check_coverage(**target, receipts=[partial])
        self.assertEqual(coverage["pending_stages"], [0])
        missing = self.read(target, [partial])
        self.assertIn("shared author guidance", missing["content"])
        self.assertNotIn("writing core", missing["content"])
        recovered = self.ack(missing)
        self.assertEqual(stages.check_coverage(**target, receipts=[partial, recovered])["status"],
                         "ACKNOWLEDGED")

    def test_legacy_receipts_stay_valid_only_for_their_own_plan(self):
        receipt = self.ack(self.read())
        receipt.pop("schema", None)
        receipt.pop("source", None)
        self.assertEqual(stages.check_coverage(**self.args(), receipts=[receipt])["status"],
                         "ACKNOWLEDGED")
        with self.assertRaises(stages.ReceiptError):
            self.read(self.args("writing"), [receipt])

    def test_context_root_manifest_and_source_body_changes_reject_reuse(self):
        receipt = self.ack(self.read())
        with self.assertRaises(stages.ReceiptError):
            self.read(self.args("writing", context_id="different"), [receipt])
        changed = copy.deepcopy(receipt)
        changed.setdefault("source", {})["plugin_root"] = str(self.root / "elsewhere")
        with self.assertRaises(stages.ReceiptError):
            self.read(self.args("writing"), [changed])
        path = self.root / "skills/route/core.md"
        before = path.read_text(encoding="utf-8")
        path.write_text("changed source", encoding="utf-8")
        with self.assertRaises(stages.ReceiptError):
            self.read(self.args("writing"), [receipt])
        path.write_text(before, encoding="utf-8")
        manifest = self.root / "skills/route/manifest.yaml"
        value = json.loads(manifest.read_text(encoding="utf-8"))
        value["version"] = 2
        manifest.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(stages.ReceiptError):
            self.read(self.args("writing"), [receipt])

    def test_delivery_without_explicit_complete_read_does_not_allow_reuse(self):
        receipt = self.read()["receipt_template"]
        output = self.read(self.args("writing"), [receipt])
        self.assertIn("shared author guidance", output["content"])
        self.assertEqual(output["reused_chars"], 0)
        receipt["read_complete"] = True
        with self.assertRaises(stages.ReceiptError):
            self.read(self.args("writing"), [receipt])

    def test_source_request_and_resource_subset_cannot_be_forged(self):
        receipt = self.ack(self.read())
        for change in ("source", "resources", "plan_id", "duplicate"):
            altered = copy.deepcopy(receipt)
            if change == "source":
                altered.setdefault("source", {})["skill"] = "writing"
            elif change == "resources":
                altered["resources"] = [{"path": "skills/writing/core.md", "chars": 12, "sha256": "fake"}]
            elif change == "plan_id":
                altered["plan_id"] = "fake"
            receipts = [altered, copy.deepcopy(altered)] if change == "duplicate" else [altered]
            with self.subTest(change=change), self.assertRaises(stages.ReceiptError):
                self.read(self.args("writing"), receipts)

    def test_later_source_stage_requires_read_predecessors(self):
        source = self.args(selectors=["conditional_loads.extra"])
        first = self.ack(self.read(source))
        later = self.ack(self.read(source, [first], stage_id=1))
        with self.assertRaisesRegex(stages.ReceiptError, "predecessor"):
            self.read(self.args("writing"), [later])

    def test_circular_source_reads_cannot_supply_their_own_predecessors(self):
        (self.root / "skills/.shared/other.md").write_text("other", encoding="utf-8")
        later_receipts = []
        for name, core, extra in (("alpha", "other", "voice"), ("beta", "voice", "other")):
            folder = self.root / "skills" / name
            folder.mkdir()
            (folder / "manifest.yaml").write_text(json.dumps({
                "skill": name, "always_load": [f"../.shared/{core}.md"],
                "conditional_loads": {"extra": [f"../.shared/{extra}.md"]},
            }), encoding="utf-8")
            args = self.args(name, selectors=["conditional_loads.extra"])
            core_read = self.ack(self.read(args))
            later_receipts.append(self.ack(self.read(args, [core_read], stage_id=1)))
        with self.assertRaisesRegex(stages.ReceiptError, "cyclic predecessor"):
            self.read(receipts=later_receipts)

    def test_source_failure_is_a_receipt_error_and_does_not_return_partial_text(self):
        receipt = self.ack(self.read())
        (self.root / "skills/route/core.md").unlink()
        with self.assertRaisesRegex(stages.ReceiptError, "source can no longer be resolved"):
            self.read(self.args("writing"), [receipt])

    def test_target_snapshot_requires_matching_body_not_just_matching_path(self):
        original = self.ack(self.read())
        folder = self.root / "skills/shared-only"
        folder.mkdir()
        (folder / "manifest.yaml").write_text(json.dumps({
            "skill": "shared-only", "always_load": ["../.shared/voice.md"],
        }), encoding="utf-8")
        voice = self.root / "skills/.shared/voice.md"
        before = voice.read_text(encoding="utf-8")
        voice.write_text("x" * len(before), encoding="utf-8")
        target = stages.build_plan(**self.args("shared-only"))
        # Model a change between preparing the target and rebuilding the origin:
        # the receipt is valid for A, but the pending target body is B.
        voice.write_text(before, encoding="utf-8")
        read = stages._read_resources(target, [original])
        self.assertEqual(stages._covered_stages(target, read), set())

    def test_cli_reuses_existing_receipt_list_without_an_extra_workflow(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("load_skill_resources.py", "resource_stages.py"):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        command = [sys.executable, "-X", "utf8", str(scripts / "load_skill_resources.py")]
        context = ["--context-id", "synthetic-cli-context"]

        def call(skill, arguments):
            output = subprocess.run(command + ["--skill", skill] + context + arguments,
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(output.returncode, 0, output.stderr)
            return json.loads(output.stdout)

        first = self.ack(call("route", ["--stage", "0"]))
        receipt_file = self.root / "reads.json"
        receipt_file.write_text(json.dumps([first]), encoding="utf-8")
        second_output = call("writing", ["--stage", "0", "--receipts", str(receipt_file)])
        self.assertNotIn("shared author guidance", second_output["content"])
        self.assertIn("writing core", second_output["content"])
        second = self.ack(second_output)
        receipt_file.write_text(json.dumps([first, second]), encoding="utf-8")
        coverage = call("writing", ["--check-coverage", "--receipts", str(receipt_file)])
        self.assertEqual(coverage["status"], "ACKNOWLEDGED")
        repeated = call("writing", ["--stage", "0", "--receipts", str(receipt_file)])
        self.assertEqual(repeated["content"], "")
        self.assertIsNone(repeated["receipt_template"])

    def test_actual_theory_resources_are_reused_across_all_three_modules(self):
        receipts = []
        theory_deliveries = []
        for skill in ('journal-fit-style', 'evidence-audit', 'manuscript-writing'):
            args = dict(skill=skill, plugin_root=ROOT, context_id='synthetic-theory-reuse',
                        selectors=['shared_loads.theory_reasoning', 'shared_loads.theory_examples'])
            delivered = []
            for stage in stages.build_plan(**args)['stages']:
                output = stages.load_stage(**args, stage_id=stage['id'], receipts=receipts)
                if output['receipt_template']:
                    delivered.extend(r['path'] for r in output['receipt_template']['resources']
                                     if '/theory-reasoning' in r['path'])
                    receipts.append(self.ack(output))
            theory_deliveries.append(len(delivered))
            self.assertEqual(stages.check_coverage(**args, receipts=receipts)['status'], 'ACKNOWLEDGED')
        self.assertEqual(theory_deliveries, [2, 0, 0])

    def test_ordinary_load_has_no_new_receipt_requirement(self):
        result = loader.load_skill_resources(skill="writing", selectors=[], plugin_root=self.root)
        self.assertEqual(result.total_chars, len("shared author guidance") + len("writing core"))
        self.assertEqual(len(result.resources), 2)


if __name__ == "__main__":
    unittest.main()
