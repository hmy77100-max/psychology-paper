---
name: manuscript-writing
description: Draft or revise Chinese and English psychology manuscript sections as evidence-bounded, journal-aware, TXT-ready candidates; Stage 1A never writes source documents.
---

# Manuscript Writing

Use this skill after the task scope, authoritative source, and evidence ceiling are known. It produces candidates for user review; Stage 1A never edits manuscript files.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill manuscript-writing`. The loader includes `always_load` automatically. Add exactly one `axes.task.*`, one `axes.language.*`, and one `axes.section.*` selector. Add `conditional_loads.confirmed_style_delta` only when an approved user-specific style file exists, and add a named `shared_loads.*` selector only when the current writing task requires it.

Do not open child resource paths directly, infer a similar path, or enumerate directories. A loader error is a plugin-integrity failure; stop this plugin invocation and report the bounded error. Keep the default character budget and never load unrelated sections, languages, or task modes.

Load a confirmed journal profile only when it exists and matters to the requested section.

Use `conditional_loads.literature_support` for citation-dependent argument work, `conditional_loads.bilingual_sync` for authorized paired updates, and `conditional_loads.revision_checks` before first candidate validation/project preflight. Load distinct preparation stages separately; never combine every optional resource. Use `--list-selectors` for exact values and `--describe` to plan costs before loading. Reuse already fully read instructions while their hashes and task remain unchanged; do not repeatedly reload for every unit. Inspection options do not replace reading selected instructions completely.

## Workflow

1. Read the exact source passage and enough context to determine its function.
2. Preserve approved statistics, citations, terminology, and evidence boundaries.
3. For full-manuscript work, run `revision_check.py preflight` against the actual standard project state, approved journal profile, source version and adopted counted baseline. Confirm the author's contribution direction before the outline. `workflow_guards.py body-budget` is arithmetic only, not full-mode permission. Never invent a journal-independent limit.
4. Check whether the request changes a cross-section scientific claim; if so, stop and request an evidence audit rather than expanding the claim.
5. Draft in the required TXT-ready order.
6. Before creating a new writing artifact, run `candidate_ids.py` with all candidate IDs already issued in the task or project and register the returned ID. Reuse an ID only when revising that same artifact.
7. Verify meaning, numbers, terms, source version, and projected body length. Run `revision_check.py candidate` on the actual three-part artifact and full logical-unit extraction before delivery. Missing original, wrong order, truncated source or stale hash blocks delivery; repair it first.
8. Interpret the author's unrestricted language in context. Do not prescribe fixed reply commands or require candidate IDs when the referent is clear. In full mode, run `revision_check.py decision` before recording acceptance. Partial adoption creates a mixed candidate; “next” alone does not approve. Preserve local preferences and route explicitly approved reusable preferences to style-delta. Do not write the source file.

Do not add facts, data, statistical results, citations, methods, or author decisions. A user-approved candidate may be recorded in project state, but manuscript mutation is deferred to Stage 1B.
