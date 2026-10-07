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
- Use `conditional_loads.efficient_execution` when coordinating resource reuse or external tools.
- Use `conditional_loads.collaboration` when the user invokes a collaboration perspective, gives mixed feedback/decisions, or a revision milestone requires checking cumulative decisions. Load only the professional module needed for the actual issue; roles are not new modules or automatic independent agents.

Do not open child resource paths directly, infer a similar path, or enumerate directories. Keep the default character budget and never load every conditional branch for convenience.

For multiple preparation groups or uncertain capacity, use the same loader with `--plan --context-id <fresh-read-context>` and all required selectors in intended preparation order. It emits metadata only: core once, task axes, then whole conditional/shared groups with canonical deduplication. Keep that selector list and context ID for `--stage <id>` calls. Fully read each stage before explicitly confirming its `receipt_template` (`read_complete: true` and the actual tool `output_ref`) in a task-local JSON list; pass that list with `--receipts <path>` for subsequent stages and `--check-coverage` before dependent delivery. Never auto-confirm output success or truncated text. Receipts are caller attestations, not proof of comprehension, complete task selection or scientific verification. They bind plan, plugin root, manifest and content hashes; start fresh after context loss or changes. Do not put them in author-decision state or require user replies for them. Reuse the completed unchanged plan within this read context, not a new receipt cycle for every paragraph.

Stop any failed invocation. `ARGUMENT_ERROR` or `RESOLUTION_ERROR` requires correcting the exact invocation/resource defect, not guessing selectors. `BUDGET_EXCEEDED` permits metadata planning of the same necessary groups, not a raised limit, omitted rules or arbitrary text slicing; an oversized indivisible stage requires resource repair. `READ_RECEIPT_INVALID` requires inspecting the missing/stale receipt, then completing missing reads or replanning in the current context. Failed/metadata-only loads never count as complete. Keep ordinary bounded single loads for simple tasks; staging is not mandatory ceremony.

## Route

Read-only manuscript review takes the short route directly to `evidence-audit`, including full-manuscript scope. It does not require journal positioning or project initialization. When using the guard for this intent, pass `--task evidence_audit`. Targeted source lookup inside that review is not the deferred literature-management workflow.

1. Identify task, scope, language, permission, authoritative source, and whether project mode is needed. Map the user's natural language to controlled task and scope labels, then run `workflow_guards.py project-mode`. If it returns `PROJECT_MODE_CONFIRMATION_REQUIRED`, ask whether to enter project mode before any full-manuscript candidate is drafted.
2. Check whether the apparent local change carries cross-section evidence impact.
3. Choose exactly one `PRIMARY_MODULE`; include only necessary `SUPPORT_MODULES`.
4. Pass the minimal packet defined by the shared handoff schema.
5. Stop at the applicable approval, authority, evidence, or stage boundary.

For journal-directed whole-manuscript work: journal confirmation → evidence-bounded contribution recommendations → author's own view and chosen direction → logical-unit outline → body → abstract → keywords. Keep read-only review on its short route. A prior agreed contribution can be reused unless new evidence changes it. Literature support belongs to manuscript-writing's focused support resource; uncertain sources/claims can route to evidence-audit. Do not demand repeated search approval within an already authorized scope.

## Approval and state

Discussion, approval, and write permission are separate. Update project state only after the user explicitly approves the information being recorded. Keep rejected candidates and full chat history out of state.

Default to constructive work with routine evidence checking and feedback recording. Visible critic or producer perspectives require the user's explicit call; there is no four-role rotation. Use configured role names, not a global nickname. Apply item-level approval and supersession in the existing authoritative state; return confirmed items, genuinely open items and the verified save location. A pending candidate is not an intentional hold, and approved direction is not approved wording. Resume from cumulative effective decisions, not only the latest message.

## Current stage boundary

Route statistical reconstruction, recalculation, field verification, and source comparison to `analysis-adapter`. The adapter may create approved analysis-state files and reproducible analysis outputs, but it cannot modify source data or manuscript files. Literature management, manuscript patching, reviewer-response workflows, and submission audits remain unavailable until their later modules are implemented.

Targeted literature support, contribution planning and task-scoped bilingual candidates are available inside existing modules; they are not a new literature database, file watcher or manuscript patcher.
