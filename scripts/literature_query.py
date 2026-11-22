"""Look up public literature in one selected index or read a section from Europe PMC."""

import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen


WORKS = "https://api.crossref.org/works"
OPENALEX_WORKS = "https://api.openalex.org/works"
OPENALEX_FIELDS = "id,doi,display_name,publication_year,publication_date,type,primary_location,authorships"
SEARCH_FIELDS = "DOI,title,subtitle,author,container-title,published,type,relation"
USER_AGENT = "PsychologyPaper-LiteratureQuery/1.0 (https://github.com/hmy77100-max/psychology-paper)"


def normalize_doi(value):
    value = value.strip()
    if value.lower().startswith("doi:"):
        value = value[4:].strip()
    if any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("A DOI cannot contain whitespace or control characters.")
    if value.lower().startswith(("https://", "http://")):
        parts = urlsplit(value)
        if parts.netloc.lower() not in ("doi.org", "dx.doi.org"):
            raise ValueError("Supply a DOI or a doi.org resolver URL.")
        value = unquote(parts.path.lstrip("/"))
    if not re.fullmatch(r"10\.[0-9]+(?:\.[0-9]+)*/[^\s\x00-\x1f\x7f]+", value):
        raise ValueError("Invalid DOI. Example: 10.3390/su151914435")
    return value


def first_item(values):
    if not isinstance(values, list):
        raise ValueError("Unexpected list field in a Crossref work.")
    return values[0] if values else None


def work_record(work, *, exact):
    if not isinstance(work, dict) or not isinstance(work.get("DOI"), str):
        raise ValueError("Crossref work is missing its DOI.")
    doi = normalize_doi(work["DOI"])
    authors = []
    for author in work.get("author", []):
        name = author.get("name") or " ".join(filter(None, (author.get("given"), author.get("family"))))
        if name:
            authors.append(name)
    date = first_item(work.get("published", {}).get("date-parts", []))
    title = first_item(work.get("title", []))
    subtitle = first_item(work.get("subtitle", []))
    if title and subtitle:
        end = subtitle.strip().casefold().rstrip(" .")
        main = title.strip().casefold().rstrip(" .")
        if end and main != end and not main.endswith(" " + end):
            separator = " " if title.rstrip().endswith((":", "?", "!")) else ": "
            title = title.rstrip() + separator + subtitle.strip()
    record = {
        "doi": doi,
        "url": "https://doi.org/" + quote(doi, safe="/"),
        "title": title,
        "venue": first_item(work.get("container-title", [])),
        "year": first_item(date) if date else None,
        "authors": authors if exact else authors[:5],
        "author_count": len(authors),
        "type": work.get("type"),
        "relation": work.get("relation") or {},
    }
    abstract = work.get("abstract")
    if exact and isinstance(abstract, str) and abstract.strip():
        # Preserve the deposit, including JATS markup and any qualifications.
        record["abstract"] = {"source": "crossref_deposited_abstract", "content": abstract}
    return record


