# Author-led workflow 0.4.0

## Scope

Implements the thirteen recorded directions as bounded plugin-source changes. No private case log, manuscript, author identities or source data belongs in this public change. The case-review requirement was satisfied before implementation; it is not a new runtime module or evidence that post-change agent behavior has been validated.

| Direction | Implementation | Validation boundary |
| --- | --- | --- |
| 001: full original/revision/notes and free replies | Candidate file/hash/span checks; semantic-intent decision interface; natural-language and style-delta guidance | Mechanical completeness is checked. Interpreting real author language remains an agent responsibility. |
| 002: writing dependency and logical units | Function/closure/spans, stage CLI, body → abstract → keywords, dependency invalidation, explicit exceptions | Tests verify state transitions, not quality of chosen argument boundaries. |
| 003: repeated context/collaboration overhead | Selector inventory, complete cost diagnostic, canonical deduplication, hash metadata; extraction reuse and conditional delegation/wait guidance | No measured token-saving percentage or enforced host polling scheduler. |
| 004: review coverage | Current-manuscript-first full/deep review | See review-depth validation record. |
| 005: four review deliverables | Value, applicable sections, competing explanations, prioritized repair choices | Resource/scenario tests; no claimed improvement in acceptance rate. |
| 006: case before implementation | Prior case findings retained as rationale; synthetic failing regressions before new behavior | Real case material stays private; previous case output is not post-change proof. |
| 007: independent scientific judgment | Approval/history cannot override current manuscript or fill omitted content | Instructions/scenarios, not a truth classifier. |
| 008: whole-revision readiness | Actual standard state, source, approved profile, contribution and counted-baseline preflight | Does not make model-authored metadata scientifically true. |
| 009: keywords route | Exact manifest selector and section resource | Real loader regression across focused routes. |
| 010: external tools and reuse | Minimal disclosure, source/access/version records, reusable extraction, available-tools-only policy | No new browser service or unrestricted private-data upload. |
| 011: useful literature in the argument | Claim/support/directness/incremental-value/ceiling/deletion-impact filter; introduction support priority; reuse search authorization | Search and scientific appraisal are agent work, not automatic citation approval. |
| 012: contribution recommendations and author view | Journal trajectory plus direct predecessors; original reasoning; bounded angles before outline | Author selects, combines or replaces the direction. |
| 013: paired language updates | Observed Chinese/English hashes, unit ID, standing authorization, candidate-only English | Freshness is tested; translation quality and filesystem monitoring are not claimed. |

## Regression sequence

Baseline: 113 tests passed, including the earlier uncommitted review-depth implementation. New tests first failed on missing checkers/selectors, incomplete loader diagnostics and candidate-format enforcement. Subsequent failing cases exposed and drove fixes for stale counted baselines, retained-versus-adopted decisions, shared illegal state, missing plans, stage-entry checks, abstract-to-keyword invalidation and stale/missing English files.

The suite includes actual CLI/file checks in isolated temporary directories, source immutability assertions and 132 task/language/section loader combinations. The retained original source is never overwritten. Duplicate approval is idempotent; partial/advance/defer/reject never silently approve; accepted counted changes require a refreshed adopted baseline.

Commands: `python -X utf8 -m unittest discover -s tests -v`, official Skill validators for all five entrypoints, official standalone plugin validator, and `git diff --check`. GitHub CI runs the regression suite on Windows and Linux using Python 3.13.

Local release check on 2026-09-30: **141 tests passed**; all five official Skill validators and the official plugin validator passed; whitespace check passed. Shared authorization was reconciled with the checker: unqualified continuation is not adoption unless the author explicitly approved a different shorthand mapping. Invalid candidates cannot be approved or advanced through the decision checker.

The default 12,000-character resource ceiling is unchanged. Metadata inspection returns complete selected costs without dumping instruction bodies; it is not a substitute for reading selected instructions. Freshly loaded resources and source snapshots must still be checked after version changes.

## Outstanding behavioral acceptance

Scenario files are runnable prompts/rubrics for future fresh-session evaluation, not saved model runs. This release does not claim that free-language intent recognition, scientific novelty judgment, translation accuracy, literary style or long-session adherence has been experimentally validated. Apply the scenarios in a fresh task with the updated installed plugin and grade the actual outputs, especially multi-unit partial adoption and literature usefulness.

Source publication does not refresh an installed Codex plugin cache. Installation/update and the next fresh-session check are separate deployment steps. No watcher or source-document writer is installed by this change.
