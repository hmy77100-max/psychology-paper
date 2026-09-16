---
name: evidence-audit
description: Read-only audit of psychology claims, constructs, research designs, measures, visible statistics, and cross-section consistency, adapted to the paper and design type.
---

# Evidence Audit

Use this skill to judge whether a psychology manuscript's claims match its constructs, design, measures, visible results, and cross-section evidence. Report problems only; do not rewrite or modify files.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill evidence-audit`. The loader includes `always_load` automatically. Select one applicable `axes.paper_type.*`, all and only applicable `axes.design_tags.*`, one `axes.scope.*`, and the requested `axes.risk_threshold.*`. Add a named `shared_loads.*` selector only when the current audit requires it.

Do not open child resource paths directly, infer a similar path, or enumerate directories. A loader error is a plugin-integrity failure; stop this plugin invocation and report the bounded error. Keep the default character budget and never load design checks that do not apply.

## Load only applicable checks

Identify the paper type, every relevant design tag, observation unit, evidence source, scope, and requested risk threshold. Do not apply experimental checks to a survey or quantitative parameter checks to a qualitative paper.

## Audit sequence

1. Confirm the authoritative source and requested scope.
2. Reconstruct the research question and design from the manuscript or supplied design materials.
3. Audit constructs, operations, measures, data/sample descriptions, visible analyses, result interpretation, and claim boundaries applicable to that design.
4. Assign an evidence status and risk level to each material issue.
5. For evidence-bearing changes, run the change-impact audit and return a synchronization list.

Without recalculation authorization, inspect only visible consistency and mark anomalies for verification. Do not try alternate scoring, exclusions, or models. Statistical inconsistency is not evidence of misconduct.

When a significance marker or verbal significance claim is added, removed, or questioned, identify the exact named analysis for both the target value and its supporting report, then run `workflow_guards.py statistical-marker`. A marker from a correlation, regression, simple effect, interaction, alternative score, or other analysis cannot support a different named result. If the guard returns `UNRESOLVED`, preserve the authoritative text and report the mismatch for user action.

After the user chooses a response, send only the selected issue, evidence ceiling, and affected locations to `manuscript-writing` or a later module.
