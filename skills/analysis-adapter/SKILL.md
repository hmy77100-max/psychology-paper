---
name: analysis-adapter
description: Identify underused information in psychology data, assess methods, reproduce analyses, and compare results while preserving author decisions.
---

# Psychology Analysis Adapter

Use for analysis opportunities, reconstruction, recalculation or source comparison in psychology manuscripts and data, including when the author has not named an alternative method. Preserve source data and manuscript files.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill analysis-adapter`. The loader includes `always_load` automatically. Add all and only applicable `axes.design_tags.*` selectors and any required `conditional_loads.*` selector. Do not infer paths or enumerate directories.

## Intent-specific workflow

Apply the four intents in the loaded core. Load `conditional_loads.method_learning` to investigate a worthwhile analysis opportunity, learn or compare methods, or execute candidates. Load shared authorization, state rules, and handoff only when relevant. Confirm adoption before updating ANALYSIS_REGISTRY.md; propose manuscript synchronization without editing it.

When formal and verification outputs both exist, load `conditional_loads.source_comparison` and run compare_analysis_results.py before interpretation. Use workflow_guards.py statistical-marker for disputed markers. Describe discrepancies and preserve the formal source pending author adoption.
