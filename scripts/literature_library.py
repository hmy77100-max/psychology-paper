"""Save and retrieve an author's literature across papers and working directories."""
import argparse
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from contextlib import closing
from itertools import combinations, islice
from pathlib import Path
from urllib.parse import urlsplit

from literature_query import arxiv_identifier, normalize_doi


SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY, doi TEXT, title TEXT NOT NULL, title_key TEXT NOT NULL,
    authors TEXT NOT NULL, year TEXT, venue TEXT, kind TEXT, url TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS by_doi ON works(doi);
CREATE INDEX IF NOT EXISTS by_title ON works(title_key);
DROP INDEX IF EXISTS by_url;
CREATE INDEX IF NOT EXISTS by_candidate_url ON works(url) WHERE url <> '';
CREATE TABLE IF NOT EXISTS sources (
    work_id INTEGER REFERENCES works, source TEXT, request_url TEXT, retrieved_at TEXT,
    record_url TEXT, PRIMARY KEY(work_id, source, request_url, retrieved_at, record_url)
);
CREATE TABLE IF NOT EXISTS tags (
    work_id INTEGER REFERENCES works, tag TEXT, PRIMARY KEY(work_id, tag)
);
CREATE TABLE IF NOT EXISTS reading (
    work_id INTEGER REFERENCES works, attachment TEXT, version TEXT, locator TEXT, note TEXT,
    was_read INTEGER NOT NULL, blob_sha256 TEXT NOT NULL,
    PRIMARY KEY(work_id, attachment, version, locator, note, blob_sha256)
);
CREATE TABLE IF NOT EXISTS stored_files (
    sha256 TEXT PRIMARY KEY, content BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS relations (
    work_id INTEGER REFERENCES works, relation TEXT, related_doi TEXT,
    PRIMARY KEY(work_id, relation, related_doi)
);
"""


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def citation_ids(record):
    """Use the identifiers of this record; an arXiv paper's journal DOI is a relation."""
    url = urlsplit(record.get("url") or "")
    host, path = url.hostname, url.path.strip("/")
    doi, pmid = record.get("doi"), record.get("pmid")
    arxiv, pmcid = record.get("arxiv_id"), record.get("pmcid")
    if host in {"doi.org", "dx.doi.org"} and not doi:
        doi = record["url"]
    if not pmid:
        if host == "pubmed.ncbi.nlm.nih.gov" and path.isdigit():
            pmid = path
        elif host in {"europepmc.org", "www.ebi.ac.uk"} and re.fullmatch(r"article/MED/[0-9]+", path):
            pmid = path.rsplit("/", 1)[-1]
    if host == "arxiv.org" and path.startswith("abs/") and not arxiv:
        arxiv = record["url"]
    ids = {}
    if doi:
        ids["doi"] = normalize_doi(doi).casefold()
    if pmid and re.fullmatch(r"[1-9][0-9]*", str(pmid)):
        ids["pmid"] = str(pmid)
    if pmcid and re.fullmatch(r"PMC[1-9][0-9]*(?:\.[0-9]+)?", str(pmcid), re.I):
        ids["pmcid"] = str(pmcid).upper()
    if arxiv:
        base, version = arxiv_identifier(arxiv)
        ids["arxiv_id"] = base.casefold() + version
    return ids


def edition_links(record):
    links = {}
    pairs = list(record.get("relations") or [])
    if record.get("journal_doi"):
        pairs.append(("is-preprint-of", record["journal_doi"]))
    for kind, entries in (record.get("relation") or {}).items():
        pairs.extend((kind, entry["id"]) for entry in entries
                     if entry.get("id-type") == "doi" and entry.get("id"))
    for kind, doi in pairs:
        if kind in {"is-preprint-of", "has-preprint", "is-manuscript-of", "has-manuscript"}:
            links[normalize_doi(doi).casefold()] = "publication_type"
        elif kind in {"is-version-of", "has-version", "is-new-version-of", "is-previous-version-of"}:
            links[normalize_doi(doi).casefold()] = "version"
    return links


def title_words(text):
    return re.sub(r"[\s\-,.:;!?—–]+", " ", normalized(text or "")).strip()


def has_extra_subtitle(left, right):
    """Some indexes store only the main title. Do not drop two different subtitles."""
    for short, long in ((left, right), (right, left)):
        short = normalized(short or "")
        head, colon, tail = normalized(long or "").partition(":")
        if not colon or not tail.strip() or ":" in short or title_words(head) != title_words(short):
            continue
        if len(short.split()) < 4 and len(short) < 24:
            continue
        return not re.search(r"\b(errat\w*|corrigend\w*|correct\w*|retract\w*|addend\w*|edition|"
                             r"revised version|expression of concern)\b|勘误|勘誤|更正|撤[稿回]|修[订訂]版", tail)
    return False


def author_forms(name):
    # Crossref often supplies "Elizabeth A. Hoge", PubMed "Hoge EA".
    plain = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
    words = re.findall(r"[^\W_]+", plain, re.UNICODE)
    if not words:
        return []
    if len(words) == 1:
        return [(words[0].casefold(), [])]
    forms = []
    for family, rest in ((words[-1], words[:-1]), (words[0], words[1:])):
        given = []
        for word in rest:
            if word.isupper() and word.isascii() and len(word) <= 3:
                given.extend(word.casefold())
            else:
                given.append(word.casefold())
        forms.append((family.casefold(), given))
    return forms


def compatible_authors(left, right):
    if normalized(left) == normalized(right):
        return True
    for family, given in author_forms(left):
        for other_family, other_given in author_forms(right):
            if family != other_family:
                continue
            if all(a == b or (min(len(a), len(b)) == 1 and a[0] == b[0]) for a, b in zip(given, other_given)):
                return True
    return False


def publication_form(record, ids):
    types = {normalized(t) for t in [record.get("type"), *(record.get("publication_types") or [])] if t}
    if "arxiv_id" in ids or types & {"preprint", "posted-content"}:
        return "preprint"
    if types & {"published erratum", "erratum", "corrigendum", "correction", "retraction of publication",
                "expression of concern"}:
        return "notice"
    if types & {"journal-article", "journal article", "article"}:
        return "article"
    return ""


def compare_citations(left, right):
    """Compare one pair. Related editions stay independent and carry no shared reading state."""
    left_ids, right_ids = citation_ids(left), citation_ids(right)
    left_arxiv, right_arxiv = left_ids.get("arxiv_id"), right_ids.get("arxiv_id")
    if left_arxiv and right_arxiv:
        left_base, left_version = arxiv_identifier(left_arxiv)
        right_base, right_version = arxiv_identifier(right_arxiv)
        if left_base == right_base and left_version != right_version:
            return {"status": "related", "differences": ["version"]}
    for record, target in ((left, right_ids.get("doi")), (right, left_ids.get("doi"))):
        if target:
            relation = edition_links(record).get(target)
            if relation:
                return {"status": "related", "differences": [relation]}

    common = sorted(left_ids.keys() & right_ids.keys())
    id_differences = [key for key in common if left_ids[key] != right_ids[key]]
    shared = any(left_ids[key] == right_ids[key] for key in common
                 if key != "arxiv_id" or arxiv_identifier(left_ids[key])[1])
    title1, title2 = title_words(left.get("title")), title_words(right.get("title"))
    same_title = bool(title1 and title1 == title2)
    if not shared and not same_title:
        return {"status": "distinct", "differences": id_differences}

    differences = list(id_differences)
    extra_subtitle = bool(shared and not same_title and has_extra_subtitle(left.get("title"), right.get("title")))
    if title1 and title2 and not same_title and not extra_subtitle:
        differences.append("title")
    left_authors = left.get("authors") or ([left["first_author"]] if left.get("first_author") else [])
    right_authors = right.get("authors") or ([right["first_author"]] if right.get("first_author") else [])
    author_conflict = any(not compatible_authors(a, b) for a, b in zip(left_authors, right_authors))
    counts = left.get("author_count"), right.get("author_count")
    if author_conflict or (all(counts) and counts[0] != counts[1]):
        differences.append("authors")
    status = "possible"
    if shared:
        status = "conflict" if differences else "same"
    left_form, right_form = publication_form(left, left_ids), publication_form(right, right_ids)
    if left_form and right_form and left_form != right_form:
        differences.append("publication_type")
        if status == "same":
            status = "possible"
    if extra_subtitle:
        differences.append("subtitle")
        if status == "same" and not (left_authors and right_authors):
            status = "possible"
    year1, year2 = str(left.get("year") or ""), str(right.get("year") or "")
    if year1 and year2 and year1 != year2:
        differences.append("year")
        if shared and not (year1.isdigit() and year2.isdigit() and abs(int(year1) - int(year2)) == 1):
            status = "conflict"
        elif status == "same" and not ((same_title or extra_subtitle) and left_authors and right_authors):
            status = "possible"
    return {"status": status, "differences": differences}


def field(record, key):
    value = record.get(key)
    if value is None:
        return ""
    if key == "year" and isinstance(value, int):
        return str(value)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be text.")
    return value.strip()


def selected_record(path, pick):
    if path == "-":
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    else:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Supply a bibliographic record or a literature_query.py result.")
    if payload.get("preview_only") is True:
        raise ValueError("This is a search preview. Retrieve the selected record before saving it.")
    record = payload
    if "records" in payload:
        rows = payload["records"]
        if payload.get("status") not in {"matched", "candidates"} or not isinstance(rows, list) or not rows:
            raise ValueError("The query did not return selectable candidates.")
        if pick is None and len(rows) > 1:
            raise ValueError("Choose one candidate using --pick (numbered from 1).")
        index = 1 if pick is None else pick
        if not 1 <= index <= len(rows):
            raise ValueError("--pick is outside the candidate list.")
        record = rows[index - 1]
    elif pick not in (None, 1):
        raise ValueError("The input has only one record.")
    if not isinstance(record, dict):
        raise ValueError("Expected a bibliographic record.")
    item = {k: field(record, k) for k in ("doi", "title", "year", "venue", "type", "url",
                                          "pmid", "pmcid", "arxiv_id", "journal_doi")}
    item["doi"] = normalize_doi(item["doi"]).casefold() if item["doi"] else None
    if not item["title"] and not item["doi"]:
        raise ValueError("At least a title or DOI is needed.")
    authors = record.get("authors", [])
    if not isinstance(authors, list) or not all(isinstance(a, str) for a in authors):
        raise ValueError("authors must be a list of names.")
    item["authors"] = authors
    types = record.get("publication_types")
    if types is not None:
        if not isinstance(types, list) or not all(isinstance(t, str) for t in types):
            raise ValueError("publication_types must be a list of labels.")
        item["publication_types"] = types
    count = record.get("author_count")
    if count is not None:
        if type(count) is not int or count < len(authors):
            raise ValueError("author_count must include all listed authors.")
        item["author_count"] = count
    item["source"] = field(payload, "source") or field(record, "source") or "manual"
    item["request_url"] = field(payload, "request_url")
    item["retrieved_at"] = field(payload, "retrieved_at")
    relations = record.get("relation", {})
    if not isinstance(relations, dict):
        raise ValueError("Expected a mapping of DOI relations.")
    item["relations"] = []
    for kind, entries in relations.items():
        if not isinstance(entries, list):
            raise ValueError("Expected a list of relation entries.")
        for entry in entries:
            if isinstance(entry, dict) and entry.get("id-type") == "doi":
                item["relations"].append((kind, normalize_doi(field(entry, "id")).casefold()))
    return item


def attachment_reference(value):
    if not value:
        return ""
    if value.startswith("zotero://"):
        return value
    return str(Path(value).expanduser().resolve())


def store_attachment(db, reference):
    if not reference or reference.startswith("zotero://") or not Path(reference).is_file():
        raise ValueError("--store-file requires an existing local file in --attachment.")
    data = Path(reference).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    inserted = db.execute("INSERT OR IGNORE INTO stored_files VALUES(?,?)", (digest, data)).rowcount
    return digest, "stored_bytes" if inserted else "reused_stored_bytes"


def reading_copy(db, key, args):
    attachment = attachment_reference(args.attachment)
    if not args.sha256:
        if args.store_file:
            digest, disposition = store_attachment(db, attachment)
            return attachment, args.version, digest, disposition
        disposition = "none"
        if attachment:
            disposition = "linked_zotero" if attachment.startswith("zotero://") else "linked_local"
        return attachment, args.version, "", disposition
    rows = db.execute(
        """SELECT DISTINCT attachment,version FROM reading
           WHERE work_id=? AND blob_sha256=? AND (?='' OR attachment=?) AND (?='' OR version=?)""",
        (key, args.sha256, attachment, attachment, args.version, args.version),
    ).fetchall()
    if not rows:
        raise ValueError("No matching stored file for this library version.")
    if len(rows) > 1:
        raise ValueError("Select the original attachment or version for these reading notes.")
    return rows[0]["attachment"], rows[0]["version"], args.sha256, "reused_stored_bytes"


def export_attachment(db, args):
    rows = db.execute("SELECT DISTINCT blob_sha256 FROM reading WHERE work_id=? AND blob_sha256<>''",
                      (args.id,)).fetchall()
    choices = [r[0] for r in rows]
    if args.sha256:
        if args.sha256 not in choices:
            raise ValueError("This file was not stored for this library version.")
        digest = args.sha256
    elif len(choices) == 1:
        digest = choices[0]
    elif choices:
        raise ValueError("Several files are stored. Select --sha256 from this version's reading entries.")
    else:
        raise ValueError("No attachment bytes stored for this version.")
    content = db.execute("SELECT content FROM stored_files WHERE sha256=?", (digest,)).fetchone()[0]
    output = args.output.expanduser().resolve()
    with output.open("xb") as stream:
        try:
            stream.write(content)
            stream.flush()
        except OSError:
            stream.close()
            output.unlink(missing_ok=True)
            raise
    return {"status": "exported", "id": args.id, "sha256": digest, "output": str(output)}


def citation_snapshot(record):
    return {k: record[k] for k in ("doi", "title", "authors", "author_count", "year", "pmid", "pmcid",
                                  "arxiv_id", "journal_doi", "type", "publication_types")
            if record.get(k)}


def saved_sources(db, key):
    columns = "source,request_url,retrieved_at,record_url"
    sources = {tuple(row): dict(row) for row in db.execute(
        f"SELECT {columns} FROM sources WHERE work_id=? ORDER BY rowid", (key,))}
    # Old libraries retain their original source links even when no per-source citation was kept.
    if sources and db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_citations'").fetchone():
        for row in db.execute(f"SELECT {columns},citation FROM source_citations WHERE work_id=? ORDER BY rowid", (key,)):
            sources[row[:4]].setdefault("citations", []).append(json.loads(row["citation"]))
    return list(sources.values())


def check_save_identity(db, stored, incoming, *, author_selected):
    key = stored["id"]
    stored = dict(stored)
    stored["type"] = stored.pop("kind")
    stored["authors"] = json.loads(stored["authors"])
    stored["relations"] = [tuple(row) for row in db.execute(
        "SELECT relation,related_doi FROM relations WHERE work_id=?", (key,))]
    candidates = [(entry["source"], {**snapshot, "url": entry["record_url"]})
                  for entry in saved_sources(db, key) for snapshot in entry.get("citations", [])]
    candidates.append(("library_record", stored))
    pending = None
    new_ids = citation_ids(incoming)
    for source, previous in candidates:
        comparison = compare_citations(previous, incoming)
        old_ids = citation_ids(previous)
        incompatible = [name for name in old_ids.keys() & new_ids.keys() if old_ids[name] != new_ids[name]]
        if incompatible or comparison["status"] in {"related", "conflict"}:
            return {"status": "metadata_conflict", "id": key,
                    "differences": sorted(set(comparison["differences"] + incompatible)),
                    "stored": {"source": source, "url": previous.get("url"), **citation_snapshot(previous)},
                    "incoming": {"source": incoming["source"], "url": incoming["url"], **citation_snapshot(incoming)},
                    "detail": "Review the source records and submit the verified version."}
        if comparison["status"] != "possible":
            continue
        type_mismatch = "publication_type" in comparison["differences"]
        if type_mismatch or (pending is None and not author_selected and old_ids.keys() & new_ids.keys()):
            pending = {"status": "possible_duplicate", "id": key, "differences": comparison["differences"],
                       "stored": {"source": source, **citation_snapshot(previous)},
                       "incoming": {"source": incoming["source"], **citation_snapshot(incoming)},
                       "detail": ("Check the publication type against the original source before saving." if type_mismatch
                                  else "Check the sources, then use --id if this is the same version.")}
    return pending


def save(db, args, record):
    # Acquire the write lock before checking identities or possible duplicates.
    db.execute("BEGIN IMMEDIATE")
    key = args.id
    if key is not None:
        if not db.execute("SELECT 1 FROM works WHERE id=?", (key,)).fetchone():
            raise ValueError("No saved version has this id.")
    if record:
        doi, url = record["doi"], record["url"]
        if key is None and doi:
            row = db.execute("SELECT id FROM works WHERE doi=?", (doi,)).fetchone()
            key = row["id"] if row else None
        title_key = normalized(record["title"])
        if key is None and (title_key or url) and not args.separate:
            matches = db.execute(
                """SELECT id,title,doi,url FROM works WHERE (? IS NULL OR doi IS NULL)
                   AND ((title_key<>'' AND title_key=?) OR (url<>'' AND url=?)) ORDER BY id""",
                (doi, title_key, url),
            ).fetchall()
            if matches:
                return {"status": "possible_duplicate", "records": [dict(r) for r in matches],
                        "detail": "Choose --id for the same version, or --separate for a distinct record."}
        authors = json.dumps(record["authors"], ensure_ascii=False)
        if key is None:
            key = db.execute(
                "INSERT INTO works(doi,title,title_key,authors,year,venue,kind,url) VALUES(?,?,?,?,?,?,?,?)",
                (doi, record["title"], title_key, authors, record["year"], record["venue"], record["type"], url),
            ).lastrowid
        else:
            old = db.execute("SELECT * FROM works WHERE id=?", (key,)).fetchone()
            review = check_save_identity(db, old, record, author_selected=args.id is not None)
            if review:
                return review
            old_authors = json.loads(old["authors"])
            if old_authors and record["authors"][:len(old_authors)] != old_authors:
                authors = old["authors"]
            db.execute(
                "UPDATE works SET doi=coalesce(doi,?),title=?,title_key=?,authors=?,year=?,venue=?,kind=?,url=? WHERE id=?",
                (doi, old["title"] or record["title"], old["title_key"] or title_key, authors,
                 old["year"] or record["year"], old["venue"] or record["venue"],
                 old["kind"] or record["type"], old["url"] or url, key),
            )
        provenance = (key, record["source"], record["request_url"], record["retrieved_at"], url)
        db.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?)", provenance)
        # A separate table keeps older installations compatible and is created only on an accepted save.
        db.execute("""CREATE TABLE IF NOT EXISTS source_citations (
                   work_id INTEGER, source TEXT, request_url TEXT, retrieved_at TEXT, record_url TEXT, citation TEXT,
                   PRIMARY KEY(work_id,source,request_url,retrieved_at,record_url,citation),
                   FOREIGN KEY(work_id,source,request_url,retrieved_at,record_url)
                   REFERENCES sources(work_id,source,request_url,retrieved_at,record_url))""")
        db.execute("INSERT OR IGNORE INTO source_citations VALUES(?,?,?,?,?,?)",
                   (*provenance, json.dumps(citation_snapshot(record), ensure_ascii=False, sort_keys=True)))
        db.executemany("INSERT OR IGNORE INTO relations VALUES(?,?,?)",
                       [(key, kind, related) for kind, related in record["relations"]])
    db.executemany("INSERT OR IGNORE INTO tags VALUES(?,?)", [(key, t.strip()) for t in args.tag if t.strip()])
    disposition = "none"
    if any((args.read, args.attachment, args.version, args.locator, args.note, args.store_file, args.sha256)):
        attachment, version, digest, disposition = reading_copy(db, key, args)
        db.execute(
            "INSERT INTO reading VALUES(?,?,?,?,?,?,?) ON CONFLICT(work_id,attachment,version,locator,note,blob_sha256) "
            "DO UPDATE SET was_read=max(was_read,excluded.was_read)",
            (key, attachment, version, args.locator, args.note, int(args.read), digest),
        )
    return {"status": "saved", "id": key, "attachment_disposition": disposition}


