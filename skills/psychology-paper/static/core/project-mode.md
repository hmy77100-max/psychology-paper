# Project mode

Enter project mode for full-manuscript revision, formal project reanalysis, formal reviewer response, submission preparation, or work expected to continue across sessions. Confirm the authoritative manuscript before initializing state.

Before full-manuscript writing begins, record the confirmed journal's body limit, counting unit, counting scope, and current body count in `.psychology-paper/PROJECT.md`. If the limit is unknown, pause candidate drafting and ask the user for the journal rule or permission to verify it. When the current body already exceeds the limit, accept only candidates that reduce or preserve the length of the passage they replace.

Do not require project mode for one isolated sentence or paragraph unless the change affects the paper-wide evidence chain. A long-running project stores only authoritative paths, confirmed journal, approved decisions, formal analysis source, intentional holds, unresolved blockers, and the next action.

If `.psychology-paper/PROJECT.md` exists, validate it before use. If it does not exist, initialization requires explicit confirmation and must not scan, copy, or edit manuscript files.


Short method consultations and standalone candidate reanalyses do not require a manuscript project. Apply project validation when creating or changing manuscript project state; this exception does not relax validate_project.

Controlled tasks `method_review`, `candidate_analysis`, and `verification` use STANDALONE_ANALYSIS and never grant manuscript writing, even when project state already exists. Legacy `reanalysis` retains formal project gating.
