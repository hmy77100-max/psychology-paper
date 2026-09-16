# Repository maintenance rules

- Add or change behavior only after adding a failing regression or behavioral scenario and observing the failure. Run the full test suite before completion.
- The only authoritative Skill resource map is `skills/<skill-name>/manifest.yaml`.
- Resolve declared resources through `scripts/load_skill_resources.py`. Do not guess alternate manifest names or child resource paths.
- Do not enumerate directories or recursively search the repository to recover a missing Skill resource. Report the bounded missing path and repair the authoritative manifest or declared file.
- Keep journal-specific values in paper project state or test fixtures. Do not promote one paper's journal limit, terminology, or statistical result into a global default.
- Tests and plugin maintenance must not modify user manuscripts or source data.
