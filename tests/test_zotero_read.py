"""Read a paper's own annotations without touching a Zotero library."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import zotero_read


PAPER, FIRST, SECOND = "PPPP2222", "AAAA2222", "BBBB2222"
MARK, MARK2, COLL = "QQQQ2222", "RRRR2222", "CCCC2222"


def item(key, kind, **fields):
    return {"key": key, "data": {"key": key, "itemType": kind, **fields}}


def invoke(*argv):
    output = io.StringIO()
    with redirect_stdout(output):
        code = zotero_read.main(list(argv))
    return code, json.loads(output.getvalue())


class ZoteroReadTests(unittest.TestCase):
    def setUp(self):
        self.pages = {
            f"items/{PAPER}": item(PAPER, "journalArticle", title="Same Paper"),
            f"items/{PAPER}/children": [
                item(FIRST, "attachment", parentItem=PAPER, contentType="application/pdf", title="Preprint"),
                item(SECOND, "attachment", parentItem=PAPER, contentType="application/pdf", title="Published PDF"),
            ],
            f"items/{FIRST}/children": [item(MARK2, "annotation", annotationType="highlight",
                parentItem=FIRST, annotationText="Other edition", annotationPageLabel="iv")],
            f"items/{SECOND}/children": [item(MARK, "annotation", annotationType="highlight",
                parentItem=SECOND, annotationText="The  exact quotation.", annotationComment="记得的笔记",
                annotationPageLabel="iv", annotationPosition=json.dumps({"pageIndex": 5}))],
        }

    def request(self, path, params=None):
        rows = self.pages[path]
        if isinstance(rows, dict):
            return rows, None
        start, limit = params["start"], params["limit"]
        return rows[start:start + limit], len(rows)

    def test_real_attachment_pagination_comment_and_physical_page(self):
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request), \
                patch.object(zotero_read, "PAGE_SIZE", 1):
            code, result = invoke("highlights", "--paper", PAPER, "--query", "记得的笔记")
        self.assertEqual((code, result["status"]), (0, "ok"))
        record, = result["records"]
        self.assertEqual(record["quote"], "The  exact quotation.")
        self.assertEqual(record["comment"], "记得的笔记")
        self.assertEqual(record["attachment_key"], SECOND)
        self.assertEqual((record["page_label"], record["page_number"]), ("iv", 6))
        self.assertEqual(record["open_url"], f"zotero://open-pdf/library/items/{SECOND}?page=6&annotation={MARK}")

    def test_unknown_physical_page_does_not_convert_printed_page(self):
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request):
            _, result = invoke("highlights", "--paper", PAPER, "--query", "Other edition")
        record, = result["records"]
        self.assertEqual(record["page_label"], "iv")
        self.assertIsNone(record["page_number"])
        self.assertIsNone(record["open_url"])

    def test_search_is_scoped_and_paged(self):
        self.pages[f"collections/{COLL}/items/top"] = [item(PAPER, "book", title="Test book")]
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request) as get:
            code, result = invoke("papers", "--collection", COLL, "--query", "test & book")
        self.assertEqual(code, 0)
        self.assertEqual(result["records"][0]["key"], PAPER)
        self.assertEqual(get.call_args.args[1]["q"], "test & book")
        self.pages["collections"] = [{"key": COLL, "data": {"key": COLL, "name": "My collection"}}]
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request):
            _, result = invoke("collections")
        self.assertEqual(result["records"][0]["name"], "My collection")

    def test_group_pdf_standalone_empty_and_paged_matches(self):
        self.pages[f"items/{SECOND}"] = self.pages[f"items/{PAPER}/children"][1]
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request):
            _, group = invoke("highlights", "--group", "24", "--paper", SECOND)
            _, page = invoke("highlights", "--paper", PAPER, "--limit", "1")
            _, second = invoke("highlights", "--paper", PAPER, "--start", str(page["next_start"]))
            code, empty = invoke("highlights", "--paper", PAPER, "--query", "absent")
        self.assertIn("groups/24/items/", group["records"][0]["open_url"])
        self.assertEqual(second["records"][0]["annotation_key"], MARK)
        self.assertEqual((code, empty["status"], empty["records"]), (0, "not_found", []))

    def test_wrong_parent_cannot_substitute_for_target_annotation(self):
        self.pages[f"items/{SECOND}/children"][0]["data"]["parentItem"] = FIRST
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request):
            _, result = invoke("highlights", "--paper", PAPER, "--query", "exact quotation")
        self.assertFalse(result["records"])

    def test_loopback_get_only_status_distinguishes_permission_and_service_failure(self):
        for http_status, expected in [(403, "disabled"), (404, "missing_item"), (302, "error"), (500, "error")]:
            response = Mock(status=http_status)
            with patch.object(zotero_read, "HTTPConnection") as connect:
                conn = connect.return_value
                conn.getresponse.return_value = response
                code, result = invoke("papers", "--group", "24", "--query", "secret & text")
                self.assertEqual(connect.call_args.args, ("127.0.0.1", 23119))
                method, path = conn.request.call_args.args
                self.assertEqual(method, "GET")
                self.assertEqual(urlsplit(path).path, "/api/groups/24/items/top")
                self.assertEqual(parse_qs(urlsplit(path).query)["q"], ["secret & text"])
                self.assertEqual(conn.request.call_count, 1)
            self.assertNotEqual(code, 0)
            self.assertEqual(result["status"], expected)
        with patch.object(zotero_read, "HTTPConnection", side_effect=ConnectionRefusedError):
            code, out = invoke("collections")
        self.assertNotEqual(code, 0)
        self.assertEqual(out["status"], "unavailable")

    def test_invalid_keys_do_not_open_service(self):
        with patch.object(zotero_read, "HTTPConnection") as connect:
            code, out = invoke("highlights", "--paper", "../abcde")
            self.assertNotEqual(code, 0)
            self.assertEqual(out["status"], "invalid_input")
            connect.assert_not_called()

    def test_protocol_errors_are_not_missing_records_or_user_input_errors(self):
        cases = [("papers", None, {"unexpected": []}), ("highlights", PAPER, item(SECOND, "book"))]
        for command, paper_key, payload in cases:
            with self.subTest(command=command), patch.object(zotero_read.LocalLibrary, "get", return_value=(payload, None)):
                argv = [command, "--paper", paper_key] if paper_key else [command]
                code, result = invoke(*argv)
                self.assertNotEqual(code, 0)
                self.assertEqual(result["status"], "error")

    def test_nontext_pdf_marks_keep_comments_regions_and_locator_without_inventing_a_quote(self):
        self.pages[f"items/{SECOND}/children"] = [
            item(MARK, "annotation", parentItem=SECOND, annotationType="image", annotationComment="图上圈的区域",
                 annotationPosition={"pageIndex": 1, "rects": [[15, 20, 60, 80]]}),
            item(MARK2, "annotation", parentItem=SECOND, annotationType="note",
                 annotationComment="页边笔记", annotationPosition={"pageIndex": 2}),
            item("TTTT2222", "annotation", parentItem=SECOND, annotationType="ink",
                 annotationPosition={"pageIndex": 4, "paths": [[4, 3, 9, 2, 7, 5]]}),
            item("UUUU2222", "annotation", parentItem=FIRST, annotationType="note", annotationComment="wrong attachment"),
        ]
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request):
            code, image = invoke("highlights", "--paper", PAPER, "--query", "圈的区域")
            _, note = invoke("highlights", "--paper", PAPER, "--query", "页边")
            _, all_marks = invoke("highlights", "--paper", PAPER)
        self.assertEqual(code, 0)
        region, = image["records"]
        self.assertEqual((region["type"], region["quote"], region["comment"]), ("image", "", "图上圈的区域"))
        self.assertEqual(region["bounds"], [15, 20, 60, 80])
        self.assertIn(f"{SECOND}?page=2&annotation={MARK}", region["open_url"])
        self.assertEqual(note["records"][0]["quote"], "")
        self.assertIsNone(note["records"][0]["bounds"])
        self.assertNotIn("wrong attachment", [r["comment"] for r in all_marks["records"]])
        self.assertEqual(all_marks["records"][-1]["bounds"], [4, 2, 9, 5])

    def test_collection_fragment_search_is_bounded_and_returns_paper_for_comment(self):
        path = f"collections/{COLL}/items/top"
        self.pages[path] = [item("SSSS2222", "book", title="Unannotated"), self.pages[f"items/{PAPER}"]]
        self.pages["items/SSSS2222/children"] = []
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request) as get:
            code, first = invoke("highlights", "--collection", COLL, "--query", "笔记", "--paper-limit", "1")
            self.assertEqual(code, 0)
            self.assertEqual(first["next_paper_start"], 1)
            self.assertEqual(first["scope"]["papers_in_batch"], 1)
            self.assertFalse(any(PAPER in c.args[0] for c in get.call_args_list))
            _, second = invoke("highlights", "--collection", COLL, "--query", "笔记", "--paper-start", "1")
            _, invalid = invoke("highlights", "--collection", COLL)
        self.assertEqual(second["records"][0]["paper_title"], "Same Paper")
        self.assertEqual(second["records"][0]["paper_key"], PAPER)
        self.assertIsNone(second["next_paper_start"])
        self.assertEqual(invalid["status"], "invalid_input")

    def test_doi_query_finds_only_exact_record_even_on_later_page(self):
        self.pages["items/top"] = [item(FIRST, "book", DOI="10.1234/other"),
                                   item(PAPER, "book", DOI="https://doi.org/10.1234/Main")]
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request) as get, \
                patch.object(zotero_read, "PAGE_SIZE", 1):
            code, result = invoke("papers", "--query", "https://doi.org/10.1234/MAIN")
            _, explicit = invoke("papers", "--doi", "10.1234/Main")
        self.assertEqual(code, 0)
        self.assertEqual([r["key"] for r in result["records"]], [PAPER])
        self.assertEqual(explicit["records"], result["records"])
        self.assertTrue(all(c.args[1]["qmode"] == "everything" for c in get.call_args_list))

    def test_local_top_may_include_child_pdf_alongside_parent_and_standalone_pdf(self):
        # Zotero 10's local /items/top search returned both rows for the same paper.
        child = item(FIRST, "attachment", parentItem=PAPER, contentType="application/pdf", title="PDF")
        parent = item(PAPER, "journalArticle", title="Paper")
        standalone = item("FREE2222", "attachment", contentType="application/pdf", title="Separate PDF")
        for path in ("items/top", f"collections/{COLL}/items/top"):
            self.pages[path] = [child, parent, standalone]
        self.pages[f"items/{PAPER}/children"] = [child]
        self.pages[f"items/{FIRST}/children"] = [item(MARK, "annotation", annotationType="highlight",
                parentItem=FIRST, annotationText="Match here")]
        self.pages["items/FREE2222/children"] = []
        with patch.object(zotero_read.LocalLibrary, "get", side_effect=self.request):
            for selection in ([], ["--collection", COLL]):
                _, result = invoke("papers", "--query", "Paper", *selection)
                self.assertEqual([r["key"] for r in result["records"]], [PAPER, "FREE2222"])
                _, first = invoke("papers", *selection, "--limit", "1")
                self.assertEqual((first["status"], first["records"], first["next_start"]), ("ok", [], 1))
            _, marks = invoke("highlights", "--collection", COLL, "--query", "match")
            self.assertEqual([r["annotation_key"] for r in marks["records"]], [MARK])
            self.assertEqual(marks["scope"]["papers_in_batch"], 2)
            _, batch = invoke("highlights", "--collection", COLL, "--query", "match", "--paper-limit", "1")
            self.assertEqual((batch["scope"]["papers_in_batch"], batch["next_paper_start"]), (0, 1))

    def test_desktop_exposes_annotations_only_on_typed_attachment_children(self):
        def desktop(path, params=None):
            if path == f"items/{SECOND}/children" and params.get("itemType") != "annotation":
                return [], 0
            return self.request(path, params)

        with patch.object(zotero_read.LocalLibrary, "get", side_effect=desktop) as get:
            _, out = invoke("highlights", "--paper", PAPER, "--query", "记得的笔记")
        self.assertEqual([r["annotation_key"] for r in out["records"]], [MARK])
        self.assertFalse(any(c.args[0] == "items" for c in get.call_args_list))
