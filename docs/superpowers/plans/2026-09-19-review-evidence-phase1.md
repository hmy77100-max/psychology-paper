# Review Evidence Phase 1 Implementation Plan

> For agentic workers: use executing-plans for inline implementation. Use writing-skills behavioral scenarios for the Skill changes.

**Goal:** Implement internal review responsibilities and targeted evidence verification without changing the existing short route.

**Architecture:** Extend evidence-audit's canonical manifest with a small always-loaded workflow and conditional evidence guidance. Keep scientific judgment with the model; add a read-only provenance-record checker and a narrow read-only audit guard.

**Tech Stack:** Existing Markdown Skills, JSON manifests and scenarios, Python standard library, unittest.

## Global Constraints

- Implement phases 1 and 2 of the approved sequence; document phases 3 through 6 without claiming completion.
- Never modify user manuscripts/data or installed plugin cache.
- Reuse project context; no mandatory new project or journal workflow.
- No new dependencies, browsing service, persistent memory format or semantic rules engine.
- Keep 12,000-character resource ceiling and existing named-analysis marker guard.

## Task 1: Baseline and failing tests

- [x] Read current behavior and run the original full suite.
- [x] Sample existing Skill behavior on source-version ambiguity and review-to-edit transition cases.
- [x] Add tests/test_review_evidence.py for manifest isolation/budget, read-only audit guard, evidence-note provenance/partial access/invalid inputs and CLI no-write behavior.
- [x] Add tests/scenarios/review-evidence.json using existing scenario schema and cross-design manual rubrics.
- [x] Run `python -X utf8 -m unittest discover -s tests -p test_review_evidence.py -v`; verify failures are missing functionality, not syntax/environment errors.

## Task 2: Minimal implementation

Files: scripts/review_evidence.py; scripts/workflow_guards.py; skills/evidence-audit/SKILL.md; manifest.yaml; static/core/review-workflow.md; references/external-evidence.md; references/evidence-note.md; references/audit-report-schema.md; static/core/audit-principles.md.

- [x] Implement `validate_record(record) -> dict` with `record_complete`, `errors`, `limitations`, `scientific_verification: false`. Check fields and source IDs/access/locators; never judge scientific truth. CLI accepts `--record PATH` or `--record -` for stdin and does not write files.
- [x] For `task == 'evidence_audit'`, return `ProjectModeDecision('READ_ONLY_AUDIT', False)` before project-mode checks. Preserve all other guard behavior.
- [x] Add internal responsibility/context/stop guidance as one small always-load resource; detailed verification and note contract only under `conditional_loads.external_evidence`.
- [x] Update report to distinguish facts/inference, include evidence-backed recommendations, coverage and strengths when useful, respect requested risk filtering and stop at feedback.
- [x] Clarify targeted audit lookup versus deferred literature management in router docs; do not introduce new routing or execution modules.
- [x] Run focused tests; then sample fresh-agent behavior with the revised Skill on the same scenarios.

## Task 3: Review and delivery

- [x] Run complete unittest suite, official plugin/Skill validators, and `git diff --check`.
- [x] Review changed runtime resources for conflicting instructions, overloading, unwanted file writes and ungrounded success claims.
- [x] Update README and record actual validation outcomes plus remaining limits in docs/validation/review-evidence-phase1.md.
- [x] Commit only intended source, tests and documentation with public noreply identity. Push development branch and create a draft PR; leave main and installed plugin unchanged.

Delivery: draft PR https://github.com/hmy77100-max/psychology-paper/pull/1. Main and the installed plugin are unchanged.
