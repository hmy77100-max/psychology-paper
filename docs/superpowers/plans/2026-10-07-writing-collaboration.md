# Writing craft and on-demand collaboration implementation plan

> **For agentic workers:** Use executing-plans to implement task-by-task. Implementation stays in this session; fresh-context agents are used only for the writing-skills behavioral tests.

**Goal:** Improve precise author-led writing and preserve scoped decisions during optional multi-perspective collaboration.

**Architecture:** Extend existing manuscript-writing and psychology-paper modules with focused manifest resources. Reuse shared authorization, handoff and PROJECT state, without a new state store or autonomous team.

**Tech Stack:** Markdown instructions, JSON manifests, Python unittest and the existing resource loader.

## Global constraints

- Candidate-only manuscripts; no source-data changes, new watchers or installed-cache mutation.
- Default resource budget 12,000 characters; optional preparation stages stay separate.
- Complete original/revised/notes contract, logical units, explicit author decisions and scientific evidence ceiling remain intact.
- Role names are configurable. Visible critic/producer perspectives require the user's call; routine evidence checks and feedback recording do not.
- Record proposal/adoption/implementation/verification/publication separately. Private optimization history is gitignored.

## Task 1: Baseline and executable regression contracts

- [x] Read new log requirements and existing manifests, core resources, state template and tests.
- [x] Confirm approved Humanizer scope and current authorization to optimize; reuse the existing minimal-module design.
- [x] Choose scoped resources over a new module or default multi-agent workflow. No visual design question applies.
- [x] Capture five fresh-context control samples of the same synthetic deadline/reviewer/partial-approval case; record literal failures and passing boundaries.
- [x] Create tests/test_writing_collaboration.py with manifest, content-contract, trigger and resource-budget tests; run `python -m unittest discover -s tests -p test_writing_collaboration.py -v` and observe missing-contract failures.

## Task 2: Minimal implementation

- [x] Add `conditional_loads.prose_diagnostics` -> manuscript-writing/references/prose-diagnostics.md; include diagnosis/repair examples, protective rules, sample-based voice observations and contribution articulation.
- [x] Add `conditional_loads.collaboration` -> psychology-paper/references/collaboration.md; specify role activation, evidence dissent, itemized decisions, existing-state receipt and post-revision verification.
- [x] Wire triggers in both SKILL.md entrypoints. Extend current workflow, style-delta, shared authorization/minimal handoff and existing PROJECT template rather than introducing new stores.
- [x] Preserve upstream Academic Humanizer license in THIRD_PARTY_NOTICES.md and identify adapted sections. Keep source examples synthetic.
- [x] Run targeted tests until green. Structural string assertions are contracts, not proof of model behavior.

## Task 3: Verification and handoff

- [x] Repeat five fresh-context samples with the added guidance; manually score state classification, author voice, evidence protection and truthful write status.
- [x] Run a focused application scenario with the complete loaded resources, not only abbreviated micro-test context.
- [x] Run `python -m unittest discover -s tests -v`, resource-size checks and `git diff --check`.
- [x] Review actual changes for privacy, source/data safety, role autonomy and contradictory instructions; fix and rerun affected checks.
- [x] Record outcomes and limits in docs/validation/writing-collaboration.md and update CHANGELOG.md under Unreleased.
- [x] Update private optimization status and report local implementation, tests, publication and installation separately. Do not claim reduced token costs or long-run immunity from these tests.

## Authoring checklist

- [x] RED observed, literal baseline recorded, failure type identified.
- [x] Existing skill names/frontmatter retained; description triggers and conditional routing checked.
- [x] Positive recipes, concrete example and quick comparison table; no invented data or private narrative.
- [x] Supporting reference resources reachable and only conditionally loaded.
- [x] Five control/treatment samples manually reviewed; same-context limitations stated.
- [x] Full-context pressure scenario and full automated suite verified.
- [x] No unrelated rules/roles or terminology changes; state receipt distinguishes planned from written.
- [x] Release/installation remain separate; no public publish in this request.
