# Minimal module handoff

Pass the following ordered packet:

```text
task
source_path
location
scope
paper_and_design_tags
authoritative_source
approved_constraints
evidence_ceiling
required_output
open_issue
PRIMARY_MODULE
SUPPORT_MODULES
STOP_CONDITION
```

- `task`: the concrete action requested now.
- `source_path`: the authoritative file path; omit copied contents when the receiver can read it.
- `location`: the exact section, paragraph, table, figure, sheet, or field.
- `scope`: sentence, paragraph, section, full manuscript, project, or submission milestone.
- `paper_and_design_tags`: the paper, design, observation-unit, and evidence-source tags that control checks.
- `authoritative_source`: the source ID and role governing this task.
- `approved_constraints`: only user-approved limits and frozen content.
- `evidence_ceiling`: the strongest claim permitted by the current evidence.
- `required_output`: diagnosis, candidate, profile, synchronization list, or state update.
- `open_issue`: one unresolved question that can change the task; use null when none exists.
- `PRIMARY_MODULE`: exactly one module responsible for the result.
- `SUPPORT_MODULES`: only the modules needed for a bounded supporting check.
- `STOP_CONDITION`: the event at which work must stop for approval, missing authority, or unavailable capability.

Exclude full chat history, rejected candidates, unrelated sections, repeated journal guidance, and duplicated file contents. If the receiver can read a file, pass its path and location.
