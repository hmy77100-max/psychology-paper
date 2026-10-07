---
name: manuscript-writing
description: Draft or revise Chinese and English psychology manuscript sections as evidence-bounded, journal-aware, TXT-ready candidates; Stage 1A never writes source documents.
---

# Manuscript Writing

Use this skill after the task scope, authoritative source, and evidence ceiling are known. It produces candidates for user review; Stage 1A never edits manuscript files.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill manuscript-writing`. The loader includes `always_load` automatically. Add exactly one `axes.task.*`, one `axes.language.*`, and one `axes.section.*` selector. Add `conditional_loads.confirmed_style_delta` only when an approved user-specific style file exists, and add a named `shared_loads.*` selector only when the current writing task requires it.

Do not open child resource paths directly, infer a similar path, or enumerate directories. Keep the default character budget and never load unrelated sections, languages, or task modes.

For multiple preparation groups or uncertain capacity, use the same loader with `--plan --context-id <fresh-read-context>` and all required selectors in intended preparation order. It emits metadata only: core once, task axes, then whole conditional/shared groups with canonical deduplication. Keep that selector list and context ID for `--stage <id>` calls. Fully read each stage before explicitly confirming its `receipt_template` (`read_complete: true` and the actual tool `output_ref`) in a task-local JSON list; pass that list with `--receipts <path>` for subsequent stages and `--check-coverage` before dependent delivery. Never auto-confirm output success or truncated text. Receipts are caller attestations, not proof of comprehension, complete task selection or scientific verification. They bind plan, plugin root, manifest and content hashes; start fresh after context loss or changes. Do not put them in author-decision state or require user replies for them. Reuse the completed unchanged plan within this read context, not a new receipt cycle for every paragraph.

Stop any failed invocation. `ARGUMENT_ERROR` or `RESOLUTION_ERROR` requires correcting the exact invocation/resource defect, not guessing selectors. `BUDGET_EXCEEDED` permits metadata planning of the same necessary groups, not a raised limit, omitted rules or arbitrary text slicing; an oversized indivisible stage requires resource repair. `READ_RECEIPT_INVALID` requires inspecting the missing/stale receipt, then completing missing reads or replanning in the current context. Failed/metadata-only loads never count as complete. Keep ordinary bounded single loads for simple tasks; staging is not mandatory ceremony.

Load a confirmed journal profile only when it exists and matters to the requested section.

Use `conditional_loads.prose_diagnostics` when the author requests less formulaic writing, supplies a voice sample, or a concrete prose problem remains after ordinary revision. It supplements, not replaces, the logical-unit and candidate contracts. Plan its load separately from literature, bilingual and revision-check preparation; reuse unchanged instructions.

Use `conditional_loads.literature_support` for citation-dependent argument work, `conditional_loads.bilingual_sync` for authorized paired updates, and `conditional_loads.revision_checks` before first candidate validation/project preflight. Load distinct preparation stages separately; never combine every optional resource. Use `--list-selectors` for exact values and `--describe` to plan costs before loading. Reuse already fully read instructions while their hashes and task remain unchanged; do not repeatedly reload for every unit. Inspection options do not replace reading selected instructions completely.

## Workflow

1. Read the exact source passage and enough context to determine its function.
2. Preserve approved statistics, citations, terminology, and evidence boundaries.
3. For full-manuscript work, run `revision_check.py preflight` against the actual standard project state, approved journal profile, source version and adopted counted baseline. Confirm the author's contribution direction before the outline. `workflow_guards.py body-budget` is arithmetic only, not full-mode permission. Never invent a journal-independent limit.
4. Check whether the request changes a cross-section scientific claim; if so, stop and request an evidence audit rather than expanding the claim.
5. Draft in the required TXT-ready order.
6. Before creating a new writing artifact, run `candidate_ids.py` with all candidate IDs already issued in the task or project and register the returned ID. Reuse an ID only when revising that same artifact.
7. Verify meaning, numbers, terms, source version, and projected body length. Run `revision_check.py candidate` on the actual three-part artifact and full logical-unit extraction before delivery. Missing original, wrong order, truncated source or stale hash blocks delivery; repair it first.
   Match every applicable effective author requirement to the candidate location and verification result; distinguish checked, pending and out-of-scope dependencies. A discussion or structural checker pass alone is not semantic verification. Keep Chinese/English and cross-section dependencies pending until their actual artifacts have been checked.
8. Interpret the author's unrestricted language in context. Do not prescribe fixed reply commands or require candidate IDs when the referent is clear. In full mode, run `revision_check.py decision` before recording acceptance. Partial adoption creates a mixed candidate; “next” alone does not approve. Preserve local preferences and route explicitly approved reusable preferences to style-delta. Do not write the source file.

Do not add facts, data, statistical results, citations, methods, or author decisions. A user-approved candidate may be recorded in project state, but manuscript mutation is deferred to Stage 1B.
