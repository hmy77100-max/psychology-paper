"""Find saved papers and their PDF highlights in Zotero Desktop (read-only, no API key)."""
import argparse
import json
import re
from http.client import HTTPConnection, HTTPException
from itertools import islice
from urllib.parse import urlencode

from literature_query import normalize_doi


PAGE_SIZE = 50


class LocalError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def check_key(key, *, user_input=False):
    if not isinstance(key, str) or not re.fullmatch(r"[A-Z0-9]{8}", key):
        raise LocalError("invalid_input" if user_input else "error", "Expected an eight-character Zotero item or collection key.")
    return key


class LocalLibrary:
    def __init__(self, group):
        if group is not None and group < 1:
            raise LocalError("invalid_input", "A group ID must be a positive integer.")
        self.path = f"/api/groups/{group}" if group else "/api/users/0"
        self.link_scope = f"groups/{group}" if group else "library"

    def get(self, path, params=None):
        address = f"{self.path}/{path}"
        if params:
            address += "?" + urlencode(params)
        # Direct connection: system proxy settings and HTTP redirects cannot route private queries elsewhere.
        conn = HTTPConnection("127.0.0.1", 23119, timeout=8)
        try:
            conn.request("GET", address, headers={"Zotero-API-Version": "3", "Accept": "application/json"})
            reply = conn.getresponse()
            if reply.status == 403:
                raise LocalError("disabled", "Enable local communication in Zotero Settings > Advanced.")
            if reply.status == 404:
                raise LocalError("missing_item", "This resource was not found in the selected local library.")
            if reply.status != 200:
                raise LocalError("error", f"Zotero returned HTTP {reply.status}.")
            total = reply.getheader("Total-Results")
            return json.loads(reply.read()), int(total) if total is not None else None
        finally:
            conn.close()

    def page(self, path, params, start, limit):
        rows, total = self.get(path, {**params, "limit": limit, "start": start})
        if not isinstance(rows, list):
            raise ValueError("Expected a Zotero result list.")
        end = start + len(rows)
        more = end < total if total is not None else len(rows) == limit
        if more and not rows:
            raise ValueError("Zotero returned an empty page before its reported result total.")
        return rows, end if more else None

    def items(self, path, params):
        start = 0
        while start is not None:
            rows, start = self.page(path, params, start, PAGE_SIZE)
            yield from rows

    def children(self, key, item_type=None):
        params = {"itemType": item_type} if item_type else {}
        for row in self.items(f"items/{key}/children", params):
            if row["data"].get("parentItem") == key:
                yield row["data"]


def paper_record(row):
    data = row["data"]
    authors = [c.get("name") or " ".join(filter(None, (c.get("firstName"), c.get("lastName"))))
               for c in data.get("creators", [])]
    return {"key": row["key"], "type": data["itemType"], "title": data.get("title", ""),
            "authors": authors, "date": data.get("date", ""), "doi": data.get("DOI", "")}


def is_pdf(data):
    return data.get("itemType") == "attachment" and data.get("contentType") == "application/pdf"


def top_paper(row):
    # The Desktop API can include a child PDF alongside its parent in /items/top.
    data = row["data"]
    return not data.get("parentItem") and data["itemType"] not in ("note", "annotation") and (
        data["itemType"] != "attachment" or is_pdf(data))


def region_bounds(position):
    # A region or freehand mark can be located without reproducing its full drawing.
    boxes = []
    for line in position.get("rects", []) + position.get("paths", []):
        if not isinstance(line, list) or len(line) < 2 or len(line) % 2:
            continue
        if all(type(n) in (int, float) for n in line):
            xs, ys = line[::2], line[1::2]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
    if boxes:
        return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return None


def annotation_record(library, paper_key, attachment, annotation):
    position = annotation.get("annotationPosition") or {}
    if isinstance(position, str):
        try:
            position = json.loads(position)
        except ValueError:
            position = {}
    if not isinstance(position, dict):
        position = {}
    index = position.get("pageIndex")
    number = index + 1 if type(index) is int and index >= 0 else None
    file_key = check_key(attachment["key"])
    mark_key = check_key(annotation["key"])
    reader = f"zotero://open-pdf/{library.link_scope}/items/{file_key}"
    return {"paper_key": paper_key, "attachment_key": file_key, "attachment_title": attachment.get("title"),
            "annotation_key": mark_key, "type": annotation["annotationType"],
            "quote": annotation.get("annotationText") or "", "comment": annotation.get("annotationComment") or "",
            "page_label": annotation.get("annotationPageLabel") or None, "page_number": number, "bounds": region_bounds(position),
            "open_url": f"{reader}?page={number}&annotation={mark_key}" if number else None}