def show(db, key):
    row = db.execute("SELECT * FROM works WHERE id=?", (key,)).fetchone()
    if not row:
        return {"status": "not_found"}
    record = dict(row)
    record.pop("title_key")
    record["type"] = record.pop("kind")
    record["authors"] = json.loads(record["authors"])
    record["sources"] = saved_sources(db, key)
    record["tags"] = [r[0] for r in db.execute("SELECT tag FROM tags WHERE work_id=? ORDER BY tag", (key,))]
    record["reading"] = [dict(r) for r in db.execute(
        "SELECT attachment,version,locator,note,was_read,blob_sha256 FROM reading WHERE work_id=? ORDER BY rowid", (key,))]
    for entry in record["reading"]:
        entry["read"] = bool(entry.pop("was_read"))
        path = entry["attachment"]
        entry["attachment_available"] = Path(path).is_file() if path and not path.startswith("zotero://") else None
    record["read"] = any(r["read"] for r in record["reading"])
    record["related"] = [dict(r) for r in db.execute(
        """SELECT w.id,r.related_doi AS doi,r.relation,'outgoing' AS direction
           FROM relations r LEFT JOIN works w ON w.doi=r.related_doi WHERE r.work_id=?
           UNION ALL SELECT w.id,w.doi,r.relation,'incoming' FROM relations r
           JOIN works w ON w.id=r.work_id WHERE r.related_doi=? ORDER BY doi,relation""",
        (key, record["doi"]))]
    return {"status": "found", "record": record}


