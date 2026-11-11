---
name: psychology-paper
description: Route multi-step psychology manuscript work across journal fit, evidence auditing, bilingual writing, and reproducible statistical-analysis support while preserving user approval and source authority.
---

# Psychology Paper Router

Use this skill when a psychology manuscript request may require journal positioning, evidence review, writing, or long-running project state. For a clearly isolated language edit, route directly without forcing full project setup.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill psychology-paper`. The loader includes the shared author-led short core in `always_load`; direct writing uses the same resource. Add only the selectors required by the current route:

- `--select conditional_loads.project_mode` for full-manuscript, reanalysis, review-response, or submission work.
- `--select conditional_loads.ambiguous_route` when the primary module is unclear.
- `--select conditional_loads.module_handoff` when another module is required.
- `--select conditional_loads.recovery` when source, scope, or permission is unresolved.
- Add a named `shared_loads.*` selector only when that shared rule is required.
- Use `conditional_loads.efficient_execution` when coordinating resource reuse or external tools.
- Use `conditional_loads.collaboration` when the user invokes a collaboration perspective, gives mixed feedback/decisions, or a revision milestone requires checking cumulative decisions. Load only the professional module needed for the actual issue; roles are not new modules or automatic independent agents.

Do not open child resource paths directly, infer a similar path, or enumerate directories. Keep the default character budget and never load every conditional branch for convenience.

Use ordinary bounded loads for simple tasks; staging is not mandatory. For multiple preparation groups or uncertain capacity, use `--plan --context-id <fresh-read-context>` with the needed selectors; metadata is not a completed read. Read each `--stage <id>` fully, then record its receipt_template with `read_complete: true` and the actual `output_ref`. Pass the explicit JSON list through `--receipts <path>` and check `--check-coverage` before dependent delivery.

Reuse valid receipts for unchanged resources across modules in the same read context; keep the planned selectors for each stage. Start fresh after context loss or changed resources. Never attest truncated output, infer a read from tool success, or treat a receipt as understanding or scientific verification. No per-paragraph receipt cycle or author approval is needed.

Stop a failed invocation. Correct exact ARGUMENT_ERROR/RESOLUTION_ERROR defects; do not guess selectors. BUDGET_EXCEEDED permits planning the same necessary groups, not raising the budget or omitting/truncating rules. An oversized whole stage needs resource repair. For READ_RECEIPT_INVALID, inspect the stale/missing record and complete the required reads or replan.

## Route

Read-only manuscript review takes the short route directly to `evidence-audit`, including full-manuscript scope. It does not require journal positioning or project initialization. When using the guard for this intent, pass `--task evidence_audit`. Targeted source lookup inside that review is not the deferred literature-management workflow.

1. Identify task, scope, language, permission, authoritative source, and whether project mode is needed. Map the user's natural language to controlled task and scope labels, then run `workflow_guards.py project-mode`. If it returns `PROJECT_MODE_CONFIRMATION_REQUIRED`, ask whether to enter project mode before any full-manuscript candidate is drafted.
2. Check whether the apparent local change carries cross-section evidence impact.
3. Choose exactly one `PRIMARY_MODULE`; include only necessary `SUPPORT_MODULES`.
4. Pass the minimal packet defined by the shared handoff schema.
5. Respect approval, source authority and unresolved evidence; section-order advice is not a drafting gate.

For journal-directed whole-manuscript work, reuse the confirmed journal context and author-chosen contribution, outline and revision sequence. Recommend changes when evidence warrants them; no universal section order determines the author's argument. Keep read-only review on its short route. Literature support belongs to manuscript-writing; material unresolved evidence conflicts can use evidence-audit. Do not repeat settled positioning or search approval.

## Approval and state

Discussion, approval, and write permission are separate. Update project state only after the user explicitly approves the information being recorded. Keep rejected candidates and full chat history out of state.

Default to constructive work with routine evidence checking and feedback recording. Visible critic or producer perspectives require the user's explicit call; there is no four-role rotation. Use configured role names, not a global nickname. Apply item-level approval and supersession in the existing authoritative state; return confirmed items, genuinely open items and the verified save location. A pending candidate is not an intentional hold, and approved direction is not approved wording. Resume from cumulative effective decisions, not only the latest message.

## Current stage boundary

Route statistical reconstruction, recalculation, field verification, and source comparison to `analysis-adapter`. The adapter may create approved analysis-state files and reproducible analysis outputs, but it cannot modify source data or manuscript files. Literature management, manuscript patching, reviewer-response workflows, and submission audits remain unavailable until their later modules are implemented.

Targeted literature support, contribution planning and task-scoped bilingual candidates are available inside existing modules; they are not a new literature database, file watcher or manuscript patcher.
