---
name: evidence-audit
description: Use when reviewing psychology manuscripts, evaluating claims and methods, checking measures against source literature, or examining cross-section evidence consistency without editing.
---

# Evidence Audit

Help the author address material publication obstacles through evidence-grounded review. The plugin structures scope, sources and feedback; the model reasons and recommends; the author chooses. Review only: do not rewrite the manuscript or modify files.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill evidence-audit`. The loader includes `always_load` automatically. Select one applicable `axes.paper_type.*`, all and only applicable `axes.design_tags.*`, one `axes.scope.*`, and the requested `axes.risk_threshold.*`. Add a named `shared_loads.*` selector only when the current audit requires it.

For a material question requiring external verification, add `conditional_loads.external_evidence`. Reuse already loaded guidance and sufficient inspected evidence; do not reload all groups for each issue. If no risk threshold is specified, use `axes.risk_threshold.all`. If scope is `change-impact`, also select `axes.scope.local` for the report contract.

Paper/design selectors apply when reviewing manuscript evidence. A scope clarification or explanation of review tools uses core rules only; do not invent a paper type or ask for one just to answer that meta-question.

For scientific review select `conditional_loads.methods_review` with the applicable design resources. Before delivering findings or reconciling a repeat review, load `conditional_loads.quality_review` once. Use focused loads for each stage and retain already loaded resources; do not combine every optional group or repeat all design/profile content for a quality check. Stay within the unchanged per-load budget.

Do not open child resource paths directly, infer a similar path, or enumerate directories. A loader error is a plugin-integrity failure; stop this plugin invocation and report the bounded error. Keep the default character budget and never load design checks that do not apply.

## Load only applicable checks

Identify the paper type, every relevant design tag, observation unit, evidence source, scope, and requested risk threshold. Do not apply experimental checks to a survey or quantitative parameter checks to a qualitative paper.

## Audit sequence

1. Take the short route directly into review, including full-manuscript review. Reuse relevant supplied article/journal profiles and project memory without restarting journal positioning or creating state.
2. Reconstruct the author's question and design. Clarify only uncertainties that materially affect this review.
3. Check applicable constructs, operations, measures, samples, visible analyses and claims. Check other sections, tables, figures and appendices before alleging a conflict; state anything not inspected.
4. For externally verifiable uncertainties that could change a material recommendation, perform targeted source lookup using available browsing/retrieval tools. Honor offline requests and tool/access limits; report unresolved questions and continue independent checks.
5. Separate observed facts, interpretations and recommendations. Assign issue kind separately from evidence status/risk; preserve supported contributions. Apply quality review to sources, coverage, duplicates, conflicts and any prior issue dispositions before delivery.
6. For proposed evidence-bearing changes, load `axes.scope.change-impact` and return affected locations. Deliver the review and stop; no automatic editing or analysis handoff.

Without recalculation authorization, inspect only visible consistency and mark anomalies for verification. Do not try alternate scoring, exclusions, or models. Statistical inconsistency is not evidence of misconduct.

When a significance marker or verbal significance claim is added, removed, or questioned, identify the exact named analysis for both the target value and its supporting report, then run `workflow_guards.py statistical-marker`. A marker from a correlation, regression, simple effect, interaction, alternative score, or other analysis cannot support a different named result. If the guard returns `UNRESOLVED`, preserve the authoritative text and report the mismatch for user action.

For a later editing request with unspecified scope, ask full-manuscript versus targeted revision. Reuse scope already specified by the user. Only then follow the existing revision route with the selected issue, evidence ceiling and affected locations. Assent to advice alone does not start that route.