def find(db, term, offset):
    db.create_function("norm", 1, normalized)
    key = normalized(term)
    rows = db.execute(
        """SELECT id,title,doi,authors,year FROM works w
           WHERE instr(norm(w.title || ' ' || coalesce(w.doi,'') || ' ' || w.authors || ' ' || coalesce(w.year,'')), :key) > 0
              OR (w.url <> '' AND w.url = :url)
              OR EXISTS(SELECT 1 FROM sources WHERE work_id=w.id AND record_url <> '' AND record_url = :url)
              OR EXISTS(SELECT 1 FROM tags WHERE work_id=w.id AND instr(norm(tag),:key) > 0)
              OR EXISTS(SELECT 1 FROM reading WHERE work_id=w.id
                  AND instr(norm(note || ' ' || version || ' ' || locator || ' ' || attachment),:key) > 0)
           ORDER BY id DESC LIMIT 51 OFFSET :offset""", {"key": key, "url": term.strip(), "offset": offset})
    records = [dict(r) for r in rows]
    next_offset = offset + 50 if len(records) > 50 else None
    records = records[:50]
    for record in records:
        record["authors"] = json.loads(record["authors"])
    return {"status": "found" if records else "not_found", "records": records, "next_offset": next_offset}


def reading_status(db, doi):
    row = db.execute("SELECT id FROM works WHERE doi=?", (doi,)).fetchone()
    if row is None:
        return {"status": "no_local_record", "doi": doi, "read_evidence": []}
    evidence = [dict(entry) for entry in db.execute(
        """SELECT DISTINCT version, attachment, locator, blob_sha256 FROM reading
           WHERE work_id=? AND was_read=1 ORDER BY version,attachment,locator,blob_sha256""", (row["id"],))]
    return {"status": "has_read_record" if evidence else "saved_no_read_record",
            "id": row["id"], "doi": doi, "read_evidence": evidence}


