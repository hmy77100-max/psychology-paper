"""Public CLI checks using disposable author libraries."""
import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "literature_library.py"
WORK = {"title": "Attention at two distances", "doi": "10.5555/ABC", "authors": ["Lin Q"], "year": 2021}


class CitationComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPT.parent))
        cls.addClassCleanup(sys.path.remove, str(SCRIPT.parent))
        from literature_library import compare_citations
        cls.compare = staticmethod(compare_citations)

    def compare_pair(self, left, right, status, fields=()):
        result = self.compare(left, right)
        self.assertEqual(result, self.compare(right, left))
        self.assertEqual(status, result["status"])
        self.assertEqual(set(fields), set(result["differences"]))

    def test_full_names_and_initials_across_sources_and_years(self):
        left = dict(WORK, title="Attention: at two distances", authors=["Elizabeth A. Hoge", "Lin Q"])
        right = dict(WORK, doi="https://doi.org/10.5555/abc", authors=["Hoge EA", "Q. Lin"], year="2022")
        self.compare_pair(left, right, "same", ["year"])
        self.compare_pair(left, {**right, "authors": []}, "possible", ["year"])
        self.compare_pair(left, {**right, "year": 2024}, "conflict", ["year"])

    def test_wrong_doi_metadata_or_second_identifier_must_not_merge(self):
        self.compare_pair(WORK, {**WORK, "title": "The cost of emotional effort"}, "conflict", ["title"])
        self.compare_pair(WORK, {**WORK, "authors": ["Brown F"]}, "conflict", ["authors"])
        self.compare_pair({**WORK, "pmid": "123"}, {**WORK, "pmid": "124"}, "conflict", ["pmid"])
        self.compare_pair({**WORK, "authors": ["Lin Q", "Brown F"]},
                          {**WORK, "authors": ["Lin Q", "Smith G"]}, "conflict", ["authors"])

    def test_missing_identifier_and_same_title_are_only_candidates(self):
        self.compare_pair(WORK, {"title": WORK["title"]}, "possible")
        self.compare_pair(WORK, {**WORK, "doi": "10.5555/another"}, "possible", ["doi"])
        self.compare_pair({"title": "Study one"}, {"title": "Study two"}, "distinct")
        self.compare_pair(WORK, {"doi": WORK["doi"]}, "same")

    def test_registered_title_and_one_additional_subtitle(self):
        left = {"doi": "10.1001/jamapsychiatry.2022.3679", "authors": ["Elizabeth A. Hoge"],
                "title": "Mindfulness-Based Stress Reduction vs Escitalopram for the Treatment of Adults With Anxiety Disorders"}
        right = {**left, "authors": ["Hoge EA"], "title": left["title"] + ": A Randomized Clinical Trial."}
        self.compare_pair(left, right, "same", ["subtitle"])
        self.compare_pair({**left, "authors": []}, right, "possible", ["subtitle"])
        self.compare_pair({**left, "title": left["title"] + ": Outcomes in a Different Population"},
                          right, "conflict", ["title"])
        self.compare_pair(left, {**right, "title": left["title"] + ": Correction"}, "conflict", ["title"])
        self.compare_pair({**left, "title": "Results"}, {**right, "title": "Results: A Randomized Clinical Trial"},
                          "conflict", ["title"])

    def test_distinct_full_names_with_two_shared_words(self):
        self.compare_pair({**WORK, "authors": ["John Robert Smith"]},
                          {**WORK, "authors": ["John Robert Williams"]}, "conflict", ["authors"])

    def test_preprint_with_publication_doi_and_no_registered_relation_needs_review(self):
        journal = {**WORK, "type": "journal-article"}
        self.compare_pair({**WORK, "type": "preprint"}, journal, "possible", ["publication_type"])
        self.compare_pair({**WORK, "arxiv_id": "1507.04544v1"}, journal, "possible", ["publication_type"])
        self.compare_pair({**WORK, "publication_types": ["Published Erratum"]}, journal, "possible", ["publication_type"])
        self.compare_pair({**WORK, "publication_types": ["Journal Article", "Randomized Controlled Trial"]}, journal, "same")

    def test_pubmed_url_and_explicit_ids_describe_same_record(self):
        self.compare_pair({"title": "Trial", "pmid": "1234"}, {"title": "Trial", "url": "https://pubmed.ncbi.nlm.nih.gov/1234/"}, "same")
        self.compare_pair({"title": "Trial", "pmid": "1234"}, {"title": "Trial", "url": "https://example.org/1234/"}, "possible")

    def test_versioned_links_and_registered_publication_relationship(self):
        first = {"title": "Preprint", "url": "https://arxiv.org/abs/1507.04544v1"}
        later = {"title": "Methods", "arxiv_id": "1507.04544v5", "journal_doi": WORK["doi"]}
        self.compare_pair(first, {"title": "Preprint", "arxiv_id": "1507.04544v1"}, "same")
        self.compare_pair(first, later, "related", ["version"])
        self.compare_pair({"title": "Preprint", "arxiv_id": "1507.04544"}, first, "related", ["version"])
        self.compare_pair(later, WORK, "related", ["publication_type"])
        self.compare_pair(first, {**WORK, "relation": {"references": [{"id-type": "doi", "id": "10.4/source"}]}}, "distinct")
        self.compare_pair({**first, "relations": [("is-preprint-of", WORK["doi"])]}, WORK,
                          "related", ["publication_type"])


class LiteratureLibraryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.first, self.second = self.home / "paper1", self.home / "paper2"
        self.first.mkdir()
        self.second.mkdir()
        self.db = self.home / "PsychologyPaper" / "literature.sqlite3"

    def cli(self, *args, data=None, ok=True, cwd=None):
        env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home)}
        proc = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(SCRIPT), *args], input=json.dumps(data),
            capture_output=True, encoding="utf-8", errors="replace", cwd=cwd or self.first, env=env,
        )
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0)
        return json.loads(proc.stdout)

    def save(self, record, *options, **kwargs):
        return self.cli("save", "--input", "-", *options, data=record, **kwargs)

    def test_empty_reads_create_no_library(self):
        self.assertEqual([], self.cli("find", "attention")["records"])
        self.assertEqual("not_found", self.cli("show", "22")["status"])
        self.assertFalse(self.db.parent.exists())

    def test_save_receipt_identifies_the_actual_library_and_this_saves_attachment(self):
        created = self.cli("--library", "personal.db", "save", "--input", "-", data=WORK)
        self.assertEqual(str(self.first / "personal.db"), created.get("library_path"))
        self.assertEqual("none", created.get("attachment_disposition"))
        self.assertFalse(self.db.exists())

        src = self.first / "copy.pdf"
        src.write_bytes(b"selected copy")
        linked = self.save(WORK, "--attachment", src.name)
        key = str(linked["id"])
        self.assertEqual(str(self.db), linked.get("library_path"))
        self.assertEqual("linked_local", linked.get("attachment_disposition"))
        for options, expected in (
            (["--attachment", "zotero://select/library/items/ABCD1234"], "linked_zotero"),
            (["--attachment", src.name, "--store-file"], "stored_bytes"),
            (["--attachment", src.name, "--store-file"], "reused_stored_bytes"),
            (["--tag", "later"], "none"),
        ):
            with self.subTest(expected=expected):
                result = self.cli("save", "--id", key, *options)
                self.assertEqual(expected, result.get("attachment_disposition"))
        entries = self.cli("show", key)["record"]["reading"]
        digest = next(e["blob_sha256"] for e in entries if e["blob_sha256"])
        src.unlink()
        reused = self.cli("save", "--id", key, "--sha256", digest, "--read", "--locator", "Table 1")
        self.assertEqual("reused_stored_bytes", reused.get("attachment_disposition"))

    def test_reading_status_handles_missing_library_invalid_doi_and_unreadable_database(self):
        missing = self.cli("reading-status", "--doi", WORK["doi"])
        self.assertEqual("library_missing", missing["status"])
        self.assertEqual("error", self.cli("reading-status", ok=False)["status"])
        self.assertEqual("error", self.cli("reading-status", "--doi", "paper title", ok=False)["status"])
        self.assertFalse(self.db.parent.exists())
        broken = self.home / "corrupt.sqlite"
        broken.write_bytes(b"broken database")
        result = self.cli("--library", str(broken), "reading-status", "--doi", WORK["doi"], ok=False)
        self.assertEqual("error", result["status"])
        self.assertEqual(b"broken database", broken.read_bytes())

    def test_reading_status_limits_evidence_to_explicit_reads_of_the_exact_doi(self):
        self.save(WORK, "--attachment", "publisher.pdf", "--version", "published", "--locator", "p8",
                  "--note", "saved for later")
        read = self.save({**WORK, "doi": "10.5555/preprint"}, "--read", "--version", "preprint")
        self.assertEqual("no_local_record", self.cli("reading-status", "--doi", "10.5555/ab")["status"])
        first = self.cli("reading-status", "--doi", WORK["doi"])
        self.assertEqual(("saved_no_read_record", []), (first["status"], first["read_evidence"]))
        a = self.first / "accepted.pdf"
        a.write_bytes(b"accepted copy")
        self.save(WORK, "--read", "--attachment", a.name, "--store-file", "--version", "AAM",
                  "--locator", "Table 2", "--note", "private reading notes")
        before = self.db.read_bytes()
        result = self.cli("--library", str(self.db), "reading-status", "--doi", "https://doi.org/10.5555/ABC",
                          cwd=self.second)
        self.assertEqual(before, self.db.read_bytes())
        self.assertEqual(("has_read_record", "10.5555/abc"), (result["status"], result["doi"]))
        self.assertEqual(1, len(result["read_evidence"]))
        evidence = result["read_evidence"][0]
        self.assertEqual(("AAM", str(a), "Table 2"), (evidence["version"], evidence["attachment"], evidence["locator"]))
        self.assertTrue(evidence["blob_sha256"])
        self.assertNotIn("private reading notes", json.dumps(result))
        self.assertNotIn("publisher.pdf", json.dumps(result))
        self.assertNotEqual(read["id"], result["id"])

    def test_read_marker_without_a_version_does_not_identify_an_attachment(self):
        self.save(WORK, "--read")
        self.save(WORK, "--attachment", "unread.pdf", "--version", "published")
        result = self.cli("reading-status", "--doi", WORK["doi"])
        self.assertEqual("has_read_record", result["status"])
        self.assertEqual([{"version": "", "attachment": "", "locator": "", "blob_sha256": ""}],
                         result["read_evidence"])

    def test_discovery_preview_needs_full_record_before_save(self):
        preview = {"source": "Europe PMC", "status": "candidates", "preview_only": True,
                   "records": [{"title": "A shortlisted paper", "doi": WORK["doi"]}]}
        result = self.save(preview, ok=False)
        self.assertEqual(result["status"], "error")
        self.assertIn("preview", result["detail"].lower())
        self.assertFalse(self.db.exists())

    def test_saved_preprints_and_pubmed_records_can_be_recalled_by_exact_source_url(self):
        first_url = "https://arxiv.org/abs/1507.04544v1"
        later_url = first_url + "0"
        first = self.save({"source": "arXiv", "url": first_url, "title": "Two versions"})["id"]
        later = self.save({"source": "arXiv", "url": later_url, "title": "Two versions"}, "--separate")["id"]
        public_id = self.save(dict(WORK, url="https://doi.org/" + WORK["doi"]))["id"]
        pubmed_url = "https://pubmed.ncbi.nlm.nih.gov/36350591/"
        self.save(dict(WORK, source="PubMed", url=pubmed_url))
        for url, expected in ((first_url, first), (later_url, later), (pubmed_url, public_id)):
            with self.subTest(url=url):
                self.assertEqual([expected], [r["id"] for r in self.cli("find", url, cwd=self.second)["records"]])

    def test_crossref_selection_and_reopen_from_another_paper(self):
        envelope = {"source": "Crossref", "status": "candidates", "retrieved_at": "2026-11-20",
                    "request_url": "https://api.crossref.org/works?query=attention",
                    "records": [{"title": "Different", "doi": "10.5555/other"}, WORK]}
        self.save(envelope, ok=False)
        self.assertFalse(self.db.exists())
        key = self.save(envelope, "--pick", "2", "--tag", "心理距离")["id"]
        found = self.cli("find", "心理距离", cwd=self.second)["records"]
        self.assertEqual([key], [r["id"] for r in found])
        record = self.cli("show", str(key), cwd=self.second)["record"]
        self.assertEqual(WORK["title"], record["title"])
        self.assertEqual("Crossref", record["sources"][0]["source"])
        self.assertEqual("2026-11-20", record["sources"][0]["retrieved_at"])
        self.assertTrue(self.db.is_file())
        self.assertFalse((self.second / "literature.sqlite3").exists())

    def test_duplicate_doi_preserves_prior_sources_and_attachment_specific_reading(self):
        a, b = self.first / "accepted.pdf", self.first / "publisher.pdf"
        a.touch()
        b.touch()
        one = self.save({**WORK, "source": "author website"}, "--read", "--attachment", a.name,
                        "--locator", "p. 4", "--note", "实际读过", "--tag", "复查")
        two = self.save({**WORK, "doi": "https://doi.org/10.5555/abc", "source": "publisher"},
                        "--attachment", b.name)
        self.assertEqual(one["id"], two["id"])
        self.cli("save", "--id", str(one["id"]), "--read", "--attachment", a.name,
                 "--locator", "p. 4", "--note", "实际读过")
        r = self.cli("show", str(one["id"]))["record"]
        self.assertEqual(2, len(r["sources"]))
        self.assertEqual(2, len(r["reading"]))
        traces = {entry["attachment"]: entry for entry in r["reading"]}
        self.assertTrue(traces[str(a)]["read"])
        self.assertFalse(traces[str(b)]["read"])
        self.assertEqual("p. 4", traces[str(a)]["locator"])
        self.assertEqual([one["id"]], [x["id"] for x in self.cli("find", "实际读过")["records"]])

    def test_conflicting_doi_does_not_write_source_tags_or_reading(self):
        saved = self.save(dict(WORK, source="Crossref"), "--read", "--version", "accepted",
                          "--locator", "p. 4", "--note", "keep this annotation")
        key = str(saved["id"])
        original = self.cli("show", key)["record"]
        impostor = dict(WORK, source="PubMed", title="Workload in flight simulators", authors=["Rivera J"])
        for flags in ([], ["--id", key], ["--separate"]):
            with self.subTest(flags=flags):
                result = self.save(impostor, *flags, "--attachment", "wrong.pdf", "--tag", "wrong",
                                   "--read", ok=False)
                self.assertEqual("metadata_conflict", result["status"])
                self.assertIn("title", result["differences"])
                self.assertEqual("PubMed", result["incoming"]["source"])
                self.assertEqual(original, self.cli("show", key)["record"])

    def test_legacy_source_provenance_survives_later_confirmed_save(self):
        old = dict(WORK, source="Crossref")
        key = str(self.save(old)["id"])
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("DROP TABLE IF EXISTS source_citations")
        legacy = self.cli("show", key)["record"]
        self.assertEqual(["Crossref"], [s["source"] for s in legacy["sources"]])
        self.assertFalse(legacy["sources"][0].get("citations"))
        incoming = dict(WORK, source="PubMed", authors=["Lin Q", "Chen J"], pmid="12345")
        self.save(incoming, "--id", key)
        record = self.cli("show", key)["record"]
        by_source = {s["source"]: s for s in record["sources"]}
        self.assertFalse(by_source["Crossref"].get("citations"))
        self.assertEqual(["Lin Q", "Chen J"], by_source["PubMed"]["citations"][0]["authors"])
        self.assertEqual("12345", by_source["PubMed"]["citations"][0]["pmid"])

    def test_source_years_retained_and_conflicting_secondary_pmid_refused(self):
        key = str(self.save(dict(WORK, source="Crossref"))["id"])
        later = dict(WORK, source="PubMed", year=2022, pmid="12345")
        self.save(later)
        self.save(later)
        before = self.cli("show", key)["record"]
        sources = {s["source"]: s["citations"] for s in before["sources"]}
        self.assertEqual(["2021"], [s["year"] for s in sources["Crossref"]])
        self.assertEqual(["2022"], [s["year"] for s in sources["PubMed"]])
        result = self.save(dict(later, pmid="98765", source="Europe PMC"), "--id", key, ok=False)
        self.assertEqual("metadata_conflict", result["status"])
        self.assertIn("pmid", result["differences"])
        self.assertEqual("PubMed", result["stored"]["source"])
        self.assertEqual(before, self.cli("show", key)["record"])

    def test_save_checks_reported_author_count_when_lists_are_truncated(self):
        key = self.save(dict(WORK, source="Crossref", author_count=4))["id"]
        result = self.save(dict(WORK, source="PubMed", author_count=18), ok=False)
        self.assertEqual(("metadata_conflict", key), (result["status"], result["id"]))
        self.assertIn("authors", result["differences"])
        self.assertEqual(4, result["stored"]["author_count"])
        self.assertEqual(18, result["incoming"]["author_count"])

    def test_publication_type_needs_review_in_either_save_order(self):
        article = {"type": "journal-article"}
        preprint = {"type": "posted-content"}
        notice = {"type": "Journal Article", "publication_types": ["Journal Article", "Published Erratum"]}
        for n, (first, next_type) in enumerate(((article, preprint), (preprint, article),
                                                (article, notice), (notice, article))):
            with self.subTest(first=first, next_type=next_type):
                work = dict(WORK, doi=f"10.5555/form-{n}")
                key = str(self.save(dict(work, **first), "--read")["id"])
                if n == 0:
                    with closing(sqlite3.connect(self.db)) as db, db:
                        db.execute("DROP TABLE IF EXISTS source_citations")
                before = self.cli("show", key)["record"]
                for flags in ([], ["--id", key]):
                    result = self.save(dict(work, **next_type), *flags, "--tag", "should not be saved", ok=False)
                    self.assertEqual("possible_duplicate", result["status"])
                    self.assertIn("publication_type", result["differences"])
                self.assertEqual(before, self.cli("show", key)["record"])

    def test_known_preprint_versions_cannot_share_reading_via_explicit_id(self):
        first = {"title": "Method", "source": "arXiv", "arxiv_id": "1507.04544v1"}
        key = str(self.save(first, "--read", "--version", "v1")["id"])
        later = dict(first, arxiv_id="1507.04544v5")
        result = self.save(later, "--id", key, ok=False)
        self.assertEqual("metadata_conflict", result["status"])
        separate = self.save(later, "--separate")
        self.assertFalse(self.cli("show", str(separate["id"]))["record"]["read"])

    def test_related_dois_stay_separate_and_resolve_from_either_version(self):
        pre = self.save({**WORK, "doi": "10.5555/pre", "relation":
                         {"is-preprint-of": [{"id-type": "doi", "id": WORK["doi"]}]}}, "--read")
        pub = self.save(WORK)
        self.assertNotEqual(pub["id"], pre["id"])
        for a, b in [(pub, pre), (pre, pub)]:
            r = self.cli("show", str(a["id"]))["record"]
            self.assertEqual(b["id"], r["related"][0]["id"])
        self.assertFalse(self.cli("show", str(pub["id"]))["record"]["read"])

    def test_unidentified_same_title_requires_explicit_decision(self):
        one = self.save({"title": "某篇文章", "authors": ["甲"]})
        pending = self.save({"title": " 某篇文章 ", "authors": ["乙"]}, ok=False)
        self.assertEqual("possible_duplicate", pending["status"])
        self.assertEqual(one["id"], pending["records"][0]["id"])
        two = self.save({"title": "某篇文章", "authors": ["乙"]}, "--separate")
        self.assertNotEqual(one["id"], two["id"])

    def test_shared_web_page_is_a_suggestion_not_a_version_identity(self):
        url = "https://example.org/lab/publications"
        first = self.save({"title": "Working paper", "url": url})["id"]
        other = {"title": "Different lab paper", "url": url}
        suggestion = self.save(other, ok=False)
        self.assertEqual("possible_duplicate", suggestion["status"])
        self.assertEqual([first], [r["id"] for r in suggestion["records"]])
        second = self.save(other, "--separate")["id"]
        self.assertNotEqual(first, second)
        self.assertEqual(second, self.save(other, "--id", str(second), "--tag", "confirmed")["id"])
        matches = self.save(other, ok=False)
        self.assertEqual([first, second], [r["id"] for r in matches["records"]])

    def test_parallel_saves_of_one_record_retain_each_tag(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            saved = list(pool.map(lambda n: self.save(WORK, "--tag", str(n))["id"], range(4)))
        self.assertEqual(1, len(set(saved)))
        r = self.cli("show", str(saved[0]))["record"]
        self.assertEqual(["0", "1", "2", "3"], r["tags"])

    def test_author_can_confirm_an_unidentified_record_now_has_a_doi(self):
        one = self.save({"title": WORK["title"], "source": "reading list"}, "--tag", "earlier")
        self.assertEqual("possible_duplicate", self.save(WORK, ok=False)["status"])
        linked = self.save(WORK, "--id", str(one["id"]))
        self.assertEqual(one["id"], linked["id"])
        self.assertEqual(one["id"], self.save(WORK)["id"])
        r = self.cli("show", str(one["id"]))["record"]
        self.assertEqual(WORK["doi"].lower(), r["doi"])
        self.assertEqual(2, len(r["sources"]))
        self.assertEqual(["earlier"], r["tags"])
        mismatch = self.save({**WORK, "doi": "10.5555/different"}, "--id", str(one["id"]), ok=False)
        self.assertEqual("metadata_conflict", mismatch["status"])
        self.assertIn("doi", mismatch["differences"])

    def test_same_attachment_distinct_version_notes_survive_a_missing_file(self):
        path = self.first / "my-copy.pdf"
        path.touch()
        key = self.save(WORK, "--attachment", path.name, "--version", "AAM",
                        "--locator", "p2", "--read")["id"]
        self.save(WORK, "--attachment", path.name, "--version", "corrected", "--locator", "p8")
        self.save(WORK, "--attachment", path.name, "--version", "corrected", "--locator", "p8")
        self.assertTrue(self.cli("show", str(key))["record"]["reading"][0]["attachment_available"])
        path.unlink()
        r = self.cli("show", str(key))["record"]
        self.assertEqual(1, len(r["sources"]))
        self.assertEqual([(v["version"], v["locator"], v["read"]) for v in r["reading"]],
                         [("AAM", "p2", True), ("corrected", "p8", False)])
        self.assertTrue(all(v["attachment_available"] is False for v in r["reading"]))

    def test_explicit_attachment_storage_keeps_revisions_and_exports_selected_original_bytes(self):
        src = self.first / "source.pdf"
        src.write_bytes(b"first-version")
        key = self.save(WORK, "--attachment", str(src), "--version", "AAM", "--store-file",
                        "--read", "--locator", "p2")["id"]
        src.write_bytes(b"next-version")
        self.cli("save", "--id", str(key), "--attachment", str(src), "--version", "published", "--store-file")
        self.cli("save", "--id", str(key), "--attachment", str(src), "--version", "published", "--store-file")
        src.unlink()
        entries = self.cli("show", str(key))["record"]["reading"]
        self.assertEqual(2, len(entries))
        self.assertNotEqual(entries[0]["blob_sha256"], entries[1]["blob_sha256"])
        self.assertTrue(entries[0]["read"])
        self.assertFalse(entries[1]["read"])
        out = self.second / "retrieved.pdf"
        self.cli("export-attachment", str(key), "--output", str(out), ok=False)
        self.assertFalse(out.exists())
        self.cli("export-attachment", str(key), "--output", str(out), "--sha256", entries[0]["blob_sha256"])
        self.assertEqual(b"first-version", out.read_bytes())
        self.cli("export-attachment", str(key), "--output", str(out), "--sha256", entries[1]["blob_sha256"], ok=False)
        self.assertEqual(b"first-version", out.read_bytes())
        other = self.save({**WORK, "doi": "10.5555/other"})["id"]
        self.cli("export-attachment", str(other), "--output", str(self.second / "no.pdf"),
                 "--sha256", entries[0]["blob_sha256"], ok=False)

    def test_missing_file_rolls_back_entire_save(self):
        self.save(WORK, "--tag", "new", "--store-file", "--attachment", "absent.pdf", ok=False)
        self.assertEqual([], self.cli("find", "new")["records"])

    def test_later_reading_can_be_attached_to_an_existing_stored_copy(self):
        src = self.first / "archived.pdf"
        src.write_bytes(b"file to read later")
        key = self.save(WORK, "--version", "AAM", "--attachment", str(src), "--store-file")["id"]
        digest = self.cli("show", str(key))["record"]["reading"][0]["blob_sha256"]
        src.unlink()
        self.cli("save", "--id", str(key), "--sha256", digest, "--read", "--locator", "Table 2")
        entries = self.cli("show", str(key))["record"]["reading"]
        self.assertEqual([(r["attachment"], r["version"], r["blob_sha256"]) for r in entries],
                         [(str(src), "AAM", digest)] * 2)
        self.assertTrue(entries[1]["read"])
        self.assertEqual("Table 2", entries[1]["locator"])
        self.cli("save", "--id", str(key), "--sha256", "a" * 64, "--read", ok=False)

    def test_broad_search_can_retrieve_an_older_paper_beyond_first_page(self):
        first = self.save(WORK)["id"]
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executemany("INSERT INTO works(title,title_key,authors) VALUES(?,?,'[]')",
                           [(f"Attention {i}", f"attention {i}") for i in range(50)])
        results = self.cli("find", "Attention")
        self.assertEqual(50, len(results["records"]))
        self.assertEqual(50, results["next_offset"])
        next_page = self.cli("find", "Attention", "--offset", "50")
        self.assertEqual([first], [r["id"] for r in next_page["records"]])
        self.assertIsNone(next_page["next_offset"])


class LiteratureRouteTests(unittest.TestCase):
    def test_reading_intents_never_grant_manuscript_writing(self):
        from test_workflow_guards import load_guards
        guards = load_guards()
        for task in ("literature_library", "zotero_read"):
            for active in (False, True):
                result = guards.decide_project_mode(task=task, scope="cross_session",
                                                     journal_status="unknown", project_mode_active=active)
                self.assertEqual(result.status, "STANDALONE_LIBRARY")
                self.assertFalse(result.writing_allowed)

    def test_library_resource_only_loads_on_request(self):
        loader = SCRIPT.with_name("load_skill_resources.py")
        def paths(*selected):
            result = subprocess.run([sys.executable, "-B", str(loader), "--skill", "psychology-paper",
                                     "--describe", *selected], capture_output=True, check=True)
            return [r["path"] for r in json.loads(result.stdout)["resources"]]
        self.assertNotIn("references/literature-library.md", paths())
        self.assertIn("references/literature-library.md", paths("--select", "conditional_loads.literature_library"))


class CompareSourcesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.database = self.directory / "private" / "library.db"

    def compare(self, *envelopes, stdin=False, ok=True, check_offset=None):
        args = [sys.executable, "-B", "-X", "utf8", str(SCRIPT),
                "--library", str(self.database), "compare"]
        for index, payload in enumerate(envelopes):
            path = self.directory / f"response{index}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            args.extend(["--input", "-" if stdin and index == 0 else str(path)])
        if check_offset is not None:
            args.extend(["--check-offset", str(check_offset)])
        proc = subprocess.run(args, input=json.dumps(envelopes[0]) if stdin else None,
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode == 0, ok, proc.stderr or proc.stdout)
        self.assertFalse(self.database.parent.exists())
        return json.loads(proc.stdout)

    @staticmethod
    def result(source, *rows, **extra):
        return dict({"source": source, "status": "candidates", "records": list(rows)}, **extra)

    def test_compares_brief_and_full_records_without_network_or_writes(self):
        work = {"title": "Comparing stress in adults", "doi": "10.5555/test", "authors": ["P Smith"], "year": 2020}
        first = self.result("Crossref", dict(work, abstract={"content": "Entire original abstract"}))
        second = self.result("PubMed", {"title": work["title"], "doi": work["doi"], "first_author": "P Smith",
                                        "pmid": "1234", "year": 2020}, preview_only=True, total_results=3, truncated=True)
        result = self.compare(first, second, stdin=True)
        self.assertTrue(result["preview_only"])
        self.assertEqual(result["status"], "compared")
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual(result["groups"][0]["origins"], [{"source": "Crossref", "input": 1, "row": 1},
                                                          {"source": "PubMed", "input": 2, "row": 1}])
        self.assertEqual(result["inputs"][1]["total_results"], 3)
        self.assertTrue(result["inputs"][1]["truncated"])
        self.assertNotIn("Entire original abstract", json.dumps(result))

    def test_conflicting_records_cannot_merge_via_a_sparse_third_record(self):
        first = {"title": "Comparing sleep patterns in college students", "doi": "10.5555/test",
                 "authors": ["P Smith"], "year": 2020}
        third = dict(first, title="Learning motor skills in adolescents")
        bridge = {"doi": first["doi"]}
        result = self.compare(self.result("Crossref", first), self.result("OpenAlex", bridge),
                              self.result("PubMed", third))
        positions = [{(r["input"], r["row"]) for r in g["origins"]} for g in result["groups"]]
        self.assertFalse(any({(1, 1), (3, 1)} <= group for group in positions))
        self.assertIn("conflict", {item["status"] for item in result["checks"]})

    def test_years_stay_attributable_to_the_source_that_reported_them(self):
        first = {"title": "Comparing stress in adults", "doi": "10.5555/test", "authors": ["P Smith"], "year": 2019}
        result = self.compare(self.result("Crossref", first), self.result("PubMed", dict(first, year=2020)))
        self.assertEqual(1, len(result["groups"]))
        self.assertEqual([(r["source"], r["reported"]["year"]) for r in result["groups"][0]["origins"]],
                         [("Crossref", 2019), ("PubMed", 2020)])

    def test_partial_sources_and_empty_windows_keep_their_actual_status(self):
        work = {"doi": "10.5555/partial", "title": "An indexed paper"}
        result = self.compare(self.result("Crossref", status="not_found", total_results=0),
                              self.result("PubMed", work, status="partial", missing_pmids=["1234"]),
                              self.result("OpenAlex", status="rate_limited", retry_after="60"))
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["groups"]), 1)
        self.assertEqual([s["status"] for s in result["inputs"]], ["not_found", "partial", "rate_limited"])
        self.assertEqual(result["inputs"][1]["missing_pmids"], ["1234"])
        self.assertEqual(result["inputs"][2]["retry_after"], "60")

    def test_many_ambiguous_pairs_have_a_bounded_retrievable_check_page(self):
        same_title = {"title": "Performance under time pressure"}
        windows = (self.result("Crossref", *([same_title] * 6)), self.result("PubMed", *([same_title] * 6)))
        first = self.compare(*windows)
        self.assertEqual(12, len(first["groups"]))
        self.assertEqual(66, first["total_checks"])
        self.assertEqual(50, len(first["checks"]))
        next_page = self.compare(*windows, check_offset=first["next_check_offset"])
        self.assertEqual(16, len(next_page["checks"]))
        self.assertIsNone(next_page["next_check_offset"])
        self.assertEqual(66, len({tuple(row["groups"]) for row in first["checks"] + next_page["checks"]}))

    def test_rejects_non_search_payloads_without_touching_library(self):
        valid = self.result("Crossref", {"doi": "10.5555/test"})
        for other in ([valid], self.result("PubMed", {"doi": "10.5555/test"}, status="passages"),
                      self.result("PubMed", {"title": ["bad field type"]}),
                      self.result("Crossref", *([{"title": "candidate"}] * 21))):
            with self.subTest(other=str(other)[:90]):
                self.assertEqual(self.compare(valid, other, ok=False)["status"], "error")
