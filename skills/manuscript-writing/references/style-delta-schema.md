# Style delta schema

When a user approves a cross-paragraph preference that differs from the shared baseline, record it in `.psychology-paper/STYLE_DELTA.md` with:

- `rule_id`: stable project-local identifier.
- `user_wording`: the user's original preference.
- `normalized_rule`: concise reusable instruction.
- `scope`: languages, sections, or task types affected.
- `approved_on`: ISO date of explicit approval.
- `status`: `APPROVED` or `RETIRED`.

When a rule comes from an author sample, retain its source/location and observed feature (rhythm, connectors, hedge placement, opening, notation or phrasing) with the author's actual approval. Separate observation from instruction: a supplied sample permits task-local adaptation, not automatic permanent rules. Keep the latest author correction authoritative; mark an older incompatible rule RETIRED with a replacement reference. Do not treat a sample's unverified factual claims as style evidence for the manuscript.

Do not record rejected candidates, one-off sentence instructions, full conversations, or rules already present in the shared baseline. Record the file path under `optional_state_files.style_delta` in `PROJECT.md`.
