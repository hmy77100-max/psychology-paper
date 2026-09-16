---
name: analysis-adapter
description: Reconstruct, preflight, reproduce, and compare quantitative psychology analyses while preserving design, field, source, and user-approval boundaries.
---

# Psychology Analysis Adapter

Use this skill when a psychology manuscript requires statistical reconstruction, recalculation, source comparison, or a reproducible analysis specification. It may create approved analysis-state files and analysis outputs, but it never modifies source data or manuscript files.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill analysis-adapter`. The loader includes `always_load` automatically. Add all and only applicable `axes.design_tags.*` selectors and any required `conditional_loads.*` selector. Do not infer paths or enumerate directories.

## Required sequence

Follow this order: research design → data fields → scoring → sample → model → software → results → manuscript synchronization.

1. Reconstruct the design from the manuscript, materials, preregistration, syntax, output, or author statement. If the design cannot be reconstructed, ask for it; do not infer it from column names.
2. Build a field map from the design and ask the author to confirm every analysis-bearing field, plus any missed grouping variable, repeated-measure level, exclusion flag, covariate, manipulation, check, mediator, moderator, or outcome.
3. Run `analysis_preflight.py`. Do not calculate until it returns `READY_FOR_ANALYSIS`.
4. Use exactly one `AUTHORITATIVE` analysis source and at most one `VERIFICATION` source. Prefer the original software, syntax, and output when available. With only transparent Excel/CSV data, recommend Python or R and let the user confirm the formal source.
5. Lock scoring, sample, exclusions, model, software version, estimator, Bootstrap settings, and seed before formal calculation. Do not try alternative specifications to seek significance.
6. When an authoritative and a verification output both exist, run `compare_analysis_results.py` before interpretation. Present discrepancies in natural language: what differs, confirmed cause, remaining uncertainty, and effect on the manuscript conclusion. Preserve the authoritative result until the user adopts a new formal source; statistical disagreement is not evidence of misconduct.
7. Update `ANALYSIS_REGISTRY.md` only after the user adopts the formal specification or result. Generate a synchronization list; do not modify the manuscript.

Statistical markers, effect labels, and verbal significance claims must refer to the same named analysis. Use `workflow_guards.py statistical-marker` when a marker is added, removed, or disputed.
