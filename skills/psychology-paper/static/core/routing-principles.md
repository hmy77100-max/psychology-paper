# Routing principles

Interpret ordinary requests; choose one primary module:

- journal fit/style → `journal-fit-style`
- review or evidence conflict → `evidence-audit`
- writing/translation candidates → `manuscript-writing`
- method review, candidate calculation, formal analysis or verification → `analysis-adapter`
- orchestration/decisions → `psychology-paper`

After understanding the design during manuscript work, use `analysis-adapter` to assess potentially unused observations; a general revision request is enough. Keep isolated language edits local.

Standalone `method_review`, `candidate_analysis` and `verification` need no project setup and grant no manuscript writes; `reanalysis` is formal project work. Pass bounded context/authorization to support modules. Scientific meaning or identifier changes need impact checks, not automatic escalation; reading does not widen edit scope.
