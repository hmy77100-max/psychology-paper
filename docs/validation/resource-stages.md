# Resource stage validation — 2026-10-07

This document records the pre-release development snapshot for 0.5.0. Release and installation occur separately; statements below about an unchanged installation describe that snapshot, not a live version query.

## Scope and status

Local implementation only. No publication, installation-cache refresh, manuscript/data edits, new dependencies or increased character limit. Existing uncommitted writing/collaboration changes remain intact. The stage helper is part of the existing loader, not a new academic module.

## Reproduced boundary

The installed `0.4.0+codex.20260930095838` loader's read-only `--describe` confirms that manuscript-writing plus `bilingual_sync`, `revision_checks` and `literature_support` requires **14,493** instruction-body characters against **12,000**. Its manifest SHA256 is `43b6bdb76cc789aae49baf8bfbf16f82199b79174a9dc9d17cbb6db3dba74fbd`.

Core costs 4,490; the three supplements cost 1,648, 5,450 and 2,905. The final supplement crosses the cumulative ceiling; it is not individually oversized. Three ordinary separate loads would repeat core twice, totaling 23,473 body characters. The new staged size fixture covers the same 14,493-character union once. This fixture reproduces exact sizes, not the historical instructional text or historical exit-code behavior.

The local development version includes earlier approved writing changes, so its current core is 4,856, not 4,490. Current measured plans:

| Route | Stage body sizes | Unique body total |
| --- | --- | --- |
| Three writing supplements | 4,856 / 1,648 / 5,450 / 2,905 | 14,859 |
| Full manuscript, Chinese introduction, candidate format, literature, revision checks | 4,856 / 2,576 / 2,267 / 2,905 / 5,450 | 18,054 |
| Router collaboration, authorization, state rules | 1,709 / 4,608 / 4,557 / 4,072 | 14,946 |
| Empirical survey full audit, all risks, methods, quality, external evidence | 2,286 / 3,233 / 3,620 / 4,732 / 2,888 | 16,759 |

All listed stages fit the unchanged ceiling. These are selected route regressions, not a claim that every possible combination or every future indivisible resource group fits. The previous 132-combination check covered writing axes plus candidate format and prose diagnostics, not all supplemental paths.

## Automated evidence

Before implementation, eight stage tests failed because the staged API was absent. A later subprocess regression also exposed distinct exception classes when the loader ran as a script and was imported by its helper; the CLI now classifies both consistently.

- `python -X utf8 -m unittest discover -s tests -q`: **166 tests passed**, including **14** stage tests.
- `git diff --check`: passed; Windows line-ending normalization warnings are not whitespace failures.
- Exact-size synthetic regression and actual local manifests preserve the full selected union with canonical path deduplication.
- Per-stage content equals the complete current source text and its recorded character count/hash; no slicing or truncation is performed by the loader.
- Core and conditional multifile groups over 12,000 fail rather than being split arbitrarily.
- Missing predecessors, unconfirmed delivery, duplicate/unknown stages, malformed receipts, blank output references and stale plan/context/root/manifest/resources/selection cannot satisfy coverage.
- CLI tests cover metadata-only planning, argument mistakes, selector resolution, capacity, receipt failures, mode conflicts and attempts to raise the staged limit.
- A full subprocess journey reads every stage using temporary test attestations, finishes coverage, then demonstrates incomplete coverage after a receipt is removed. Chinese temporary paths work. The journey confirms the selected manifest and loader source remain unchanged; the implementation contains no file-write operation.

## Interpretation and limits

The 12,000 limit measures instruction bodies, not labels, JSON overhead, tokens or model context size. Plans and receipts add overhead; no token-billing savings have been measured. The tests fabricate explicitly marked test attestations to exercise the protocol, not to claim actual model understanding.

Real callers must read complete untruncated output before acknowledging it, using the actual tool-output reference. The checker validates metadata consistency, not the truth of that attestation or the existence of that reference. It does not infer which selectors a research task requires, verify scientific quality, approve author choices or authorize manuscript changes.

Old ordinary loads have no staged receipt and cannot silently become acknowledged stages. Changed selection, files, plugin root or lost read context requires a fresh plan and complete relevant reads. Within a completed unchanged plan, reuse instructions rather than repeating the protocol for every paragraph. Ordinary small tasks retain the direct-load route.

Entry rules now tell writing, review and routing callers how to use stages and classify failures. Sustained live-agent compliance and real token savings still need observation after a separately authorized release/install; local tests do not establish either.
