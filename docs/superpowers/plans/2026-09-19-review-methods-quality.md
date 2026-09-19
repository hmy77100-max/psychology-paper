# Review Methods and Quality Implementation Plan

**Goal:** Implement approved steps 3 and 6 inside evidence-audit. Steps 4 and 5 remain deferred.

**Architecture:** Add conditionally loaded methods and quality guidance; reuse existing design fragments. One model-maintained issue record can stay in conversation. An optional read-only checker validates record consistency, never scientific correctness or semantic duplication. No new agents, project initialization, journal positioning, analysis execution or automatic persistence.

**Scope:** Extend the existing draft PR. Preserve the short route, model freedom to recommend, author adoption, source authority and the 12,000-character per-load ceiling.

## Task 1: Establish failing coverage

- [x] Run original 90-test baseline and sample old behavior for clustered units, resolved/held issues and conflicting analysis identities.
- [x] Add `tests/test_review_quality.py`: valid standalone records; IDs; model classifications; missing basis; hold/resolution distinction; reopen evidence; duplicate aliases; conflicting alias statuses; malformed input; no-write CLI; conditional resource loading/budget.
- [x] Add cross-design and repeat-review fixtures in `tests/scenarios/review-methods-quality.json` before editing Skill rules.
- [x] Run focused tests and observe missing helper/selectors fail.

## Task 2: Implement methods and quality

- [x] Add `conditional_loads.methods_review` and `conditional_loads.quality_review` to the existing manifest. Methods guidance traces question to operationalization, units, model and claim; distinguishes demonstrated error, reporting gap, unresolved check, bounded limitation and author choice.
- [x] Quality guidance matches issues by model-judged claim/location/analysis identity, combines duplicates, investigates conflicts, records resolution basis and reopens only on identified new evidence/context. Held is not resolved; intentional holds are not repeatedly nagged.
- [x] Add `scripts/review_quality.py`: `validate_review(record) -> dict` checks structure, controlled labels, IDs, duplicate links, resolution/hold/reopening basis; returns `record_complete`, `scientific_verification=false`, errors and limitations. `--record PATH|-` reads JSON only. It cannot detect semantic duplicates, decide resolution or compare papers.
- [x] Update entry to load methods during scientific review and quality before delivery/review updates. Select focused groups per stage; reuse already loaded content, never load every resource together.
- [x] Amend only applicable design fragments where a gap is concrete. Avoid duplicating general methods rules across all fragments.

## Task 3: Verify and deliver

- [x] Run focused and full suites, plugin/changed-Skill validation and diff checks.
- [x] Fresh-agent synthetic scenario test of revised rules; inspect responses and disclose limitations.
- [x] Document baseline/final observations and remaining real-manuscript limits. Update README and roadmap status; no acceptance-rate claim.
- [ ] Commit and push to current development branch; update existing draft PR title/body around combined scope. Keep main and installed plugin unchanged.
