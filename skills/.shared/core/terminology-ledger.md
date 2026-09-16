# Terminology ledger

The terminology ledger prevents theoretical constructs, operations, checks, and outcomes from being collapsed into one name.

Record one row per term with these fields:

| Field | Meaning |
|---|---|
| `chinese_name` | Approved Chinese construct or variable name. |
| `english_name` | Approved English name. |
| `abbreviation` | Approved abbreviation or null. |
| `level` | Trait, state, manipulation, task, observed response, or other declared level. |
| `theoretical_construct` | The theory-level concept, if any. |
| `manipulation` | The operation intended to change the construct. |
| `manipulation_check` | What the check directly measures. |
| `measured_indicator` | Scale, item, device, or derived feature. |
| `outcome_indicator` | Self-report, preference, choice, performance, consequential behavior, or other outcome type. |
| `noninterchangeable_terms` | Similar labels that must not be silently substituted. |
| `source_location` | File and location supporting the mapping. |
| `confirmation_status` | `CONFIRMED`, `INFERRED`, or `UNRESOLVED`. |

Build the initial mapping from the manuscript, design, materials, data dictionary, and author statements. Then ask the author whether any variable, grouping field, repeated-measure level, or task-specific meaning has been missed. Ambiguous mappings remain unresolved; do not select the interpretation that produces the strongest result.
