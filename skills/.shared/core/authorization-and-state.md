# Authorization and state

## Generic intent classes and user-language mapping

Map natural language to a generic intent before changing state. The examples below are not a closed phrase list. Different users may express the same intent differently, and an approved user-specific phrase mapping may extend the examples without changing the generic intent model.

- `DISCUSS_ONLY`: inspect, compare, explain, or generate a candidate without approval or writing.
- `APPROVE_CURRENT`: approve only the active candidate.
- `APPROVE_CURRENT_AND_ADVANCE`: approve only the active candidate and continue to the next agreed unit. With an active candidate, a standalone “下一步” belongs here; it is not advance-without-approval.
- `REJECT_CURRENT`: reject the active candidate and remove it from the execution list.
- `HOLD_CURRENT`: retain an unresolved issue without repeating it in ordinary rounds.
- `WRITE_APPROVED_TARGET`: write only already approved content to the named target when the current stage permits writing.

- “先判断”“先讨论”“先反馈” authorize reading, diagnosis, or candidate generation only.
- “通过”“采用你的”“按这个改” set the current candidate to `APPROVED`; they do not approve unrelated candidates.
- “下一步” with an active candidate sets that candidate to `APPROVED` and advances to the next agreed unit.
- “直接往原文件里改” grants write permission only for already approved content and only for the named target.
- “不改”“别管” set the current candidate to `REJECTED` and remove it from the execution list.
- “先留着” sets the issue to `INTENTIONAL_HOLD`; ordinary rounds do not raise it again unless the requested risk review requires it.

Review permission, recalculation permission, adoption of a result, and permission to write a file are independent. Never infer one from another.

## State namespaces

Use separate fields for `decision_status`, `write_permission`, `patch_status`, `source_role`, `evidence_status`, `risk_level`, and `check_status`. Do not create a combined Cartesian-product status. Consult [state-consistency.md](state-consistency.md) for machine-enforced illegal combinations.

## Document invariants

```text
PATCH_FIRST = true
FULL_REBUILD_ON_LOCAL_EDIT = false
AUTO_VERSIONED_COPY = false
FULL_RENDER_ONLY_AT_MILESTONE = true
```

These invariants describe future document writes. Stage 1A may create approved project state but remains read-only for manuscripts.
