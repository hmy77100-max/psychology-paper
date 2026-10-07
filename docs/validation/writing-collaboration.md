# Writing craft and collaboration validation — 2026-10-07

This document records the pre-release development snapshot for 0.5.0. Its historical local/Unreleased/install status and test counts are preserved as provenance, not a live release query. The subsequent resource-stage validation records the expanded 166-test suite.

## Scope and implementation

Local source changes on the existing feature branch, starting at c8b236b. The release/install version remains 0.4.0; these changes are Unreleased, not installed or published. No research manuscript, research data or live project state was changed. The private optimization log is excluded from Git.

Implemented as two focused manifest resources, short existing-entry triggers, shared decision/handoff guidance, author-style integration and existing project-template documentation. No independent team service, new decision database, auto-writer, watcher or default four-role panel was introduced. These are agent instructions and resource contracts, not a new automatic state-transition engine.

## Automated RED → GREEN

- Added 10 tests in test_writing_collaboration.py before production edits. Initial run: 10 failures, due to absent selectors, missing instruction contracts and missing third-party notice.
- First implementation: 132 writing-route combinations exceeded the default resource budget. Diagnosis: the prose reference was 4,220 characters and a full-manuscript bilingual discussion route reached 14,073. The selectors were valid; this was a content-size failure.
- Replaced duplicated English explanations with compact Chinese examples and retained invariant checks; budget was not raised and required source comparison was not removed.
- Targeted run: all 10 tests passed. Full Windows suite: 152 tests passed. Diff whitespace check passed.
- After the original-text reminder, all 132 task/language/section combinations plus candidate format and prose diagnostics fit: maximum 11,370 characters (full-manuscript / english / keywords). The prose reference is 1,341 characters. Collaboration plus shared authorization also fits (final total is checked by the automated test).

String checks test instruction contracts and exact routing, not prose quality or scientific correctness. Existing tests additionally cover actual candidate-file/state safety. No new Linux CI run is claimed.

## Fresh-context micro-tests

The synthetic case combines deadline, reviewer-authority and sunk-cost pressures with partial approval, unavailable statistical output, a rejected term change, superseded order and an author sample. The original draft and cited names are synthetic. See tests/fixtures/writing-collaboration-probe.md.

Five control samples used an abbreviated existing-context prompt; five treatment samples used that prompt plus a compact new-guidance excerpt. Each sample was a separate fresh agent, not a role-played expert panel. This is a micro-test, not an exhaustive test of either whole plugin version. Controls and treatments both received the same task; treatment had additional context. No controlled token, latency or manuscript-quality benchmark was performed.

### Literal baseline observations

| Sample | Relevant actual output | Evaluation |
| --- | --- | --- |
| baseline_1 | “intentional_holds：候选段落仍待作者确认。” | Pending candidate incorrectly classified as an author hold. |
| baseline_2 | “intentional_holds：不替换‘心理距离’；保留必要的不确定性表述；p=.048 待核验。” | Rejection, invariant and missing evidence conflated with holds. |
| baseline_3 | “intentional_holds：候选段落仍待作者确认。” | Same pending-versus-hold failure. |
| baseline_4 | “intentional_holds：保留‘心理距离’、必要的‘可能’及 p=.048。” | Requirements and uncertainty treated as holds. |
| baseline_5 | “intentional_holds：候选段落待作者确认；暂缓删除科学限定语及调整 p 值。” | Inferred postponement not actually requested by author. |

All five preserved the technical name, uncertain association, three citation keys and reported p value; all rejected the proposed divide-p correction. Those successes do not warrant claims that the new guidance created these abilities. All used generic approval summaries for unspecified remaining suggestions rather than fully identifying approval scope.

### Initial treatment observations (before final clarification)

All five distinguished pending candidates from intentional holds and marked the term change rejected. All retained source quantities/citations and did not claim actual file writes. However, this was not an all-pass result:

- treatment_1: “作者对审稿建议的授权分别记录：删除全部‘可能’、替换重复术语、将 p 改为 p/3”. This assumed the unavailable approval list referred to nearby reviewer comments.
- treatment_3: “可识别的删尽‘可能’、替换术语及 p 值修改分别记录批准来源”. Same ambiguous-adoption issue.
- treatment_4: “作者批准、执行需核验：全面删‘可能’、替换重复术语、p值修改”. Same ambiguity; scientific caution does not cure an invented adoption link.
- treatment_2 and treatment_5 preserved the missing-list scope rather than assigning approval to those comments.
- Four treatments abbreviated the source. For example treatment_3 wrote “原文：以你本轮提供的三句为底稿，保留供核对。” Only treatment_2 reproduced the source in full. The micro-test did not execute the existing artifact checker; abbreviated source remains a failed delivery requirement.

These failures led to two narrow clarifications: nearby external feedback is not automatically the referenced approved list; and the prose resource requires verbatim complete original rather than a reference back to supplied text. No global canned replies or extra approval round were introduced.

## Full-resource follow-up

Completed after the two clarifications: full_context_acceptance used both entrypoints, exact manifests and fully loaded focused resources, rather than relying on the abbreviated micro-test prompt. Manual inspection found the following in its actual output:

- Full source paragraph reproduced verbatim in the original/revision/notes sequence.
- Preserved all three citation keys, technical term, uncertainty and p value; no borrowed sample claim or invented new contribution.
- Explicit rejection was excluded from execution, not marked pending or held. D3 superseded D2; direction and candidate acceptance remained separate.
- It stated: “在对应关系明确前，不能把附近两条审稿意见直接当作已获你批准的建议。” Missing-list clarification was limited to scope, not a request to approve known decisions again.
- It stated no actual project, abstract/discussion/English artifact or candidate-file validation had been checked, and labelled the update “未保存”. It did not fabricate a saved receipt or independent team.
- It identified the sample's question opening and short-sentence rhythm as task-local observations, not a permanent style rule.

This is one full-resource follow-up, not five repeated final-version trials. The five-per-arm micro-test exposed failures; only the bounded follow-up supports the final wording. Long-run stability remains unverified. The test deliberately used simulated content without filesystem writes, so it does not establish live state-persistence or bilingual-synchronization success.

## Limits

- This work does not establish reliable behavior over long conversations, improved publication outcomes, statistical correctness or reduced token usage.
- Five small samples are not a scientific performance estimate; only the stated failures/pass boundaries were checked manually.
- Post-revision matrices are agent-authored receipts. They must reference checked artifacts and leave unobserved bilingual or cross-section effects pending.
- The installed plugin remains unchanged. No PR, merge or refresh occurred in this optimization request.
