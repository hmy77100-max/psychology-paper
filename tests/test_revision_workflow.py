"""Executable synthetic revision journeys; never open real manuscripts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import revision_check as revision
from project_state import render_json_frontmatter


class RevisionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = "第一段原文。\n第二段原文。"
        self.source = self.file("paper.txt", self.original)
        self.extract = self.file("extract.txt", self.original)
        self.artifact = self.file("candidate.txt", "中文原文\n" + self.original +
                                  "\n修改后中文\n合并后的候选。\n必要说明\n合并两个排版段，保留论点。")
        self.unit = {"id": "body-1", "section": "introduction", "function": "motivate question",
                     "closure": "complete rationale", "spans": [[0, len(self.original)]], "status": "PENDING"}
        self.record = {"mode": "chinese", "source": self.source,
                       "extraction": {**self.extract, "source_sha256": self.source["sha256"]},
                       "unit": self.unit, "artifact": self.artifact}
        self.profile = self.root / "journal.md"
        budget = {"limit": 100, "unit": "characters", "counting_scope": "main_text"}
        self.profile.write_text(render_json_frontmatter({"status": "approved", "journal_name": "Example",
            "body_budget": {**budget, "source_url": "https://example.org/guide", "verified_on": "2026-09-30"}}, "Profile"), encoding="utf-8")
        self.state = {"schema": "psychology-paper-project", "schema_version": 1,
            "project_root": str(self.root), "authoritative_manuscript": self.source["path"],
            "sources": [{"path": self.source["path"], "role": "AUTHORITATIVE"}],
            "optional_state_files": {"journal_profile": str(self.profile)},
            "journal": {"name": "Example", "status": "USER_CONFIRMED"},
            "body_budget": {**budget, "current": revision.count_text(self.original, "characters"),
                "status": "WITHIN_LIMIT", "baseline_status": "CURRENT", "baseline": {
                    **self.extract, "source_sha256": self.source["sha256"], "adoption_status": "USER_ADOPTED"}},
            "source_sha256": self.source["sha256"], "issued_candidate_ids": [],
            "framing": {"status": "AUTHOR_CONFIRMED", "statement": "bounded contribution", "author_response": "我想突出这个问题"},
            "revision": {"content_revision": 0, "units": [copy.deepcopy(self.unit),
                {"id": "abstract", "section": "abstract", "status": "PENDING"},
                {"id": "keywords", "section": "keywords", "status": "PENDING"}]}}
        self.save_state()

    def file(self, name, text):
        p = self.root / name
        p.write_text(text, encoding="utf-8")
        return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}

    def save_state(self):
        p = self.root / ".psychology-paper" / "PROJECT.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(render_json_frontmatter(self.state, "State"), encoding="utf-8")

    def test_cross_paragraph_candidate_matches_whole_logical_unit(self):
        self.assertEqual(revision.validate_candidate(self.record, self.root), [])

    def test_missing_original_reordered_sections_and_empty_notes_fail(self):
        for text in ["修改后中文\n候选\n必要说明\n理由", "修改后中文\n候选\n中文原文\n原文\n必要说明\n理由",
                     "中文原文\n" + self.original + "\n修改后中文\n候选\n必要说明\n"]:
            with self.subTest(text=text):
                self.record["artifact"] = self.file("candidate.txt", text)
                self.assertTrue(revision.validate_candidate(self.record, self.root))

    def test_abbreviated_original_or_stale_source_fails(self):
        self.record["artifact"] = self.file("candidate.txt", "中文原文\n第一段……\n修改后中文\n候选\n必要说明\n理由")
        self.assertTrue(revision.validate_candidate(self.record, self.root))
        Path(self.source["path"]).write_text("changed", encoding="utf-8")
        self.assertTrue(revision.validate_candidate(self.record, self.root))

    def test_overlapping_spans_or_missing_function_fails(self):
        self.record["unit"]["spans"] = [[0, 5], [3, 8]]
        self.assertTrue(revision.validate_candidate(self.record, self.root))
        self.record["unit"] = {**self.unit, "function": ""}
        self.assertTrue(revision.validate_candidate(self.record, self.root))

    def test_preflight_reads_actual_standard_files(self):
        self.assertEqual(revision.preflight(self.root), [])
        self.state["body_budget"]["current"] = 999
        self.save_state()
        self.assertTrue(revision.preflight(self.root))

    def test_unknown_scope_unconfirmed_framing_and_unapproved_profile_block(self):
        for field in ("scope", "framing", "profile"):
            with self.subTest(field=field):
                original = copy.deepcopy(self.state)
                if field == "scope": self.state["body_budget"]["counting_scope"] = "unresolved"
                if field == "framing": self.state["framing"]["status"] = "CANDIDATE"
                if field == "profile": self.profile.write_text("not approved frontmatter", encoding="utf-8")
                self.save_state()
                self.assertTrue(revision.preflight(self.root))
                self.state = original

    def test_abstract_waits_for_body_and_keywords_for_current_abstract(self):
        self.assertTrue(revision.check_stage(self.state, "abstract"))
        self.assertTrue(revision.check_stage(self.state, "keywords"))
        self.assertEqual(revision.check_stage(self.state, "abstract", "本次只改摘要"), [])
        self.state["revision"]["units"][0].update(status="APPROVED", source_sha256=self.source["sha256"])
        self.assertEqual(revision.check_stage(self.state, "abstract"), [])
        self.state["revision"]["units"][1].update(status="APPROVED", body_revision=0, source_sha256=self.source["sha256"])
        self.assertEqual(revision.check_stage(self.state, "keywords"), [])

    def test_free_author_language_approves_and_invalidates_later_sections(self):
        self.state["revision"]["units"][1]["status"] = "APPROVED"
        self.save_state()
        result = revision.propose_decision(self.root, self.record, "APPROVE_CURRENT", "这个版本合我意，往后走")
        self.assertEqual(result["errors"], [])
        state = result["proposed_state"]
        self.assertEqual(state["revision"]["units"][0]["status"], "APPROVED")
        self.assertEqual(state["revision"]["units"][1]["status"], "PENDING")
        self.assertEqual(state["body_budget"]["baseline_status"], "REFRESH_REQUIRED")
        self.assertEqual(revision.preflight(self.root), [])  # proposed state was not silently saved

    def test_partial_and_advance_do_not_approve_candidate(self):
        for intent in ("PARTIAL", "ADVANCE_ONLY", "REJECT", "DEFER"):
            result = revision.propose_decision(self.root, self.record, intent, "保留开头，后面我还想想")
            self.assertNotEqual(result.get("proposed_state", self.state)["revision"]["units"][0]["status"], "APPROVED")

    def test_invalid_candidate_cannot_be_approved(self):
        self.record["artifact"] = self.file("candidate.txt", "修改后中文\nonly candidate")
        for intent in ("APPROVE_CURRENT", "ADVANCE_ONLY"):
            result = revision.propose_decision(self.root, self.record, intent, "可以")
            self.assertTrue(result["errors"])
            self.assertNotIn("proposed_state", result)

    def test_refresh_required_blocks_new_candidate_and_repeat_is_idempotent(self):
        result = revision.propose_decision(self.root, self.record, "APPROVE_CURRENT", "采用")
        self.state = result["proposed_state"]
        self.save_state()
        self.assertTrue(revision.preflight(self.root))
        again = revision.propose_decision(self.root, self.record, "APPROVE_CURRENT", "刚才那版采用")
        self.assertEqual(again["status"], "ALREADY_APPROVED")
        self.assertEqual(again["proposed_state"]["body_budget"]["current"], self.state["body_budget"]["current"])

    def test_sync_uses_observed_version_and_keeps_translation_candidate(self):
        record = {"authorized": True, "unit_id": "body-1", "chinese": self.extract,
                  "english_based_on_sha256": "old", "chinese_status": "CANDIDATE"}
        result = revision.sync_status(record, self.root)
        self.assertEqual(result["status"], "UPDATE_CANDIDATE")
        self.assertFalse(result["write_allowed"])
        record["english_based_on_sha256"] = self.extract["sha256"]
        record["english"] = self.file("english.txt", "English candidate")
        self.assertEqual(revision.sync_status(record, self.root)["status"], "CURRENT")
        record["authorized"] = False
        self.assertEqual(revision.sync_status(record, self.root)["status"], "AUTHORIZATION_REQUIRED")

    def test_preflight_rejects_illegal_shared_state_and_empty_plan(self):
        self.state["current_action"] = {"decision_status": "CANDIDATE", "write_permission": "WRITE_ALLOWED"}
        self.save_state()
        self.assertTrue(revision.preflight(self.root))
        self.state.pop("current_action")
        self.state["revision"]["units"] = []
        self.save_state()
        self.assertTrue(revision.preflight(self.root))

    def test_counted_candidate_must_use_current_adopted_baseline(self):
        other = self.file("adopted.txt", "已经采用的不同内容。")
        self.state["body_budget"].update(current=revision.count_text("已经采用的不同内容。", "characters"),
            baseline={**other, "source_sha256": self.source["sha256"], "adoption_status": "USER_ADOPTED"})
        self.save_state()
        for intent in ("APPROVE_CURRENT", "RETAIN_CURRENT"):
            result = revision.propose_decision(self.root, self.record, intent, "按这个决定")
            self.assertTrue(result["errors"])

    def test_abstract_change_invalidates_keywords(self):
        self.unit["section"] = "abstract"
        self.state["revision"]["units"] = [copy.deepcopy(self.unit),
            {"id": "body", "section": "discussion", "status": "APPROVED", "source_sha256": self.source["sha256"]},
            {"id": "keywords", "section": "keywords", "status": "APPROVED", "source_sha256": self.source["sha256"], "body_revision": 0}]
        self.save_state()
        result = revision.propose_decision(self.root, self.record, "APPROVE_CURRENT", "采用摘要")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["proposed_state"]["revision"]["units"][2]["status"], "PENDING")

    def test_same_artifact_cannot_silently_change_retain_into_approval(self):
        result = revision.propose_decision(self.root, self.record, "RETAIN_CURRENT", "还是保留我的原文")
        self.state = result["proposed_state"]
        self.save_state()
        result = revision.propose_decision(self.root, self.record, "APPROVE_CURRENT", "我改主意了，用候选")
        self.assertEqual(result["status"], "PROPOSED")
        self.assertEqual(result["proposed_state"]["revision"]["units"][0]["status"], "APPROVED")

    def run_cli(self, command, *args):
        return subprocess.run([sys.executable, "-X", "utf8", str(Path(revision.__file__)), command,
            "--project-root", str(self.root), *args], capture_output=True, text=True, encoding="utf-8")

    def test_stage_cli_blocks_early_abstract_and_records_explicit_exception(self):
        result = self.run_cli("stage", "--section", "abstract")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(json.loads(result.stdout)["errors"])
        result = self.run_cli("stage", "--section", "abstract", "--explicit-stage-request", "本次先给我摘要候选")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["author_stage_request"], "本次先给我摘要候选")

    def test_cli_candidate_and_decision_are_read_only(self):
        self.file("record.json", json.dumps(self.record, ensure_ascii=False))
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for command, args in [("candidate", []), ("decision", ["--intent", "APPROVE_CURRENT", "--author-response", "就用这一版吧"] )]:
            result = self.run_cli(command, "--record", "record.json", *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["read_only"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_sync_cannot_call_a_missing_or_changed_english_file_current(self):
        record = {"authorized": True, "unit_id": "body-1", "chinese": self.extract,
                  "english_based_on_sha256": self.extract["sha256"], "chinese_status": "APPROVED"}
        self.assertNotEqual(revision.sync_status(record, self.root)["status"], "CURRENT")
        record["english"] = self.file("english.txt", "first")
        Path(record["english"]["path"]).write_text("changed", encoding="utf-8")
        self.assertEqual(revision.sync_status(record, self.root)["status"], "UNRESOLVED")

    def test_malformed_records_return_bounded_errors(self):
        self.record["unit"] = []
        self.assertTrue(revision.validate_candidate(self.record, self.root))
        self.state["revision"] = None
        self.save_state()
        result = self.run_cli("preflight")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(json.loads(result.stdout)["errors"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