def library_exists(path):
    try:
        path.stat()
    except FileNotFoundError:
        return False
    return True


def read_search_window(path, number):
    if path == "-":
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    else:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("source"), str) or not payload["source"].strip():
        raise ValueError(f"Input {number} must be a query result with its source.")
    status = payload.get("status")
    has_rows = status in ("candidates", "matched", "partial")
    if not has_rows and status not in ("not_found", "seed_not_found", "access_denied", "rate_limited",
                                        "invalid_input", "error"):
        raise ValueError(f"Input {number} does not describe a bibliographic search.")
    rows = payload.get("records")
    if not isinstance(rows, list) or len(rows) > 20 or (rows and not has_rows):
        raise ValueError(f"Input {number} must contain at most 20 candidate records consistent with its status.")
    if (has_rows and not rows and status != "partial") or payload.get("returned", len(rows)) != len(rows):
        raise ValueError(f"Input {number} has an inconsistent result count.")
    source = payload["source"]
    scope = {key: payload[key] for key in ("source", "status", "total_results", "limit", "truncated",
             "retrieved_at", "query", "from_date", "to_date", "sort", "direction", "warnings",
             "missing_pmids", "retry_after", "detail") if key in payload}
    if isinstance(payload.get("seed"), dict):
        scope["seed"] = {key: payload["seed"][key] for key in ("doi", "openalex_id") if payload["seed"].get(key)}
    scope.update(input=number, returned=len(rows))
    records = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not any(row.get(k) for k in (
                "title", "doi", "pmid", "pmcid", "arxiv_id", "openalex_id", "source_id", "url")):
            raise ValueError(f"Input {number}, row {index} has no bibliographic identity.")
        for key in ("title", "doi", "pmid", "pmcid", "arxiv_id", "openalex_id", "source_id", "url", "year"):
            field(row, key)
        authors = row.get("authors") or ([row["first_author"]] if row.get("first_author") else [])
        if not isinstance(authors, list) or not all(isinstance(author, str) for author in authors):
            raise ValueError(f"Input {number}, row {index} has invalid authors.")
        record = dict(row, authors=authors)
        origin = {"source": source, "input": number, "row": index}
        records.append((record, origin))
    return scope, records


