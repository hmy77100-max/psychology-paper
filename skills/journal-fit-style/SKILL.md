---
name: journal-fit-style
description: Profile a psychology manuscript, recommend or assess target journals, and learn official requirements plus recent article organization before journal-directed revision.
---

# Journal Fit and Style

Use this skill when the user needs journal direction, fit assessment, or journal-specific organization and writing style. It diagnoses and proposes; it does not rewrite the manuscript.

## Deterministic resource loading

Resolve the [resource loader](../../scripts/load_skill_resources.py) relative to this entry file and run it with `--skill journal-fit-style`. The loader includes `always_load` automatically. Add exactly one applicable `axes.journal_status.*` selector and one `axes.depth.*` selector. Add an `axes.output.*` or `shared_loads.*` selector only when the requested deliverable requires it.

Do not open child resource paths directly, infer a similar path, or enumerate directories. A loader error is a plugin-integrity failure; stop this plugin invocation and report the bounded error. Keep the default character budget and never load all journal-status or depth branches.

## Route by journal status

- No target journal: build a manuscript profile before suggesting ambitious, balanced, and safer directions.
- Candidate journals: perform a light current scan for each candidate.
- Confirmed journal: keep that journal authoritative, verify current official requirements, and study closely matched recent articles.
- Existing profile: refresh only drift-prone policies or observations needed for the current task.

## Evidence and browsing

Current journal scope, article types, review model, limits, fees, data/ethics policies, and submission requirements require live verification from official sources. Observed writing style comes from recent published articles and must be labelled as observation rather than requirement. Candidate scans default to 1–2 close articles; confirmed-journal deep study defaults to 2–3 and expands only when their patterns conflict.

## Output and approval

Return a manuscript profile, candidate comparison, or journal profile candidate. State the fit, strongest match, largest risk, and revision implications. Do not switch a user-confirmed journal. Write `.psychology-paper/JOURNAL_PROFILE.md` only after approval and record its path in project state.