def highlight_records(library, item, query):
    data = item["data"]
    key = check_key(data["key"])
    attachments = [data] if is_pdf(data) else (row for row in library.children(key) if is_pdf(row))
    paper_key = data.get("parentItem") or key
    needle = " ".join(query.casefold().split())
    for attachment in attachments:
        for annotation in library.children(check_key(attachment["key"]), "annotation"):
            if annotation.get("itemType") != "annotation":
                continue
            record = annotation_record(library, paper_key, attachment, annotation)
            record["paper_title"] = data.get("title") if paper_key == key else None
            if any(needle in " ".join(record[name].casefold().split()) for name in ("quote", "comment")):
                yield record


def page_matches(records, start, limit):
    sample = list(islice(records, start, start + limit + 1))
    return sample[:limit], start + limit if len(sample) > limit else None


def as_doi(text):
    try:
        return normalize_doi(text).casefold() if text else None
    except ValueError:
        return None


def highlight_page(library, args):
    scope = {}
    if args.paper:
        key = check_key(args.paper, user_input=True)
        item, _ = library.get(f"items/{key}")
        if item["data"]["key"] != key:
            raise ValueError("Zotero returned a different item.")
        papers = [item]
    else:
        key = check_key(args.collection, user_input=True)
        if not args.query.strip() or args.paper_start < 0 or not 1 <= args.paper_limit <= 20:
            raise LocalError("invalid_input", "Collection annotation search needs a phrase, 1–20 papers and a nonnegative paper start.")
        raw, next_paper = library.page(f"collections/{key}/items/top", {"itemType": "-note"}, args.paper_start, args.paper_limit)
        papers = [r for r in raw if top_paper(r)]
        scope = {"scope": {"collection": key, "paper_start": args.paper_start, "papers_in_batch": len(papers)},
                 "next_paper_start": next_paper}
    records = (mark for item in papers for mark in highlight_records(library, item, args.query))
    rows, more = page_matches(records, args.start, args.limit)
    return rows, more, scope


def run(args):
    library = LocalLibrary(args.group)
    if not 1 <= args.limit <= 100 or args.start < 0:
        raise LocalError("invalid_input", "Choose --limit 1 to 100 and a nonnegative --start.")
    scope = {}
    if args.command == "highlights":
        rows, more, scope = highlight_page(library, args)
    elif args.command == "collections":
        page, more = library.page("collections", {}, args.start, args.limit)
        rows = [{"key": r["key"], "name": r["data"]["name"],
                 "parent": r["data"].get("parentCollection") or None} for r in page]
    else:
        path = f"collections/{check_key(args.collection, user_input=True)}/items/top" if args.collection else "items/top"
        params = {"itemType": "-note"}
        doi = as_doi(args.doi or args.query)
        if args.doi is not None and not doi:
            raise LocalError("invalid_input", "Expected a DOI or doi.org URL.")
        if doi:
            params.update(q=doi, qmode="everything")
            matching = (paper_record(r) for r in library.items(path, params) if top_paper(r) and as_doi(r["data"].get("DOI")) == doi)
            rows, more = page_matches(matching, args.start, args.limit)
        else:
            if args.query:
                params["q"] = args.query
            page, more = library.page(path, params, args.start, args.limit)
            rows = [paper_record(r) for r in page if top_paper(r)]
    has_page = rows or more is not None or scope.get("next_paper_start") is not None
    return {"source": "Zotero Desktop", "library": library.link_scope, "status": "ok" if has_page else "not_found",
            "records": rows, "next_start": more, **scope}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("collections", "papers", "highlights"):
        command = commands.add_parser(name)
        command.add_argument("--group", type=int, help="Local group library ID (default: personal library)")
        command.add_argument("--limit", type=int, default=10)
        command.add_argument("--start", type=int, default=0)
        if name == "papers":
            command.add_argument("--collection", help="Limit to this Zotero collection key")
            search = command.add_mutually_exclusive_group()
            search.add_argument("--query", help="Title, author, year or DOI")
            search.add_argument("--doi", help="Find this exact DOI")
        if name == "highlights":
            target = command.add_mutually_exclusive_group(required=True)
            target.add_argument("--paper", help="Zotero paper or PDF attachment key")
            target.add_argument("--collection", help="Search within a batch of papers in this collection")
            command.add_argument("--paper-start", type=int, default=0, help="First paper in the collection batch")
            command.add_argument("--paper-limit", type=int, default=5, help="Size of collection batch (1–20)")
            command.add_argument("--query", default="", help="Phrase in selected text or annotation comments")
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except LocalError as exc:
        result = {"source": "Zotero Desktop", "status": exc.status, "detail": str(exc), "records": []}
    except (OSError, HTTPException):
        result = {"source": "Zotero Desktop", "status": "unavailable", "records": [],
                  "detail": "Zotero Desktop is not reachable on its local API port."}
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        result = {"source": "Zotero Desktop", "status": "error", "records": [], "detail": f"Unexpected Zotero data: {exc}"}
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] in ("ok", "not_found") else 2


if __name__ == "__main__":
    raise SystemExit(main())
