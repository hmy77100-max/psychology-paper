# Current-manuscript authority and review depth

Implemented 2026-09-20 for OPT-004, OPT-005 and OPT-007 after OPT-006's manuscript case review. No manuscript facts, journal thresholds or personal data were added to runtime rules.

## Changes

- Standalone review uses the submitted completed manuscript without a profile prerequisite; project review uses the current approved manuscript. Older profiles cannot supply missing report content or resurrect removed claims. Approval is not scientific validation.
- Ordinary-language screening, full review, deep re-review and incremental verification remain distinct. Whole-paper review defaults to full depth unless explicitly narrowed. An unchanged file does not block requested deeper review.
- Full review requires contribution assessment, section-level examination, competing explanations and prioritized advice. The entrypoint carries detailed duties; the full scope loads a compact completion reminder. Local/section scopes do not load that reminder.
- Existing issue IDs, source boundaries and closure rules remain. No quota, mandatory agents, new project memory, automatic writing or reanalysis.

## Verification performed

1. Added `tests/test_review_depth.py` before production edits. Baseline: five tests ran; four test methods had failures (12 failing subtests/assertions), budget test passed. Missing authority safeguards, full-scope completion resource and deep-versus-incremental distinction were observed.
2. Added rules and tested the real canonical loader. Budget regressions exposed oversized combinations. Compressed duplicated wording and kept the existing 12,000-character limit; did not relax tests or increase the limit.
3. Final complete suite: **113 tests passed** (`python -X utf8 -m unittest discover -s tests -v`). This includes five added resource regressions and validation of the eight new scenario records by the existing scenario-contract tests.
4. Canonical loader character totals: mixed-design full methods 10,556; full quality 8,440; full external/source-authority 11,933. Conditional contribution/advice resources remain stage-specific rather than all loaded together.
5. Official skill validator: `Skill is valid!`; official plugin validator: passed. Bundled Python initially lacked PyYAML; reran with the existing system Python 3.13/PyYAML 6.0.3, without installing dependencies.
6. Git whitespace check passed. Changes confined to plugin resources, tests, README and local optimization/validation records.

## Behavioral acceptance still to run

`tests/scenarios/review-depth.json` contains eight reproducible synthetic prompts and rubrics: stale profile, background-only method detail, approved text with a scientific error, unchanged-paper deep review, bounded incremental check, low-defect passage, unassembled approved fragments, and qualitative screening.

The automated tests check resource delivery, declared safeguards, budgets and scenario structure. They do **not** run a fresh model against these prompts or grade academic reasoning. For live acceptance, run each in a fresh context with the modified entrypoint and manifest-selected resources, retain the response, and assess against its required/forbidden actions and manual rubric. Excerpts must not be treated as inspected full manuscripts. Cross-paper consistency and installed fresh-session behavior remain unverified.

The earlier real-paper review demonstrated a desired output and execution shortcomings in the prior response; it was performed before this implementation and is not post-change behavioral proof.

## Release state

Historical snapshot below refers to the initial review-only change. The 0.4.0 author-led-workflow release incorporates this preserved work with additional regression coverage; see `author-led-workflow.md` for the broader validation boundaries. It still does not imply an installed-cache upgrade.

Local source implementation and automated validation complete. No commit, GitHub merge, release/version bump or installation-cache update in this change. The currently installed 0.3.0 cache is unchanged. Do not report this source work as an installed upgrade.