def compare_windows(paths, check_offset=0):
    if not 2 <= len(paths) <= 5 or paths.count("-") > 1:
        raise ValueError("Supply 2 to 5 query responses, with at most one read from stdin.")
    if check_offset < 0:
        raise ValueError("--check-offset must be nonnegative.")
    inputs, entries = [], []
    for index, path in enumerate(paths, 1):
        scope, rows = read_search_window(path, index)
        inputs.append(scope)
        entries.extend(rows)

    # A sparse entry can appear compatible with two records which contradict each other.
    # Combine a connected set of matches only if every pair agrees.
    matches = [set() for _ in entries]
    pairs = {}
    for left, right in combinations(range(len(entries)), 2):
        try:
            comparison = compare_citations(entries[left][0], entries[right][0])
        except (TypeError, AttributeError, KeyError, ValueError) as exc:
            raise ValueError(f"Invalid citation metadata at {entries[left][1]} or {entries[right][1]}: {exc}") from exc
        pairs[left, right] = comparison
        if comparison["status"] == "same":
            matches[left].add(right)
            matches[right].add(left)
    unseen = set(range(len(entries)))
    groups = []
    while unseen:
        pending = [min(unseen)]
        unseen.remove(pending[0])
        component = []
        while pending:
            index = pending.pop()
            component.append(index)
            neighbors = matches[index] & unseen
            pending.extend(neighbors)
            unseen.difference_update(neighbors)
        component.sort()
        if all(pairs[left, right]["status"] == "same" for left, right in combinations(component, 2)):
            groups.append(component)
        else:
            groups.extend([index] for index in component)
    groups.sort(key=lambda group: group[0])
    candidates, owners = [], {}
    for group_id, group in enumerate(groups, 1):
        first = entries[group[0]][0]
        # Display one actual record. Other source records retain their own titles, authors and dates.
        candidate = {key: first[key] for key in ("title", "year", "doi", "pmid", "pmcid", "arxiv_id",
                     "openalex_id", "source_id", "version") if first.get(key)}
        if first["authors"]:
            candidate["first_author"] = first["authors"][0]
        if not candidate and first.get("url"):
            candidate["url"] = first["url"]
        candidate.update(group=group_id, origins=[entries[i][1] for i in group])
        differences = {field for pair in combinations(group, 2) for field in pairs[pair]["differences"]}
        if differences:
            candidate["differences"] = sorted(differences)
            for index, origin in zip(group, candidate["origins"]):
                record = entries[index][0]
                origin["reported"] = {key: record[key] for key in sorted(differences)
                                      if key in ("doi", "year", "title", "pmid", "arxiv_id", "version") and record.get(key)}
                if "subtitle" in differences:
                    origin["reported"]["title"] = record.get("title")
                if "authors" in differences and record["authors"]:
                    origin["reported"]["first_author"] = record["authors"][0]
        candidates.append(candidate)
        for i in group:
            owners[i] = group_id

    checks = {}
    for (left, right), comparison in pairs.items():
        status = comparison["status"]
        a, b = sorted((owners[left], owners[right]))
        if a == b or status == "distinct":
            continue
        differences = comparison["differences"]
        if status == "same":
            status, differences = "possible", ["ambiguous_match_chain"]
        checks.setdefault((a, b, status), set()).update(differences)
    partial = any(s["status"] not in ("candidates", "matched", "not_found") for s in inputs)
    page = islice(checks.items(), check_offset, check_offset + 50) if check_offset < len(checks) else ()
    return {"status": "partial" if partial else "compared", "preview_only": True, "inputs": inputs,
            "groups": candidates, "total_checks": len(checks),
            "next_check_offset": check_offset + 50 if check_offset + 50 < len(checks) else None,
            "checks": [{"groups": [a, b], "status": status, "differences": sorted(fields)}
                       for (a, b, status), fields in page]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, help="Personal database (default ~/PsychologyPaper/literature.sqlite3)")
    actions = parser.add_subparsers(dest="action", required=True)
    compare = actions.add_parser("compare", help="Compare existing query results locally")
    compare.add_argument("--input", action="append", required=True, help="Query JSON file (repeat; one may be -)")
    compare.add_argument("--check-offset", type=int, default=0, help="Resume a page of ambiguous pairs or conflicts")
    add = actions.add_parser("save", help="Explicitly save one candidate or annotate one saved version")
    add.add_argument("--input", help="UTF-8 JSON input file, or - for stdin")
    add.add_argument("--id", type=int, help="An existing version to update")
    add.add_argument("--pick", type=int, help="Candidate number, starting at 1")
    add.add_argument("--separate", action="store_true", help="Confirm a separate item after a possible title match")
    add.add_argument("--tag", action="append", default=[])
    add.add_argument("--read", action="store_true", help="Mark this version/attachment as read")
    add.add_argument("--version", default="", help="Version actually consulted, e.g. accepted manuscript")
    add.add_argument("--attachment", default="", help="Local file reference or Zotero URI")
    copy_mode = add.add_mutually_exclusive_group()
    copy_mode.add_argument("--store-file", action="store_true", help="Store a recoverable copy of this local file")
    copy_mode.add_argument("--sha256", help="Attach later reading notes to bytes already stored for this --id")
    add.add_argument("--locator", default="", help="Page, section or annotation URI")
    add.add_argument("--note", default="")
    search = actions.add_parser("find")
    search.add_argument("term")
    search.add_argument("--offset", type=int, default=0, help="Offset returned by a previous page of matches")
    status = actions.add_parser("reading-status", help="Look up explicit reading records for this exact DOI")
    status.add_argument("--doi", default="", help="DOI or doi.org URL to check in this personal library")
    actions.add_parser("show").add_argument("id", type=int)
    export = actions.add_parser("export-attachment", help="Recover a stored file to a new path")
    export.add_argument("id", type=int)
    export.add_argument("--sha256", help="File from this version's reading entries (required if several)")
    export.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        path = (args.library or Path.home() / "PsychologyPaper" / "literature.sqlite3").expanduser().resolve()
        if args.action == "reading-status":
            doi = normalize_doi(args.doi).casefold()
        if args.action == "find" and args.offset < 0:
            raise ValueError("--offset must be nonnegative.")
        if args.action == "compare":
            result = compare_windows(args.input, args.check_offset)
        elif args.action == "save":
            if args.input is None and args.id is None:
                raise ValueError("Supply --input or --id.")
            if args.input is None and (args.pick is not None or args.separate):
                raise ValueError("--pick and --separate require --input.")
            if args.sha256 and args.id is None:
                raise ValueError("Use --id to select the owner of this stored file.")
            record = selected_record(args.input, args.pick) if args.input else None
            if args.id is not None and not path.is_file():
                raise ValueError("The selected saved version does not exist.")
            path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(path, timeout=10)) as db:
                db.row_factory = sqlite3.Row
                db.executescript(SCHEMA)
                with db:
                    result = save(db, args, record)
            if result["status"] == "saved":
                result["library_path"] = str(path)
        elif not library_exists(path):
            if args.action == "export-attachment":
                raise ValueError("No saved library at the selected path.")
            if args.action == "reading-status":
                result = {"status": "library_missing", "doi": doi}
            else:
                result = {"status": "not_found", "records": [], "next_offset": None} if args.action == "find" else {"status": "not_found"}
        else:
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
                db.row_factory = sqlite3.Row
                db.execute("BEGIN")
                if args.action == "export-attachment":
                    result = export_attachment(db, args)
                elif args.action == "reading-status":
                    result = reading_status(db, doi)
                else:
                    result = find(db, args.term, args.offset) if args.action == "find" else show(db, args.id)
    except (ValueError, OSError, sqlite3.Error) as exc:
        result = {"status": "error", "detail": str(exc)}
    separators = (",", ":") if args.action == "compare" else None
    print(json.dumps(result, ensure_ascii=True, separators=separators))
    return 2 if result["status"] in {"error", "possible_duplicate", "metadata_conflict"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
