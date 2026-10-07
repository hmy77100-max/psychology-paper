# Resource stages implementation plan

> **For agentic workers:** Execute inline with test-driven-development; preserve existing uncommitted writing/collaboration work.

**Goal:** Load complete required instruction groups within the unchanged budget without repeating acknowledged core resources.

**Architecture:** A read-only stage planner delegates resolution to the existing authoritative manifest resolver. Core, selected axes, and individually selected conditional/shared groups form deterministic stages. Same-context read receipts allow later stages, and a coverage check distinguishes acknowledgement from mere delivery.

**Tech Stack:** Python standard library, Markdown entrypoints, unittest.

## Constraints

- 12,000 characters per stage, no arbitrary text slicing, no raised budget.
- No source manuscript/data/state writes, no dependency installation, no public release or installed-cache change.
- Receipts are caller attestations, not proof of comprehension; delivery/describe never imply read completion.
- Context, plan, root, manifest and resource hashes are bound; incomplete/stale/unknown receipts fail closed.

## Task 1 — Regression first

- [x] Add tests/test_resource_stages.py: exact 14,493 synthetic size baseline plus actual current combination, stage coverage/dedup, stale content/manifest/context/root, dependencies, malformed receipts, oversized indivisible groups, CLI error types and real paths.
- [x] Run `python -X utf8 -m unittest discover -s tests -p test_resource_stages.py -v`; observe missing stage functionality before implementation.

## Task 2 — Minimal read-only stage API

- [x] Add scripts/resource_stages.py with build_plan, load_stage and check_coverage. Resource paths resolve only through load_skill_resources; no traversal or fallback.
- [x] Extend load_skill_resources.py CLI with mutually exclusive --plan / --stage / --check-coverage and explicit --context-id / --receipts. Existing default load stays fail-closed.
- [x] Stage output provides content and read_complete=false receipt template. Complete receipts need explicit caller confirmation and output_ref; later stages require acknowledged predecessors. Coverage returns INCOMPLETE until all stages acknowledged.
- [x] Wire bounded help into existing skill entrypoints; do not add a new instruction skill/module or unconditional full-history loading.

## Task 3 — Verify and report

- [x] Targeted tests green, all existing tests green, exact installed-version read-only --describe comparison and current-path coverage costs recorded.
- [x] Add an integration journey for all stages and unchanged source files; test selectors/payload/receipt failures before content output.
- [x] Update README, Unreleased notes and docs/validation/resource-stages.md with limits and exact counts.
- [x] Update private log and report local vs released/installed status separately.
