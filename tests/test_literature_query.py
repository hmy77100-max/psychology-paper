"""Offline checks for the public Crossref query CLI."""

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import literature_query


DOI = "10.1234/trial"
WORK = {
    "DOI": DOI,
    "title": ["记忆与学习"],
    "author": [{"given": "Wei", "family": "Chen"}, {"name": "Research Group"}],
    "container-title": ["Test Journal"],
    "published": {"date-parts": [[2024, 2]]},
    "type": "journal-article",
    "relation": {"has-preprint": [{"id-type": "doi", "id": "10.1234/preprint"}]},
}


def work_list(*items):
    return {"status": "ok", "message-type": "work-list", "message": {"items": list(items)}}


def single(work):
    return {"status": "ok", "message-type": "work", "message": work}


class SourceSelectionTests(unittest.TestCase):
    def run_cli(self, args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = literature_query.main(args)
        return code, json.loads(output.getvalue())

    def test_pubmed_search_retains_field_warnings_in_compact_results(self):
        result = dict(literature_query.result_envelope("PubMed"), status="candidates", returned=1,
                      warnings=["One search term was ignored."], records=[{"title": "Target", "pmid": "1234"}])
        with patch.object(literature_query, "query_pubmed", return_value=result, create=True) as lookup:
            code, out = self.run_cli(["--source", "pubmed", "--query", "sleep[mh]", "--brief"])
        self.assertEqual(0, code)
        self.assertEqual(result["warnings"], out["warnings"])
        self.assertEqual("1234", out["records"][0]["pmid"])
        self.assertEqual(1, lookup.call_count)

    def test_versioned_arxiv_id_in_discovery_and_exact_read(self):
        record = {"arxiv_id": "1507.04544v1", "version": "v1", "title": "Preprint", "submitted_date": "2015-07-16"}
        with patch.object(literature_query, "query_arxiv", create=True) as lookup:
            lookup.return_value = dict(literature_query.result_envelope("arXiv"), status="candidates", records=[record])
            code, out = self.run_cli(["--source", "arxiv", "--query", "Bayesian model", "--brief"])
            self.assertEqual(0, code)
            self.assertEqual(record, out["records"][0])
            lookup.return_value = dict(literature_query.result_envelope("arXiv"), status="matched", records=[record])
            code, out = self.run_cli(["--source", "arxiv", "--arxiv-id", record["arxiv_id"]])
        self.assertEqual((0, [record]), (code, out["records"]))
        self.assertEqual(2, lookup.call_count)

    def test_identifiers_from_another_database_do_not_make_requests(self):
        with patch.object(literature_query, "urlopen") as transport:
            for source, flag, value in (("crossref", "--pmid", "1234"), ("pubmed", "--doi", DOI),
                                        ("europepmc", "--arxiv-id", "1507.04544v2"), ("arxiv", "--pmid", "1234")):
                with self.subTest(source=source, flag=flag):
                    code, out = self.run_cli(["--source", source, flag, value])
                    self.assertEqual((2, "invalid_input"), (code, out["status"]))
            transport.assert_not_called()


class CrossrefTests(unittest.TestCase):
    def test_crossref_preserves_separately_deposited_subtitles_in_search_and_exact_records(self):
        work = dict(WORK, title=["Clinical outcomes"], subtitle=["A randomized clinical trial"])
        _, out, url = self.run_cli(["--query", "outcomes"], work_list(work))
        self.assertIn("subtitle", parse_qs(urlsplit(url).query)["select"][0].split(","))
        self.assertEqual("Clinical outcomes: A randomized clinical trial", out["records"][0]["title"])
        for title in ("Clinical outcomes", "Clinical outcomes: A randomized clinical trial"):
            _, out, _ = self.run_cli(["--doi", DOI], single(dict(work, title=[title])))
            self.assertEqual("Clinical outcomes: A randomized clinical trial", out["records"][0]["title"])

    def run_cli(self, args, payload=None, error=None, raw=None):
        if raw is None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        output = io.StringIO()
        with patch.object(literature_query, "urlopen", side_effect=error,
                          return_value=io.BytesIO(raw)) as transport, redirect_stdout(output):
            code = literature_query.main(args)
        self.assertEqual(transport.call_count, 1)
        self.assertGreater(transport.call_args.kwargs["timeout"], 0)
        return code, json.loads(output.getvalue()), transport.call_args.args[0].full_url

    def test_ranked_search_preserves_source_and_version(self):
        preprint = dict(WORK, DOI="10.1234/preprint", type="posted-content", relation={})
        code, out, url = self.run_cli(["--query", "记忆 & learning", "--limit", "2"],
                                      work_list(preprint, WORK))
        self.assertEqual(code, 0)
        self.assertEqual(parse_qs(urlsplit(url).query)["query.bibliographic"], ["记忆 & learning"])
        self.assertEqual(parse_qs(urlsplit(url).query)["rows"], ["2"])
        self.assertEqual(out["status"], "candidates")
        self.assertEqual(out["source"], "Crossref")
        self.assertEqual([r["doi"] for r in out["records"]], ["10.1234/preprint", DOI])
        self.assertEqual(out["records"][1]["relation"], WORK["relation"])
        self.assertEqual(out["records"][1]["year"], 2024)
        self.assertIn("Research Group", out["records"][1]["authors"])
        self.assertNotIn("abstract", out["records"][1])

    def test_exact_doi_resolves_special_characters_and_keeps_deposited_abstract(self):
        value = "10.1234/test(x);y?#"
        work = dict(WORK, DOI=value, abstract="<jats:p>Measured A, not B.</jats:p>")
        code, out, url = self.run_cli(["--doi", "https://doi.org/10.1234/TEST(x);y%3F%23"], single(work))
        self.assertEqual((code, out["status"]), (0, "matched"))
        self.assertIn("%3F%23", url)
        self.assertEqual(urlsplit(url).query, "")
        self.assertEqual(out["records"][0]["doi"], value)
        self.assertEqual(out["records"][0]["abstract"]["source"], "crossref_deposited_abstract")
        self.assertEqual(out["records"][0]["abstract"]["content"], work["abstract"])

    def test_empty_search_or_absent_doi(self):
        cases = [(["--query", "public topic"], work_list(), None),
                 (["--doi", DOI], None, HTTPError("", 404, "Not Found", {}, None))]
        for args, payload, error in cases:
            with self.subTest(args=args):
                code, out, _ = self.run_cli(args, payload, error)
                self.assertEqual((code, out["status"], out["records"]), (0, "not_found", []))

    def test_plain_doi_prefix_and_sparse_metadata(self):
        code, out, _ = self.run_cli(["--doi", "DOI: 10.1234/trial"], single({"DOI": DOI}))
        self.assertEqual((code, out["status"]), (0, "matched"))
        self.assertIsNone(out["records"][0]["year"])
        self.assertNotIn("abstract", out["records"][0])

    def test_corrupt_title_is_not_shortened_into_fake_metadata(self):
        code, out, _ = self.run_cli(["--doi", DOI], single(dict(WORK, title="Entire title")))
        self.assertNotEqual(code, 0)
        self.assertEqual(out["status"], "error")

    def test_candidate_list_bounds_long_author_lists(self):
        names = [{"name": f"Author {number}"} for number in range(100)]
        work = dict(WORK, author=names)
        _, out, _ = self.run_cli(["--query", "trial"], work_list(work))
        candidate = out["records"][0]
        self.assertEqual(candidate["author_count"], len(names))
        self.assertLess(len(candidate["authors"]), len(names))
        _, out, _ = self.run_cli(["--doi", DOI], single(work))
        self.assertEqual(len(out["records"][0]["authors"]), len(names))

    def test_on_demand_skills_link_to_query_tool(self):
        skills = Path(__file__).resolve().parents[1] / "skills"
        for relative in ("manuscript-writing/references/literature-support.md",
                         "evidence-audit/references/external-evidence.md"):
            with self.subTest(resource=relative):
                self.assertIn("scripts/literature_query.py", (skills / relative).read_text(encoding="utf-8"))

    def test_service_and_transport_failures(self):
        for error, expected in [(HTTPError("", 429, "", {"Retry-After": "60"}, None), "rate_limited"),
                                (HTTPError("", 503, "", {}, None), "error"),
                                (HTTPError("", 404, "", {}, None), "error"),
                                (URLError("offline"), "error"), (TimeoutError(), "error")]:
            with self.subTest(error=repr(error)):
                code, out, _ = self.run_cli(["--query", "learning"], error=error)
                self.assertNotEqual(code, 0)
                self.assertEqual(out["status"], expected)
                if expected == "rate_limited":
                    self.assertEqual(out["retry_after"], "60")

    def test_invalid_response_is_not_no_matches(self):
        for payload in [{"status": "ok", "message": {}}, work_list({"title": ["No DOI"]}),
                        single(dict(WORK, DOI="10.1234/other"))]:
            with self.subTest(payload=payload):
                args = ["--doi", DOI] if payload.get("message-type") == "work" else ["--query", "trial"]
                code, out, _ = self.run_cli(args, payload)
                self.assertNotEqual(code, 0)
                self.assertEqual(out["status"], "error")
        code, out, _ = self.run_cli(["--doi", DOI], raw=b"not JSON")
        self.assertNotEqual(code, 0)
        self.assertEqual(out["status"], "error")

    def test_invalid_inputs_make_no_request(self):
        with patch.object(literature_query, "urlopen") as transport:
            for args in (["--doi", "https://example.org/10.1234/abc"], ["--query", "  "],
                         ["--query", "test", "--limit", "0"]):
                with self.subTest(args=args), redirect_stdout(io.StringIO()):
                    self.assertNotEqual(literature_query.main(args), 0)
            transport.assert_not_called()


class OpenAlexTests(unittest.TestCase):
    seed = {"id": "https://openalex.org/W123", "doi": "https://doi.org/" + DOI,
            "display_name": "Seed", "publication_year": 2019, "authorships": []}
    candidate = {"id": "https://openalex.org/W456", "doi": None, "display_name": "A candidate",
                 "publication_year": 2022, "type": "article", "authorships": [
                     {"author": {"display_name": "Lin Wu"}}],
                 "primary_location": {"source": {"display_name": "Test Journal"}}}

    def run_cli(self, args, *replies):
        output = io.StringIO()
        responses = [r if isinstance(r, Exception) else io.BytesIO(json.dumps(r).encode()) for r in replies]
        with patch.object(literature_query, "urlopen", side_effect=responses) as transport, redirect_stdout(output):
            code = literature_query.main(args)
        return code, json.loads(output.getvalue()), [c.args[0].full_url for c in transport.call_args_list]

    def test_openalex_text_search_exposes_provenance_and_truncation(self):
        code, result, urls = self.run_cli(
            ["--source", "openalex", "--query", "attention & choice", "--limit", "1"],
            {"meta": {"count": 12}, "results": [self.candidate]})
        self.assertEqual(code, 0)
        self.assertEqual(len(urls), 1)
        params = parse_qs(urlsplit(urls[0]).query)
        self.assertEqual(params["search"], ["attention & choice"])
        self.assertEqual(params["per_page"], ["1"])
        self.assertNotIn("sort", params)
        self.assertEqual(result["source"], "OpenAlex")
        self.assertEqual(result["reading_status"], "not_checked")
        self.assertEqual((result["limit"], result["returned"], result["total_results"], result["truncated"]),
                         (1, 1, 12, True))
        record = result["records"][0]
        self.assertEqual((record["openalex_id"], record["doi"]), ("W456", None))
        self.assertEqual(record["authors"], ["Lin Wu"])
        self.assertEqual(record["url"], self.candidate["id"])
        self.assertEqual(record["venue"], "Test Journal")
        self.assertEqual(result["request_url"], urls[0])

    def test_seed_direction_is_explicit_and_seed_identity_is_preserved(self):
        for direction, expected in (("references", "cited_by:W123"), ("citations", "cites:W123")):
            with self.subTest(direction=direction):
                code, out, urls = self.run_cli(["--source", "openalex", "--doi", DOI,
                    "--direction", direction], self.seed, {"meta": {"count": 1}, "results": [self.candidate]})
                self.assertEqual((code, out["status"], len(urls)), (0, "candidates", 2))
                self.assertEqual(parse_qs(urlsplit(urls[1]).query)["filter"], [expected])
                self.assertEqual(parse_qs(urlsplit(urls[1]).query)["sort"], ["cited_by_count:desc"])
                self.assertEqual(out["sort"], "cited_by_count:desc")
                self.assertEqual(out["direction"], direction)
                self.assertEqual(out["seed"]["doi"], DOI)
                self.assertEqual(out["seed_request_url"], urls[0])
                self.assertEqual(out["request_url"], urls[1])
                self.assertFalse(out["truncated"])

    def test_exact_lookup_rejects_mismatched_seed(self):
        code, result, urls = self.run_cli(["--source", "openalex", "--doi", DOI], self.seed)
        self.assertEqual((code, result["status"], len(urls)), (0, "matched", 1))
        self.assertEqual(result["records"][0]["doi"], DOI)
        code, result, urls = self.run_cli(["--source", "openalex", "--doi", DOI, "--direction", "citations"],
                                           dict(self.seed, doi="10.1234/other"))
        self.assertEqual((code, result["status"], len(urls)), (2, "error", 1))

    def test_recent_seed_and_keyword_queries_filter_and_sort_the_result_set(self):
        candidate = dict(self.candidate, publication_date="2026-05-04")
        page = {"meta": {"count": 1}, "results": [candidate]}
        for mode, replies, relation in [(["--query", "facial feedback"], [page], []),
                                       (["--doi", DOI, "--direction", "citations"], [self.seed, page], ["cites:W123"])]:
            with self.subTest(mode=mode):
                code, out, urls = self.run_cli(["--source", "openalex", *mode, "--from-date", "2023-11-20",
                    "--to-date", "2026-11-20", "--sort", "newest"], *replies)
                self.assertEqual(code, 0)
                self.assertEqual(len(urls), len(replies))
                params = parse_qs(urlsplit(urls[-1]).query)
                self.assertEqual(params["filter"][0].split(","), relation + [
                    "from_publication_date:2023-11-20", "to_publication_date:2026-11-20"])
                self.assertEqual(params["sort"], ["publication_date:desc"])
                self.assertEqual(out["records"][0]["publication_date"], "2026-05-04")
                self.assertEqual((out["from_date"], out["to_date"], out["sort"]),
                                 ("2023-11-20", "2026-11-20", "publication_date:desc"))

    def test_crossref_keywords_share_date_window_without_changing_default_order(self):
        code, out, urls = self.run_cli(["--query", "facial feedback", "--from-date", "2024-02-29",
            "--to-date", "2026-10-01", "--sort", "newest", "--brief"], work_list(WORK))
        self.assertEqual((code, len(urls), out["from_date"], out["sort"]), (0, 1, "2024-02-29", "published:desc"))
        params = parse_qs(urlsplit(urls[0]).query)
        self.assertEqual(params["filter"], ["from-pub-date:2024-02-29,until-pub-date:2026-10-01"])
        self.assertEqual((params["sort"], params["order"]), (["published"], ["desc"]))

    def test_invalid_dates_and_source_specific_flags_make_no_request(self):
        for args in (["--source", "openalex", "--query", "word", "--from-date", "2023-02-29"],
                     ["--source", "openalex", "--query", "word", "--from-date", "20261103"],
                     ["--source", "openalex", "--query", "word", "--from-date", "2026-05-01", "--to-date", "2026-04-30"],
                     ["--source", "openalex", "--doi", DOI, "--sort", "newest"],
                     ["--source", "openalex", "--query", "word", "--section", "Methods"],
                     ["--source", "crossref", "--pmcid", "PMC1234", "--section", "Methods"],
                     ["--source", "europepmc", "--doi", DOI, "--direction", "citations"]):
            with self.subTest(args=args):
                code, out, urls = self.run_cli(args)
                self.assertEqual((code, out["status"], urls), (2, "invalid_input", []))

    def test_brief_keeps_candidate_identity_query_scope_and_full_record_separate(self):
        page = {"meta": {"count": 12}, "results": [self.candidate]}
        args = ["--source", "openalex", "--doi", DOI, "--direction", "citations", "--from-date", "2020-01-01"]
        code, out, urls = self.run_cli(args + ["--brief"], self.seed, page)
        self.assertEqual((code, len(urls), out["source"], out["reading_status"]), (0, 2, "OpenAlex", "not_checked"))
        self.assertTrue(out["preview_only"])
        self.assertEqual(out["seed"]["doi"], DOI)
        self.assertEqual((out["direction"], out["sort"], out["from_date"]), ("citations", "cited_by_count:desc", "2020-01-01"))
        self.assertEqual((out["total_results"], out["returned"], out["truncated"]), (12, 1, True))
        self.assertEqual(out["records"][0]["openalex_id"], "W456")
        self.assertEqual(out["records"][0]["first_author"], "Lin Wu")
        self.assertNotIn("indexed_location_version", out["records"][0])
        code, out, _ = self.run_cli(["--doi", DOI, "--brief"], single(dict(WORK, abstract="Actual abstract")))
        self.assertNotIn("preview_only", out)
        self.assertEqual(out["records"][0]["abstract"]["content"], "Actual abstract")
        _, out, _ = self.run_cli(["--query", "word", "--brief"], work_list(dict(WORK, author=[{"name":"X"}])))
        self.assertEqual(out["records"][0]["doi"], DOI)
        self.assertEqual(out["records"][0]["first_author"], "X")
        self.assertNotIn("relation", out["records"][0])

    def test_empty_links_differ_from_missing_seed_and_blocked_service(self):
        args = ["--source", "openalex", "--doi", DOI, "--direction", "citations"]
        code, result, _ = self.run_cli(args, self.seed, {"meta": {"count": 0}, "results": []})
        self.assertEqual((code, result["status"], result["total_results"]), (0, "not_found", 0))
        self.assertEqual(result["seed"]["openalex_id"], "W123")
        code, result, _ = self.run_cli(args, HTTPError("", 404, "", {}, None))
        self.assertEqual((code, result["status"]), (0, "seed_not_found"))
        for status, expected in [(403, "access_denied"), (429, "rate_limited"), (503, "error"), (404, "error")]:
            with self.subTest(status=status):
                code, result, _ = self.run_cli(args, self.seed, HTTPError("", status, "", {"Retry-After": "30"}, None))
                self.assertEqual((code, result["status"]), (2, expected))
                if status == 429:
                    self.assertEqual(result["retry_after"], "30")

    def test_invalid_modes_never_send_requests(self):
        for args in (["--doi", DOI, "--direction", "references"],
                     ["--source", "openalex", "--query", "test", "--direction", "citations"],
                     ["--source", "openalex", "--doi", DOI, "--limit", "1"],
                     ["--source", "openalex", "--query", " ", "--limit", "1"],
                     ["--source", "openalex", "--query", "test", "--limit", "21"]):
            with self.subTest(args=args):
                code, result, urls = self.run_cli(args)
                self.assertEqual((code, result["status"], urls), (2, "invalid_input", []))

    def test_corrupt_data_is_not_mistaken_for_an_empty_result(self):
        for payload in ({}, {"meta": {"count": 1}, "results": []},
                        {"meta": {"count": 1}, "results": [dict(self.candidate, id="bad")]}):
            with self.subTest(payload=payload):
                code, result, _ = self.run_cli(["--source", "openalex", "--query", "test"], payload)
                self.assertEqual((code, result["status"]), (2, "error"))


class ArxivTests(unittest.TestCase):
    entry = """<entry><id>http://arxiv.org/abs/1507.04544v1</id><title>Model evaluation</title>
      <published>2015-07-16T03:12:00Z</published><updated>2015-07-16T03:12:00Z</updated>
      <summary>The submitted abstract.</summary><author><name>A. Example</name></author>
      <category term="stat.CO"/><arxiv:doi>10.1234/journal</arxiv:doi></entry>"""

    def ask(self, entries="", total=0, **options):
        raw = (f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" '
               f'xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">'
               f'<opensearch:totalResults>{total}</opensearch:totalResults>{entries}</feed>').encode()
        with patch.object(literature_query, "urlopen", return_value=io.BytesIO(raw)) as transport:
            out = literature_query.query_arxiv(**options)
        parameters = parse_qs(urlsplit(transport.call_args.args[0].full_url).query) if transport.called else {}
        self.assertLessEqual(transport.call_count, 1)
        return out, parameters

    def test_search_shortlist_and_submitted_date_scope(self):
        out, params = self.ask(self.entry, 12, query="cat:stat.CO AND ti:Bayesian",
                               from_date="2015-01-01", to_date="2015-12-31", sort="newest")
        self.assertEqual(("candidates", 1, 12, True), (out["status"], out["returned"], out["total_results"], out["truncated"]))
        self.assertEqual(params["sortBy"], ["submittedDate"])
        self.assertIn("submittedDate:[201501010000 TO 201512312359]", params["search_query"][0])
        self.assertIn("cat:stat.CO AND ti:Bayesian", params["search_query"][0])
        self.assertEqual(params["max_results"], ["5"])
        self.assertNotIn("abstract", out["records"][0])
        self.assertEqual(out["records"][0]["arxiv_id"], "1507.04544v1")
        _, params = self.ask(query="Bayesian model comparison")
        terms = params["search_query"][0]
        self.assertTrue(all(term in terms for term in ["Bayesian", "model", "comparison"]))

    def test_exact_version_retains_identity_and_separates_published_doi(self):
        out, params = self.ask(self.entry, 1, arxiv_id="arXiv:1507.04544v1")
        self.assertEqual(params["id_list"], ["1507.04544v1"])
        self.assertEqual(out["status"], "matched")
        record = out["records"][0]
        self.assertEqual((record["arxiv_id"], record["version"], record["journal_doi"]),
                         ("1507.04544v1", "v1", "10.1234/journal"))
        self.assertEqual(record["relation"], {"is-preprint-of": [{"id-type": "doi", "id": "10.1234/journal"}]})
        self.assertEqual(record["url"], "https://arxiv.org/abs/1507.04544v1")
        self.assertIsNone(record.get("doi"))
        self.assertIn("The submitted abstract.", record["abstract"]["content"])
        out, _ = self.ask(self.entry, 1, arxiv_id="1507.04544v2")
        self.assertEqual((out["status"], out["records"]), ("error", []))
        old, params = self.ask(self.entry.replace("1507.04544v1", "math.GT/0309136v2"), 1,
                               arxiv_id="https://arxiv.org/abs/math.GT/0309136")
        self.assertEqual((old["status"], old["records"][0]["version"], params["id_list"]),
                         ("matched", "v2", ["math.GT/0309136"]))

    def test_no_hits_error_entry_and_malformed_feed_are_distinct(self):
        self.assertEqual(self.ask(query="sparse topic")[0]["status"], "not_found")
        self.assertEqual(self.ask(self.entry, 0, query="topic")[0]["status"], "error")
        service_error = '<entry><title>Error</title><id>http://arxiv.org/api/errors#x</id><summary>Bad input</summary></entry>'
        out, _ = self.ask(service_error, 1, query="topic")
        self.assertEqual((out["status"], out["records"]), ("error", []))
        self.assertIn("Bad input", out["detail"])
        with patch.object(literature_query, "urlopen", side_effect=HTTPError("", 429, "Busy", {"Retry-After": "30"}, None)):
            self.assertEqual(literature_query.query_arxiv(query="topic")["status"], "rate_limited")

    def test_invalid_inputs_make_no_network_request(self):
        for options in ({"arxiv_id": "https://example.org/abs/1507.04544"}, {"arxiv_id": "1507.04544v0"},
                        {"arxiv_id": "hep-th/9901001", "from_date": "2000-01-01"},
                        {"query": "Bayesian", "limit": 21}, {"query": "topic", "to_date": "2026-13-01"}):
            with self.subTest(options=options):
                out, params = self.ask(**options)
                self.assertEqual((out["status"], params), ("invalid_input", {}))


class EuropePMCTests(unittest.TestCase):
    lite = {"id": "122", "source": "MED", "title": "Translation study", "pubYear": "2016",
            "pmcid": "PMC123", "pmid": "122", "doi": DOI, "authorString": "Li W, Chen M.",
            "firstPublicationDate": "2016-05-23", "inEPMC": "Y"}
    xml = b"""<article><front><article-meta><article-id pub-id-type="pmc">123</article-id>
        <abstract><p>The adapted scale</p></abstract></article-meta></front>
        <body><sec id="s1"><title>Methods</title><sec id="s2"><title>Measures</title>
        <p id="p1">We used the <italic>adapted</italic> scale [3].</p>
        <p>Participants also read instructions.</p></sec></sec>
        <sec><title>Discussion</title><p>The adapted scale had limitations.</p></sec></body></article>"""

    def lookup(self, result, **kwargs):
        with patch.object(literature_query, "urlopen", return_value=io.BytesIO(json.dumps(result).encode())) as op:
            out = literature_query.query_europepmc(**kwargs)
        return out, parse_qs(urlsplit(op.call_args.args[0].full_url).query)

    def test_lite_keyword_dates_sort_and_provenance(self):
        out, params = self.lookup({"hitCount": 47, "resultList": {"result": [self.lite]}}, query="stress AND sleep",
                                   from_date="2016-04-01", to_date="2017-05-20", sort="newest", limit=1)
        self.assertEqual(("Europe PMC", "candidates", 1, True, "not_checked"),
                         (out["source"],out["status"],out["returned"],out["truncated"],out["reading_status"]))
        self.assertIn("FIRST_PDATE:[2016-04-01 TO 2017-05-20]", params["query"][0])
        self.assertEqual(["lite"], params["resultType"])
        self.assertIn("FIRST_PDATE_D desc", params["sort"])
        self.assertEqual(("PMC123", "MED:122"), (out["records"][0]["pmcid"],out["records"][0]["source_id"]))
        self.assertNotIn("abstract", out["records"][0])

    def test_exact_doi_requires_same_identifier_and_keeps_distinct_records(self):
        wrong = dict(self.lite, doi="10.1234/other")
        out, _ = self.lookup({"hitCount": 1, "resultList": {"result":[wrong]}}, doi=DOI)
        self.assertEqual("error", out["status"])
        second = dict(self.lite, id="222", source="PPR", pmcid=None)
        out, _ = self.lookup({"hitCount": 2, "resultList": {"result":[self.lite,second]}}, doi=DOI)
        self.assertEqual(["MED:122","PPR:222"], [r["source_id"] for r in out["records"]])
        empty, _ = self.lookup({"hitCount": 0, "resultList": {"result":[]}}, doi=DOI)
        self.assertEqual("not_found", empty["status"])

    def test_search_preview_reports_only_requested_dates_and_sort(self):
        payload = {"hitCount": 1, "resultList": {"result": [self.lite]}}
        for flags, scope in [
            ([], {}),
            (["--from-date", "2016-04-01", "--to-date", "2017-05-20", "--sort", "newest"],
             {"from_date": "2016-04-01", "to_date": "2017-05-20", "sort": "FIRST_PDATE_D desc"}),
        ]:
            output = io.StringIO()
            with self.subTest(flags=flags), patch.object(literature_query, "fetch_json", return_value=payload), redirect_stdout(output):
                self.assertEqual(0, literature_query.main(["--source", "europepmc", "--query", "stress", "--brief", *flags]))
                preview = json.loads(output.getvalue())
                self.assertTrue(preview["preview_only"])
                self.assertEqual(scope, {k: preview[k] for k in ("from_date", "to_date", "sort") if k in preview})

    def passages(self, xml, **kwargs):
        with patch.object(literature_query, "urlopen", return_value=io.BytesIO(xml)) as transport:
            out = literature_query.query_europepmc(pmcid="PMC123", **kwargs)
        self.assertEqual(1, transport.call_count)
        return out

    def test_methods_only_selected_original_words_and_locator(self):
        out = self.passages(self.xml, section="methods", passage_query="adapted scale")
        self.assertEqual(("passages",1), (out["status"],len(out["passages"])))
        mark = out["passages"][0]
        self.assertEqual(("We used the adapted scale [3].",["Methods","Measures"],"p1"),
                         (mark["text"],mark["section_path"],mark["paragraph_id"]))
        self.assertEqual("PMC123",out["pmcid"])
        self.assertNotIn("abstract",json.dumps(out).lower())
        self.assertEqual("no_passage",self.passages(self.xml,section="Results")["status"])

    def test_clipping_around_a_late_match_and_bounded_paragraph_count(self):
        extended = self.xml.replace(b'We used the ', b'previous text ' * 180 + b'We used the ')
        match = self.passages(extended, passage_query="adapted scale", limit=1)
        self.assertTrue(match["truncated"])
        self.assertLessEqual(len(match["passages"][0]["text"]),720)
        self.assertIn("adapted scale",match["passages"][0]["text"])
        self.assertTrue(match["passages"][0]["text_truncated"])
        start = match["passages"][0]["text_start"]
        text = "previous text " * 180 + "We used the adapted scale [3]."
        self.assertTrue(text[start - 1].isspace())

    def test_protocol_and_coverage_failures_remain_distinct(self):
        for xml, status in [(self.xml.replace(b'>123<',b'>124<'), "error"),
                            (b'<html><body>Proxy</body></html>',"error"),
                            (b'<article><front/></article>',"fulltext_unavailable"),
                            (b'broken XML',"error")]:
            with self.subTest(status=status): self.assertEqual(status, self.passages(xml,section="methods")["status"])
        for code, status in [(404,"fulltext_unavailable"),(403,"access_denied"),(429,"rate_limited")]:
            with patch.object(literature_query,"urlopen",side_effect=HTTPError("",code,"",{},None)):
                out = literature_query.query_europepmc(pmcid="PMC123",section="methods")
            self.assertEqual(status,out["status"])
        with patch.object(literature_query,"urlopen") as transport:
            for args in ({"pmcid":"PMC123"},{"pmcid":"123/../path","section":"methods"},
                         {"pmcid":"PMC123","section":"measures","limit":10},{"doi":DOI,"sort":"newest"},
                         {"query":"text","from_date":"not a date"}):
                self.assertEqual("invalid_input",literature_query.query_europepmc(**args)["status"])
            transport.assert_not_called()


class PubMedTests(unittest.TestCase):
    def article(self, pmid, **fields):
        return {"uid": pmid, "title": "Psychology article", "pubdate": "2024 Sep",
                "fulljournalname": "Test Journal", "authors": [{"name": "Mann A"}],
                "pubtype": ["Journal Article", "Randomized Controlled Trial"], **fields}

    def query(self, *responses, **kwargs):
        with patch.object(literature_query, "fetch_json", side_effect=responses) as get:
            result = literature_query.query_pubmed(**kwargs)
        return result, [call.args[0] for call in get.call_args_list]

    def test_fielded_search_batches_ids_in_rank_order_and_keeps_dates(self):
        terms = '"Depression"[mh] AND "Randomized Controlled Trial"[pt]'
        search = {"esearchresult": {"idlist": ["84", "31"], "count": "7"}}
        summaries = {"result": {"uids": ["31", "84"], "84": self.article("84"),
                                "31": self.article("31", articleids=[{"idtype": "doi", "value": DOI}])}}
        out, urls = self.query(search, summaries, query=terms, limit=2,
                               from_date="2022-01-01", to_date="2025-10-31", sort="newest")
        self.assertEqual([r["pmid"] for r in out["records"]], ["84", "31"])
        self.assertEqual(out["records"][0]["publication_types"][-1], "Randomized Controlled Trial")
        self.assertIsNone(out["records"][0]["doi"])
        self.assertEqual(out["records"][1]["doi"], DOI)
        self.assertEqual(out["records"][0]["authors"], ["Mann A"])
        self.assertEqual(out["records"][0]["year"], 2024)
        self.assertNotIn("abstract", out["records"][0])
        self.assertEqual((out["source"], out["status"], out["total_results"], out["truncated"]),
                         ("PubMed", "candidates", 7, True))
        search_params = parse_qs(urlsplit(urls[0]).query)
        self.assertEqual(search_params["term"], [terms])
        self.assertEqual(search_params["datetype"], ["pdat"])
        self.assertEqual(search_params["mindate"], ["2022/01/01"])
        self.assertEqual(search_params["maxdate"], ["2025/10/31"])
        self.assertEqual(search_params["sort"], ["pub_date"])
        self.assertEqual(out["sort"], "pub_date")
        self.assertEqual(out["to_date"], "2025-10-31")
        self.assertEqual(parse_qs(urlsplit(urls[1]).query)["id"], ["84,31"])
        self.assertEqual(len(urls), 2)
        self.assertIn("esearch.fcgi", out["request_url"])

    def test_pmid_exact_must_match_and_only_queries_once(self):
        doc = self.article("42", articleids=[{"idtype": "pmc", "value": "PMC150"}])
        out, urls = self.query({"result": {"uids": ["42"], "42": doc}}, pmid="42")
        self.assertEqual((out["status"], out["records"][0]["pmcid"]), ("matched", "PMC150"))
        self.assertEqual((len(urls), out["records"][0]["url"]), (1, "https://pubmed.ncbi.nlm.nih.gov/42/"))
        bad, _ = self.query({"result": {"uids": ["42"], "42": self.article("43")}}, pmid="42")
        self.assertEqual(bad["status"], "error")
        for kwargs in ({"pmid": "42,3"}, {"pmid": "0"}, {"query": "x", "limit": 21},
                       {"pmid": "42", "sort": "newest"}, {"query": "x", "from_date": "2025-02-30"}):
            with self.subTest(kwargs=kwargs):
                invalid, urls = self.query(**kwargs)
                self.assertEqual((invalid["status"], len(urls)), ("invalid_input", 0))

    def test_empty_search_invalid_field_and_service_failure_are_distinct(self):
        empty, urls = self.query({"esearchresult": {"count": "0", "idlist": [],
                                  "warninglist": {"outputmessages": ["No items found."]}}}, query="xyz")
        self.assertEqual((empty["status"], len(urls)), ("not_found", 1))
        result, _ = self.query({"esearchresult": {"count": "2", "idlist": ["42", "43"],
                               "errorlist": {"fieldsnotfound": ["unknownfield"]}}}, query="x[unknownfield]")
        self.assertEqual(result["status"], "invalid_input")
        for payload in ({"error": "Temporary service error"},
                        {"esearchresult": {"count": "10", "idlist": []}},
                        {"esearchresult": {"count": "2", "idlist": ["47", "47"]}}):
            bad, urls = self.query(payload, query="test")
            self.assertEqual((bad["status"], len(urls)), ("error", 1))
        warning, _ = self.query({"esearchresult": {"count": "1", "idlist": ["1"],
                                 "warninglist": {"phrasesignored": ["X Y"]}}},
                                {"result": {"uids": ["1"], "1": self.article("1")}}, query="X Y")
        self.assertIn("X Y", str(warning["warnings"]))
        limited, _ = self.query(HTTPError("", 429, "", {"Retry-After": "30"}, None), query="test")
        self.assertEqual((limited["status"], limited["retry_after"]), ("rate_limited", "30"))

    def test_summary_gaps_are_reported_without_discarding_other_matches(self):
        search = {"esearchresult": {"idlist": ["1", "2"], "count": "2"}}
        partial, _ = self.query(search, {"result": {"uids": ["1"], "1": self.article("1")}}, query="stress")
        self.assertEqual((partial["status"], partial["missing_pmids"], partial["returned"]), ("partial", ["2"], 1))
        extra, _ = self.query(search, {"result": {"uids": ["3"], "3": self.article("3")}}, query="stress")
        self.assertEqual(extra["status"], "error")


if __name__ == "__main__":
    unittest.main()
