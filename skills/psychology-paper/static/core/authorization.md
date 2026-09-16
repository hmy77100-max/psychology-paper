# Authorization routing

Consult [the shared authorization contract](../../../.shared/core/authorization-and-state.md) for user-language mappings and [the shared state rules](../../../.shared/core/state-consistency.md) before any state update.

`DISCUSSION` and `CANDIDATE` permit analysis or candidate output only. `APPROVED` records the user's selection but does not itself set `WRITE_ALLOWED`. A request to write applies only to the approved content and named target.

Stage 1A may record approved state in `.psychology-paper/`. It cannot modify the manuscript even when the user requests a direct write; return a future patch handoff and stop.