def result_envelope(source):
    return {
        "source": source, "records": [], "origin": "external_lookup", "reading_status": "not_checked",
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def fetch_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def service_error(result, exc):
    if exc.code == 429:
        return {**result, "status": "rate_limited", "retry_after": exc.headers.get("Retry-After")}
    status = "access_denied" if exc.code in (401, 403) else "error"
    return {**result, "status": status, "detail": f"{result['source']} HTTP {exc.code}"}


def validated_date_filters(from_date, to_date):
    for value in (from_date, to_date):
        if value is not None:
            if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("Publication dates must use YYYY-MM-DD.")
            date.fromisoformat(value)
    if from_date and to_date and from_date > to_date:
        raise ValueError("--from-date must not follow --to-date.")


def date_filter_parts(result, from_date, to_date, from_field, to_field):
    validated_date_filters(from_date, to_date)
    filters = []
    for key, value, field in (("from_date", from_date, from_field), ("to_date", to_date, to_field)):
        if value is not None:
            result[key] = value
            filters.append(f"{field}:{value}")
    return filters


PUBMED_UTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def pubmed_record(work, pmid, *, exact):
    if work["uid"] != pmid or not work.get("title"):
        raise ValueError("PubMed returned an unidentified or mismatched summary.")
    identifiers = {item["idtype"]: item["value"] for item in work.get("articleids", [])}
    authors = [author["name"] for author in work.get("authors", []) if author.get("name")]
    pubdate = work.get("pubdate") or work.get("epubdate") or ""
    year = re.match(r"[0-9]{4}\b", pubdate)
    types = work.get("pubtype", [])
    if not isinstance(types, list):
        raise ValueError("Invalid PubMed publication type list.")
    return {"pmid": pmid, "doi": normalize_doi(identifiers["doi"]) if identifiers.get("doi") else None,
            "pmcid": identifiers.get("pmc"), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "title": work["title"], "authors": authors if exact else authors[:5], "author_count": len(authors),
            "year": int(year.group()) if year else None, "publication_date": pubdate or None,
            "venue": work.get("fulljournalname") or work.get("source"), "type": first_item(types),
            "publication_types": types}


def query_pubmed(query=None, pmid=None, limit=None, *, from_date=None, to_date=None, sort=None):
    result = result_envelope("PubMed")
    rows = 5 if limit is None else limit
    base = {"db": "pubmed", "retmode": "json", "tool": "PsychologyPaper"}
    try:
        validated_date_filters(from_date, to_date)
        if (query is None) == (pmid is None) or not 1 <= rows <= 20 or sort not in (None, "newest"):
            raise ValueError("Choose one PubMed query or PMID, and a list limit from 1 to 20.")
        if pmid is not None:
            if not re.fullmatch(r"[1-9][0-9]*", pmid) or any(x is not None for x in (limit, from_date, to_date, sort)):
                raise ValueError("Supply one numeric PMID; date, sort and limit apply to keyword searches.")
        elif not query.strip():
            raise ValueError("Supply public search terms. PubMed fields such as [mh] and [pt] are supported.")
    except ValueError as exc:
        return {**result, "status": "invalid_input", "detail": str(exc)}

    try:
        if pmid is None:
            params = {**base, "term": query.strip(), "retmax": rows, "sort": "pub_date" if sort else "relevance"}
            if from_date or to_date:
                # ESearch requires both ends of an explicit publication-date interval.
                params.update(datetype="pdat", mindate=(from_date or "0001-01-01").replace("-", "/"),
                              maxdate=(to_date or "9999-12-31").replace("-", "/"))
            result.update({k: v for k, v in (("from_date", from_date), ("to_date", to_date),
                                             ("sort", params["sort"])) if v is not None})
            result["request_url"] = PUBMED_UTILS + "/esearch.fcgi?" + urlencode(params)
            payload = fetch_json(result["request_url"])
            if payload.get("error"):
                raise ValueError(str(payload["error"]))
            search = payload["esearchresult"]
            if search.get("ERROR"):
                raise ValueError(str(search["ERROR"]))
            diagnostics = {key: messages for group in ("warninglist", "errorlist")
                           for key, messages in search.get(group, {}).items() if messages}
            if diagnostics.get("fieldsnotfound"):
                return {**result, "status": "invalid_input", "detail": "PubMed did not recognize a query field.",
                        "warnings": diagnostics}
            if diagnostics:
                result["warnings"] = diagnostics
            ids, total = search["idlist"], int(search["count"])
            if (not isinstance(ids, list) or len(ids) != min(total, rows) or len(ids) != len(set(ids))
                    or not all(re.fullmatch(r"[1-9][0-9]*", ident) for ident in ids)):
                raise ValueError("Inconsistent PubMed search IDs or count.")
            result.update(limit=rows, total_results=total)
            if not ids:
                return {**result, "status": "not_found", "returned": 0, "truncated": False}
            # One batched ESummary follows ESearch; respect the anonymous three-requests/second limit.
            time.sleep(0.35)
        else:
            ids, total = [pmid], 1

        url = PUBMED_UTILS + "/esummary.fcgi?" + urlencode({**base, "id": ",".join(ids)})
        result["summary_request_url" if query is not None else "request_url"] = url
        payload = fetch_json(url)
        if payload.get("error"):
            raise ValueError(str(payload["error"]))
        summaries = payload["result"]
        uids = summaries["uids"]
        if not isinstance(uids, list) or len(set(uids)) != len(uids) or set(uids) - set(ids):
            raise ValueError("PubMed returned an unexpected summary identifier.")
        records, missing = [], []
        for ident in ids:
            work = summaries.get(ident, {}) if ident in uids else {}
            if not work or work.get("error"):
                if pmid and re.match(r"invalid (?:uid|id)\b", str(work.get("error", "")), re.I):
                    return {**result, "status": "not_found", "detail": str(work["error"])}
                missing.append(ident)
            else:
                records.append(pubmed_record(work, ident, exact=pmid is not None))
        result.update(returned=len(records), truncated=total > len(records), records=records)
        if missing:
            return {**result, "status": "partial" if records else "error", "missing_pmids": missing,
                    "detail": "PubMed did not supply a summary for every requested PMID."}
        return {**result, "status": "matched" if pmid is not None else "candidates"}
    except HTTPError as exc:
        return service_error(result, exc)
    except (URLError, OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {**result, "status": "error", "detail": str(exc) or type(exc).__name__}


def query_crossref(query=None, doi=None, limit=None, *, from_date=None, to_date=None, sort=None):
    result = result_envelope("Crossref")
    try:
        filters = date_filter_parts(result, from_date, to_date, "from-pub-date", "until-pub-date")
        if sort not in (None, "newest") or (doi is not None and (filters or sort)):
            raise ValueError("Use publication-date filters and --sort newest with a result list.")
        if (query is None) == (doi is None):
            raise ValueError("Choose one of --query and --doi.")
        if doi is not None:
            if limit is not None:
                raise ValueError("--limit applies only to --query.")
            doi = normalize_doi(doi)
            url = WORKS + "/" + quote(doi, safe="/")
        else:
            query = query.strip()
            rows = 5 if limit is None else limit
            if not query or not 1 <= rows <= 20:
                raise ValueError("--query needs public search terms and --limit must be 1 to 20.")
            params = {"query.bibliographic": query, "rows": rows, "select": SEARCH_FIELDS}
            if filters:
                params["filter"] = ",".join(filters)
            if sort == "newest":
                params.update(sort="published", order="desc")
                result["sort"] = "published:desc"
            url = WORKS + "?" + urlencode(params)
    except ValueError as exc:
        return {**result, "status": "invalid_input", "detail": str(exc)}

    result["request_url"] = url
    try:
        payload = fetch_json(url)
        expected_type = "work" if doi is not None else "work-list"
        if not isinstance(payload, dict) or payload.get("status") != "ok" or payload.get("message-type") != expected_type:
            raise ValueError("Unexpected Crossref response envelope.")
        message = payload.get("message")
        if doi is not None:
            record = work_record(message, exact=True)
            if record["doi"].casefold() != doi.casefold():
                raise ValueError("Crossref returned a different DOI.")
            return {**result, "status": "matched", "records": [record]}
        if not isinstance(message, dict) or not isinstance(message.get("items"), list):
            raise ValueError("Missing Crossref search result list.")
        records = [work_record(item, exact=False) for item in message["items"][:rows]]
        total = message.get("total-results")
        return {**result, "status": "candidates" if records else "not_found", "records": records,
                "limit": rows, "returned": len(records), "total_results": total,
                "truncated": total > len(records) if type(total) is int else None}
    except HTTPError as exc:
        if exc.code == 404 and doi is not None:
            return {**result, "status": "not_found", "detail": "No Crossref record for this DOI."}
        return service_error(result, exc)
    except (URLError, OSError, HTTPException, ValueError, TypeError, AttributeError) as exc:
        return {**result, "status": "error", "detail": str(exc) or type(exc).__name__}


EUROPEPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
FULLTEXT_MAX_BYTES = 12 * 1024 * 1024
PASSAGE_MAX_CHARS = 720


def europepmc_record(work):
    source, ident = work["source"], work["id"]
    if not source or not ident:
        raise ValueError("Europe PMC record has no source identifier.")
    doi = normalize_doi(work["doi"]) if work.get("doi") else None
    authors = work.get("authorString", "").rstrip(".").split(", ")
    return {"source_id": f"{source}:{ident}", "pmid": work.get("pmid"), "pmcid": work.get("pmcid"),
            "doi": doi, "title": work.get("title"), "authors": [name for name in authors[:5] if name],
            "year": work.get("pubYear"), "publication_date": work.get("firstPublicationDate"),
            "venue": work.get("journalTitle"), "type": work.get("pubType"),
            "url": "https://europepmc.org/article/" + quote(source, safe="") + "/" + quote(ident, safe="")}


def xml_text(element):
    return " ".join("".join(element.itertext()).split())


def jats_paragraphs(node, path=(), section_id=None):
    # Only traverse the article body. Its tables, figures and references have other locators.
    if node.tag == "sec":
        heading = node.find("title")
        path += (xml_text(heading) if heading is not None else node.get("sec-type", ""),)
        section_id = node.get("id") or section_id
    for child in node:
        if child.tag == "p":
            yield path, section_id, child.get("id"), xml_text(child)
        elif child.tag in {"sec", "boxed-text", "list", "list-item", "disp-quote"}:
            yield from jats_paragraphs(child, path, section_id)


def europepmc_passages(pmcid, *, section, phrase, limit):
    pmcid = pmcid.strip().upper()
    section = (section or "").strip()
    phrase = " ".join((phrase or "").split())
    rows = 2 if limit is None else limit
    out = {**result_envelope("Europe PMC"), "pmcid": pmcid, "passages": []}
    if (not re.fullmatch(r"PMC[1-9][0-9]*", pmcid) or not (section or phrase)
            or len(phrase) > PASSAGE_MAX_CHARS or not 1 <= rows <= 5):
        return {**out, "status": "invalid_input", "detail": "Choose a PMCID, section or short phrase, and limit 1 to 5."}
    url = f"{EUROPEPMC}/{pmcid}/fullTextXML"
    out.update(request_url=url, url=f"https://europepmc.org/articles/{pmcid}")
    request = Request(url, headers={"Accept": "application/xml", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=50) as response:
            data = response.read(FULLTEXT_MAX_BYTES + 1)
        if len(data) > FULLTEXT_MAX_BYTES:
            return {**out, "status": "size_limit", "detail": "Article XML exceeds the local parsing limit."}
        root = ET.fromstring(data)
        if root.tag.rsplit("}", 1)[-1] != "article":
            raise ValueError("Europe PMC did not return a JATS article.")
        if root.tag.startswith("{"):
            namespace = root.tag.split("}")[0] + "}"
            for element in root.iter():
                element.tag = element.tag.removeprefix(namespace)
        meta = root.find("front/article-meta")
        ids = {tag.get("pub-id-type"): (tag.text or "").strip() for tag in meta.findall("article-id")} if meta is not None else {}
        found_ids = {value.upper().removeprefix("PMC") for name,value in ids.items() if name in {"pmc", "pmcid"}}
        if found_ids and found_ids != {pmcid[3:]}:
            raise ValueError("The full text identifies a different PMCID.")
        body = root.find("body")
        if body is None:
            return {**out, "status": "fulltext_unavailable", "detail": "No article body in this XML."}
        if not found_ids:
            raise ValueError("Cannot verify the PMCID of the article body.")
        out.update(doi=ids.get("doi"), access_level="full_text_excerpt")
        pattern = re.compile(re.escape(phrase), re.IGNORECASE) if phrase else None
        total = 0
        for number, (path, sec_id, para_id, text) in enumerate(jats_paragraphs(body), start=1):
            if not text or (section and section.casefold() not in " / ".join(path).casefold()):
                continue
            match = pattern.search(text) if pattern else None
            if pattern and not match:
                continue
            total += 1
            if len(out["passages"]) >= rows:
                continue
            left = max(0, match.start() - (PASSAGE_MAX_CHARS - len(match.group())) // 2) if match else 0
            left = min(left, max(0, len(text) - PASSAGE_MAX_CHARS))
            right = min(len(text), left + PASSAGE_MAX_CHARS)
            if left and not text[left-1].isspace():
                space = text.find(" ", left, match.start() if match else right)
                if space != -1:
                    left = space + 1
            if right < len(text) and not text[right].isspace():
                space = text.rfind(" ", match.end() if match else left, right)
                if space != -1:
                    right = space
            segment = text[left:right]
            out["passages"].append({"section_path": list(path), "section_id": sec_id, "paragraph_id": para_id,
                                    "body_paragraph": number, "text": segment, "text_start": left,
                                    "text_truncated": len(segment) < len(text)})
        return {**out, "status": "passages" if total else "no_passage",
                "total_matches": total, "truncated": total > len(out["passages"])}
    except HTTPError as exc:
        if exc.code == 404:
            return {**out, "status": "fulltext_unavailable"}
        return service_error(out, exc)
    except (URLError, OSError, HTTPException, ET.ParseError, ValueError) as exc:
        return {**out, "status": "error", "detail": str(exc) or type(exc).__name__}


def query_europepmc(query=None, doi=None, pmcid=None, section=None, passage_query=None, limit=None,
                    from_date=None, to_date=None, sort=None):
    out = result_envelope("Europe PMC")
    try:
        if sum(v is not None for v in (pmcid, doi, query)) != 1:
            raise ValueError("Choose one query, DOI, or PMCID.")
        if (sort or from_date or to_date) and query is None:
            raise ValueError("Date and sort options apply to a search, not an identifier.")
        if pmcid is not None:
            return europepmc_passages(pmcid, section=section, phrase=passage_query, limit=limit)
        if section or passage_query:
            raise ValueError("Section and passage searches require a PMCID.")
        rows = 5 if limit is None else limit
        if not 1 <= rows <= 20 or sort not in (None, "newest"):
            raise ValueError("Choose limit 1 to 20 and optionally sort newest.")
        validated_date_filters(from_date, to_date)
        if doi is not None:
            doi = normalize_doi(doi)
            text = 'DOI:"' + doi.replace("\\", "\\\\").replace('"', '\\"') + '"'
        else:
            text = query.strip()
            if not text:
                raise ValueError("Use nonempty public search terms.")
            if from_date or to_date:
                text = f"({text}) AND FIRST_PDATE:[{from_date or '*'} TO {to_date or '*'}]"
                if from_date:
                    out["from_date"] = from_date
                if to_date:
                    out["to_date"] = to_date
        params = {"query": text, "resultType": "lite", "format": "json", "pageSize": rows}
        if sort:
            params["sort"] = "FIRST_PDATE_D desc"
            out["sort"] = params["sort"]
    except ValueError as exc:
        return {**out, "status": "invalid_input", "detail": str(exc)}
    out["request_url"] = EUROPEPMC + "/search?" + urlencode(params)
    try:
        payload = fetch_json(out["request_url"])
        total = payload["hitCount"]
        hits = payload["resultList"]["result"]
        if not isinstance(hits, list) or type(total) is not int or total < len(hits) or (total and not hits):
            raise ValueError("Inconsistent Europe PMC result list.")
        records = [europepmc_record(hit) for hit in hits[:rows]]
        if doi and any(not r["doi"] or r["doi"].casefold() != doi.casefold() for r in records):
            raise ValueError("Europe PMC returned a record for a different DOI.")
        status = "matched" if doi and len(records) == total == 1 else "candidates"
        return {**out, "status": status if records else "not_found", "records": records,
                "limit": rows, "returned": len(records), "total_results": total, "truncated": total > len(records)}
    except HTTPError as exc:
        return service_error(out, exc)
    except (URLError, OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {**out, "status": "error", "detail": str(exc) or type(exc).__name__}


ARXIV_ATOM = {"a": "http://www.w3.org/2005/Atom", "ax": "http://arxiv.org/schemas/atom",
              "s": "http://a9.com/-/spec/opensearch/1.1/"}
ARXIV_ID = re.compile(r"(\d{2}(?:0[1-9]|1[0-2])\.\d{4,5}|[a-z][a-z.-]*/\d{7})(v[1-9]\d*)?", re.I)


def arxiv_identifier(value):
    value = value.strip()
    if value.lower().startswith("arxiv:"):
        value = value[6:].strip()
    if value.lower().startswith(("https://", "http://")):
        url = urlsplit(value)
        if url.netloc.lower() != "arxiv.org" or not url.path.startswith("/abs/"):
            raise ValueError("Expected an arxiv.org/abs identifier.")
        value = url.path[5:]
    match = ARXIV_ID.fullmatch(value)
    if not match:
        raise ValueError("Invalid arXiv identifier.")
    return match.group(1), (match.group(2) or "").lower()


def arxiv_record(entry, *, exact):
    def value(tag):
        return " ".join(entry.findtext(tag, "", ARXIV_ATOM).split())

    title = value("a:title")
    if title == "Error":
        raise ValueError(value("a:summary") or "arXiv reported a request error.")
    base, version = arxiv_identifier(value("a:id"))
    if not title or not version:
        raise ValueError("Missing arXiv title or version in the returned entry.")
    identifier = base + version
    authors = [item.text.strip() for item in entry.findall("a:author/a:name", ARXIV_ATOM)
               if item.text and item.text.strip()]
    submitted = value("a:published")[:10]
    published_doi = value("ax:doi")
    record = {"title": title, "authors": authors if exact else authors[:5], "author_count": len(authors),
              "arxiv_id": identifier, "version": version, "url": "https://arxiv.org/abs/" + identifier,
              "submitted_date": submitted, "year": date.fromisoformat(submitted).year,
              "venue": "arXiv", "type": "preprint"}
    if published_doi:
        doi = normalize_doi(published_doi)
        if doi.lower().startswith("10.48550/arxiv."):
            record["work_doi"] = doi
        else:
            record["journal_doi"] = doi
            record["relation"] = {"is-preprint-of": [{"id-type": "doi", "id": doi}]}
    if exact:
        abstract = value("a:summary")
        if abstract:
            record["abstract"] = {"source": "arxiv_submitted_abstract", "content": abstract}
        record["categories"] = [cat.get("term") for cat in entry.findall("a:category", ARXIV_ATOM) if cat.get("term")]
    return record


def query_arxiv(query=None, arxiv_id=None, limit=None, *, from_date=None, to_date=None, sort=None):
    out = result_envelope("arXiv")
    try:
        if (query is None) == (arxiv_id is None):
            raise ValueError("Choose an arXiv query or identifier.")
        validated_date_filters(from_date, to_date)
        if arxiv_id is not None:
            if any(option is not None for option in (limit, from_date, to_date, sort)):
                raise ValueError("Date, sort and limit apply to a result list.")
            base, version = arxiv_identifier(arxiv_id)
            rows = 1
            params = {"id_list": base + version, "start": 0, "max_results": rows}
        else:
            rows = 5 if limit is None else limit
            terms = query.strip()
            if not terms or not 1 <= rows <= 20 or sort not in (None, "newest"):
                raise ValueError("Choose public search terms, 1 to 20 results and optionally sort newest.")
            if not re.search(r"\b(?:ti|au|abs|co|jr|rn|cat|all|id|doi|submittedDate):", terms):
                words = re.findall(r'"[^"]+"|[^"\s]+', terms)
                if not words:
                    raise ValueError("Missing arXiv search terms.")
                terms = " AND ".join(f"(ti:{word} OR abs:{word})" for word in words)
            if from_date or to_date:
                start = (from_date or "1991-01-01").replace("-", "") + "0000"
                end = (to_date or "9999-12-31").replace("-", "") + "2359"
                terms = f"({terms}) AND submittedDate:[{start} TO {end}]"
                out.update({key: value for key, value in (("from_date", from_date), ("to_date", to_date)) if value})
            params = {"search_query": terms, "start": 0, "max_results": rows}
            if sort:
                params.update(sortBy="submittedDate", sortOrder="descending")
                out["sort"] = "submittedDate:desc"
    except ValueError as exc:
        return {**out, "status": "invalid_input", "detail": str(exc)}
    url = "https://export.arxiv.org/api/query?" + urlencode(params)
    out["request_url"] = url
    try:
        request = Request(url, headers={"Accept": "application/atom+xml", "User-Agent": USER_AGENT})
        with urlopen(request, timeout=30) as response:
            root = ET.fromstring(response.read())
        if root.tag != "{" + ARXIV_ATOM["a"] + "}feed":
            raise ValueError("Expected an arXiv Atom feed.")
        entries = root.findall("a:entry", ARXIV_ATOM)
        records = [arxiv_record(entry, exact=arxiv_id is not None) for entry in entries]
        total = int(root.findtext("s:totalResults", "", ARXIV_ATOM))
        if total < len(records) or len(records) > rows or (total and not records):
            raise ValueError("Inconsistent arXiv result count.")
        if arxiv_id is not None and records:
            found_base, found_version = arxiv_identifier(records[0]["arxiv_id"])
            if total != 1 or base.casefold() != found_base.casefold() or (version and version != found_version):
                raise ValueError("arXiv returned a different work or version.")
        status = "matched" if arxiv_id is not None else "candidates"
        return {**out, "status": status if records else "not_found", "records": records, "limit": rows,
                "returned": len(records), "total_results": total, "truncated": total > len(records)}
    except HTTPError as exc:
        return service_error(out, exc)
    except (URLError, OSError, HTTPException, ET.ParseError, TypeError, ValueError) as exc:
        return {**out, "status": "error", "detail": str(exc) or type(exc).__name__}


def openalex_record(work, *, exact):
    match = re.fullmatch(r"https://openalex\.org/(W[0-9]+)", work["id"])
    if not match:
        raise ValueError("Invalid OpenAlex work identifier.")
    doi = normalize_doi(work["doi"]) if work.get("doi") else None
    authors = []
    for entry in work.get("authorships", []):
        name = (entry.get("author") or {}).get("display_name")
        if name:
            authors.append(name)
    location = work.get("primary_location") or {}
    record = {"openalex_id": match[1], "doi": doi, "title": work.get("display_name"),
              "url": "https://doi.org/" + quote(doi, safe="/") if doi else work["id"],
              "authors": authors if exact else authors[:5], "year": work.get("publication_year"),
              "type": work.get("type"), "venue": (location.get("source") or {}).get("display_name"),
              "indexed_location_version": location.get("version")}
    if work.get("publication_date"):
        record["publication_date"] = work["publication_date"]
    return record


def query_openalex(query=None, doi=None, direction=None, limit=None, *, from_date=None, to_date=None, sort=None):
    result = result_envelope("OpenAlex")
    # A work can aggregate multiple versions. Its indexed location does not identify a reader's copy.
    result["record_scope"] = "indexed_work"
    rows = 5 if limit is None else limit
    try:
        filters = date_filter_parts(result, from_date, to_date, "from_publication_date", "to_publication_date")
        if sort not in (None, "newest") or (doi is not None and not direction and (filters or sort)):
            raise ValueError("Use publication-date filters and --sort newest with a result list.")
        if direction and not doi:
            raise ValueError("--direction needs a seed DOI.")
        if (query is None) == (doi is None) or not 1 <= rows <= 20:
            raise ValueError("Choose one of --query and --doi; --limit must be 1 to 20.")
        if query is not None and not query.strip():
            raise ValueError("--query requires public search terms.")
        if doi is not None:
            doi = normalize_doi(doi)
            if limit is not None and not direction:
                raise ValueError("--limit is only for result lists.")
    except ValueError as exc:
        return {**result, "status": "invalid_input", "detail": str(exc)}
    try:
        if doi:
            result["request_url"] = OPENALEX_WORKS + "/doi:" + quote(doi, safe="/") + "?" + urlencode({"select": OPENALEX_FIELDS})
            if direction:
                result.update(direction=direction, seed_request_url=result["request_url"])
            record = openalex_record(fetch_json(result["request_url"]), exact=True)
            if not record["doi"] or record["doi"].casefold() != doi.casefold():
                raise ValueError("OpenAlex did not return the requested DOI.")
            if not direction:
                return {**result, "status": "matched", "records": [record]}
            result["seed"] = record
            filter_name = {"references": "cited_by", "citations": "cites"}[direction]
            filters.insert(0, f"{filter_name}:{record['openalex_id']}")
            params = {}
        else:
            params = {"search": query.strip()}
        if filters:
            params["filter"] = ",".join(filters)
        if sort == "newest" or direction:
            result["sort"] = "publication_date:desc" if sort == "newest" else "cited_by_count:desc"
            params["sort"] = result["sort"]
        params.update(per_page=rows, select=OPENALEX_FIELDS)
        result["request_url"] = OPENALEX_WORKS + "?" + urlencode(params)
        payload = fetch_json(result["request_url"])
        hits, total = payload["results"], payload["meta"]["count"]
        if not isinstance(hits, list) or type(total) is not int or total < len(hits) or (total and not hits):
            raise ValueError("Inconsistent OpenAlex first-page counts.")
        records = [openalex_record(work, exact=False) for work in hits[:rows]]
        return {**result, "status": "candidates" if records else "not_found", "records": records,
                "limit": rows, "returned": len(records), "total_results": total,
                "truncated": total > len(records)}
    except HTTPError as exc:
        if exc.code == 404 and doi and "seed" not in result:
            return {**result, "status": "seed_not_found" if direction else "not_found",
                    "detail": "No OpenAlex work for this DOI."}
        return service_error(result, exc)
    except (URLError, OSError, HTTPException, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {**result, "status": "error", "detail": str(exc) or type(exc).__name__}


def candidate_preview(result, query):
    summary = {key: result[key] for key in (
        "source", "status", "origin", "reading_status", "retrieved_at", "limit", "returned",
        "total_results", "truncated", "from_date", "to_date", "sort", "direction", "warnings") if key in result}
    summary["preview_only"] = True
    if query:
        summary["query"] = query
    if "seed" in result:
        summary["seed"] = {key: result["seed"][key] for key in ("doi", "openalex_id")}
    summary["records"] = []
    for record in result["records"]:
        compact = {key: record[key] for key in (
            "title", "doi", "openalex_id", "pmid", "pmcid", "id", "source_id", "record_id", "source",
            "year", "publication_date", "arxiv_id", "version", "submitted_date") if record.get(key) is not None}
        authors = record.get("authors")
        if authors:
            compact["first_author"] = authors[0]
        summary["records"].append(compact)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    labels = {"crossref": "Crossref", "openalex": "OpenAlex", "europepmc": "Europe PMC",
              "pubmed": "PubMed", "arxiv": "arXiv"}
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="Public title or bibliographic keywords; returns ranked candidates")
    mode.add_argument("--doi", help="Exact DOI, optionally as a doi.org URL")
    mode.add_argument("--pmcid", help="Europe PMC full text, e.g. PMC4877813")
    mode.add_argument("--pmid", help="Exact PubMed record by numeric identifier")
    mode.add_argument("--arxiv-id", help="arXiv preprint identifier, optionally with a specific version")
    parser.add_argument("--source", choices=labels, default="crossref")
    parser.add_argument("--direction", choices=("references", "citations"),
                        help="With an OpenAlex seed DOI: works it references, or works citing it")
    parser.add_argument("--limit", type=int, help="List records to return (1–20, default 5)")
    parser.add_argument("--from-date", help="Inclusive lower date (YYYY-MM-DD); initial submission for arXiv")
    parser.add_argument("--to-date", help="Inclusive upper date (YYYY-MM-DD); initial submission for arXiv")
    parser.add_argument("--sort", choices=("newest",), help="Order by latest publication date")
    parser.add_argument("--section", help="Europe PMC full-text section title")
    parser.add_argument("--passage-query", "--phrase", help="Words to locate in Europe PMC full text")
    parser.add_argument("--brief", action="store_true", help="Compact metadata for candidate screening")
    args = parser.parse_args(argv)
    options = {"from_date": args.from_date, "to_date": args.to_date, "sort": args.sort}
    if args.pmid is not None and args.source != "pubmed":
        result = {**result_envelope(labels[args.source]), "status": "invalid_input",
                  "detail": "--pmid requires --source pubmed."}
    elif args.arxiv_id is not None and args.source != "arxiv":
        result = {**result_envelope(labels[args.source]), "status": "invalid_input",
                  "detail": "--arxiv-id requires --source arxiv."}
    elif args.doi is not None and args.source in {"pubmed", "arxiv"}:
        result = {**result_envelope(labels[args.source]), "status": "invalid_input",
                  "detail": "Use --pmid for PubMed, --arxiv-id for arXiv, or --query to search this source."}
    elif args.direction and args.source != "openalex":
        result = {**result_envelope(labels[args.source]), "status": "invalid_input",
                  "detail": "--direction requires --source openalex and a seed DOI."}
    elif args.source != "europepmc" and any(x is not None for x in (args.pmcid, args.section, args.passage_query)):
        result = {**result_envelope(labels[args.source]), "status": "invalid_input",
                  "detail": "Full-text passage lookup requires --source europepmc and a PMCID."}
    elif args.source == "openalex":
        result = query_openalex(args.query, args.doi, args.direction, args.limit, **options)
    elif args.source == "europepmc":
        result = query_europepmc(query=args.query, doi=args.doi, pmcid=args.pmcid, section=args.section,
                                 passage_query=args.passage_query, limit=args.limit, **options)
    elif args.source == "pubmed":
        result = query_pubmed(query=args.query, pmid=args.pmid, limit=args.limit, **options)
    elif args.source == "arxiv":
        result = query_arxiv(query=args.query, arxiv_id=args.arxiv_id, limit=args.limit, **options)
    else:
        result = query_crossref(args.query, args.doi, args.limit, **options)
    if args.brief and result["status"] == "candidates":
        result = candidate_preview(result, args.query)
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":") if result.get("preview_only") else None))
    return 0 if result["status"] in ("matched", "candidates", "not_found", "seed_not_found",
                                      "passages", "no_passage", "fulltext_unavailable") else 2


if __name__ == "__main__":
    raise SystemExit(main())
