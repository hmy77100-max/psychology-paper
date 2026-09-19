---
name: psychology-paper
description: Route multi-step psychology manuscript work across journal fit, evidence auditing, bilingual writing, and reproducible statistical-analysis support while preserving user approval and source authority.
---

# Psychology Paper Router

Use this skill when a psychology manuscript request may require journal positioning, evidence review, writing, or long-running project state. For a clearly isolated language edit, route directly without forcing full project setup.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill psychology-paper`. The loader includes `always_load` automatically. Add only the selectors required by the current route:

- `--select conditional_loads.project_mode` for full-manuscript, reanalysis, review-response, or submission work.
- `--select conditional_loads.ambiguous_route` when the primary module is unclear.
- `--select conditional_loads.module_handoff` when another module is required.
- `--select conditional_loads.recovery` when source, scope, or permission is unresolved.
- Add a named `shared_loads.*` selector only when that shared rule is required.

Do not open child resource paths directly, infer a similar path, or enumerate directories. A loader error is a plugin-integrity failure; stop this plugin invocation and report the bounded error. Keep the default character budget and never load every conditional branch for convenience.

## Route

Read-only manuscript review takes the short route directly to `evidence-audit`, including full-manuscript scope. It does not require journal positioning or project initialization. When using the guard for this intent, pass `--task evidence_audit`. Targeted source lookup inside that review is not the deferred literature-management workflow.

1. Identify task, scope, language, permission, authoritative source, and whether project mode is needed. Map the user's natural language to controlled task and scope labels, then run `workflow_guards.py project-mode`. If it returns `PROJECT_MODE_CONFIRMATION_REQUIRED`, ask whether to enter project mode before any full-manuscript candidate is drafted.
2. Check whether the apparent local change carries cross-section evidence impact.
3. Choose exactly one `PRIMARY_MODULE`; include only necessary `SUPPORT_MODULES`.
4. Pass the minimal packet defined by the shared handoff schema.
5. Stop at the applicable approval, authority, evidence, or stage boundary.

## Approval and state

Discussion, approval, and write permission are separate. Update project state only after the user explicitly approves the information being recorded. Keep rejected candidates and full chat history out of state.

## Current stage boundary

Route statistical reconstruction, recalculation, field verification, and source comparison to `analysis-adapter`. The adapter may create approved analysis-state files and reproducible analysis outputs, but it cannot modify source data or manuscript files. Literature management, manuscript patching, reviewer-response workflows, and submission audits remain unavailable until their later modules are implemented.
