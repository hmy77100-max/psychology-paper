---
name: evidence-audit
description: Use when reviewing psychology manuscripts, evaluating claims and methods, checking measures against source literature, or examining cross-section evidence consistency without editing.
---

# Evidence Audit

Help the author address material publication obstacles through evidence-grounded review. The plugin structures scope, sources and feedback; the model reasons and recommends; the author chooses. Review only: do not rewrite the manuscript or modify files.

Exercise independent academic judgment to the standard of a senior, rigorous peer reviewer; this is a professional standard, not a claim of human credentials. Review the current completed manuscript, not a profile of an earlier argument. Standalone review needs no profile or project; project review uses the current approved manuscript. Approval, including prior plugin-assisted revision, is not scientific validation.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill evidence-audit`. The loader includes `always_load` automatically. Select one applicable `axes.paper_type.*`, all and only applicable `axes.design_tags.*`, one `axes.scope.*`, and the requested `axes.risk_threshold.*`. Add a named `shared_loads.*` selector only when the current audit requires it.

For a material question requiring external verification, add `conditional_loads.external_evidence`. Reuse already loaded guidance and sufficient inspected evidence; do not reload all groups for each issue. If no risk threshold is specified, use `axes.risk_threshold.all`. If scope is `change-impact`, also select `axes.scope.local` for the report contract.

Interpret ordinary requests without a command menu. Screening prioritizes blockers and labels limited coverage. Full review is the default for an entire submitted paper. Requested deep re-review examines missed questions and reasoning even without manuscript changes. Incremental verification examines requested revisions and dependent claims. Full and deep reviews use `axes.scope.full`; never silently reduce them to screening or a diff. Honor explicit issues-only, local and risk-limited requests; no profile setup prerequisite.

Paper/design selectors apply when reviewing manuscript evidence. A scope clarification or explanation of review tools uses core rules only; do not invent a paper type or ask for one just to answer that meta-question.

For scientific review select `conditional_loads.methods_review` with the applicable design resources. Before delivering findings or reconciling a repeat review, load `conditional_loads.quality_review` once. Use focused loads for each stage and retain already loaded resources; do not combine every optional group or repeat all design/profile content for a quality check. Stay within the unchanged per-load budget.

When evaluating contribution or obstacles for an existing target, select `conditional_loads.contribution_review`. When organizing substantive revision choices, select `conditional_loads.revision_options`. These are review responsibilities, not a new journal-positioning or editing route. Skip expansions outside the requested scope, including advice for issues-only requests.

Do not open child resource paths directly, infer a similar path, or enumerate directories. A loader error is a plugin-integrity failure; stop this plugin invocation and report the bounded error. Keep the default character budget and never load design checks that do not apply.

## Full-review duties

For full or requested deep review, establish the paper's strongest supported contribution against the closest relevant evidence; topic importance is not novelty. Examine applicable title/abstract, argument/predictions, methods, results, discussion, tables/figures and supplied supplements. Provide locations, evidence, consequences and severity, consolidating repeated manifestations without hiding independent problems. Note significant inspected areas without concerns and disclose coverage limits.

Test both author interpretations and reviewer objections against alternatives and contrary evidence. For an unresolved material fact, explain plausible outcomes, which conclusions each changes and what settles it; do not stop at 'verify'. Possible confounds are not demonstrated causes. Preserve defensible author choices and useful strengths.

Prioritize essential corrections, substantial improvements and acceptable limits. Explain reporting versus output verification, analysis or new evidence, benefits, costs and dependencies; use the existing conditional contribution/advice resources. Narrower wording cannot repair unidentified effects or unverifiable results. No minimum issue, source or length quota applies. A blocker list alone is not a completed full review. Apply these duties substantively, not as generic headings, and do not expand explicit local or issues-only requests.

## Applicable checks

Identify the paper type, every relevant design tag, observation unit, evidence source, scope, and requested risk threshold. Do not apply experimental checks to a survey or quantitative parameter checks to a qualitative paper.

## Audit sequence

1. Take the short route directly into review, including full-manuscript review. Identify the current manuscript and version using the workflow authority rules. Reuse compatible background and journal requirements without restarting positioning or creating state.
2. Understand the author's question, argument and design from that manuscript. Do not substitute an old profile or approved intentions for what readers can actually see. Clarify only uncertainties that materially affect this review.
3. Check applicable constructs, operations, measures, samples, visible analyses and claims. Check other sections, tables, figures and appendices before alleging a conflict; state anything not inspected.
4. For externally verifiable uncertainties that could change a material recommendation, perform targeted source lookup using available browsing/retrieval tools. Honor offline requests and tool/access limits; report unresolved questions and continue independent checks.
5. Separate observed facts, interpretations and recommendations. Assign issue kind separately from evidence status/risk; preserve supported contributions. Where in scope, compare contribution with existing target requirements and organize feasible advice by evidence needs, tradeoffs and dependencies. Apply quality review to sources, coverage, duplicates, conflicts and any prior issue dispositions before delivery.
6. For proposed evidence-bearing changes, load `axes.scope.change-impact` and return affected locations. Deliver the review and stop; no automatic editing or analysis handoff.

Without recalculation authorization, inspect only visible consistency and mark anomalies for verification. Do not try alternate scoring, exclusions, or models. Statistical inconsistency is not evidence of misconduct.

When a significance marker or verbal significance claim is added, removed, or questioned, identify the exact named analysis for both the target value and its supporting report, then run `workflow_guards.py statistical-marker`. A marker from a correlation, regression, simple effect, interaction, alternative score, or other analysis cannot support a different named result. If the guard returns `UNRESOLVED`, preserve the authoritative text and report the mismatch for user action.

For a later editing request with unspecified scope, ask full-manuscript versus targeted revision. Reuse scope already specified by the user. Only then follow the existing revision route with the selected issue, evidence ceiling and affected locations. Assent to advice alone does not start that route.
