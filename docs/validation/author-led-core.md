# Author-led short core and resource reuse

Date: 2026-11-10. Local source validation on `feat/author-led-short-core`, against baseline `82e29a7` (0.5.0). The validation history below predates installation and release preparation.

2026-11-11: the existing local installation was updated to 0.5.1 with matching manifest/test expectations. All 172 package files matched the installation, and all 187 tests passed again from the installed directory. Subsequent release preparation keeps this implementation unchanged and updates the public version notes. No Claude Code adaptation is included. Local installation checks and GitHub CI are separate verification steps.

## Scope and implementation

The author chooses the argument, substantive interpretation and writing order. The plugin supports that work through evidence, source and decision consistency; it does not prescribe paragraph logic.

- Replace the old writing-stance resource with one shared author-led core, used by routing, direct writing and review. Its body is 232 characters, 233 including the final newline.
- Remove fixed evidence-first and four-step discussion sequences, mandatory introduction endings and transition patterns, and the global one-location caveat quota.
- Replace automatic audit handoffs for scientific wording with targeted checks for material unresolved conflicts. Verified revisions within existing authorization may proceed.
- Make body/abstract/keywords order advisory. Source, candidate integrity, count baseline and author-response checks still block invalid adoption. Later changes still mark dependent summaries pending; early adoption does not approve other units.
- Extend the existing receipt interface rather than adding a second workflow. V2 receipts retain their originating request and can reuse identical complete resources across selectors and modules within one valid context. Ordinary short loads remain available; continuous paragraph editing does not require a new receipt cycle.

Shared reads match path, content hash and length. Context, root, manifest or source changes invalidate the applicable receipts. Partial receipts do not inherit omitted resources; their original receipts must remain present. Circular prerequisites cannot create a read. Legacy receipts remain plan-bound. Receipts attest reading, not comprehension or scientific verification.

## Regression evidence

Observed failures before implementation:

- Five author-core tests produced seven subtest failures: missing shared resource, unchanged default cost, fixed discussion sequence, caveat quota and automatic audit handoff.
- Two revision tests rejected an author-approved early abstract or returned a compulsory-order CLI error.
- The first ten reuse tests produced four errors and two failures. They exposed missing cross-request reuse and repeated complete delivery. A later same-path/different-content regression also failed before resource identity was strengthened.

Full-suite integration then exposed an audit resource bundle at 12,158 characters, over the unchanged 12,000 limit. Compressing old repeated review instructions brought it to 11,973. A subsequent exact safeguard assertion exposed an unnecessarily shortened source-authority phrase; the original phrase was restored rather than weakening the test.

Final command:

```text
python -X utf8 -m unittest discover -s tests -q
Ran 187 tests in 14.286s
OK
```

Baseline: 166 tests passed. The 21 added tests comprise five author-core contracts, two revision-order regressions and fourteen resource-reuse cases. Existing tests were changed only where the approved order/reuse semantics changed; source and approval safeguards remain.

An independent read-only review ran 51 targeted tests and six temporary synthetic probes (early keywords, stale baseline, unconfirmed journal, stale source, missing author response, reversed receipt order). It found no blocking issue. This is code and synthetic validation, not a real-manuscript effectiveness trial.

## Instruction-loading measurements

Baseline and current code ran in separate Python processes. The baseline came from `git archive 82e29a7`. Counts below use Unicode characters, not tokens. Resource bodies exclude labels; rendered resource output includes labels. Entry means the applicable SKILL.md. No billed-token or latency reduction is claimed.

| Ordinary request | Old resource body | New resource body | Old entry + rendered resources | New entry + rendered resources |
| --- | ---: | ---: | ---: | ---: |
| Router core | 1,709 | 1,544 | 8,317 | 7,742 |
| Writing core | 4,856 | 3,604 | 11,163 | 9,694 |
| Local edit / English / abstract | 6,170 | 5,020 | 12,647 | 11,280 |
| Same request plus prose diagnostics | 7,511 | 6,380 | 14,039 | 12,691 |

Staged measurements call the actual plan, stage and coverage functions. Each delivered body is explicitly acknowledged in the synthetic driver. Absolute plugin roots are replaced with `<plugin>` before JSON counting; JSON uses `ensure_ascii=False`, two-space indentation and a final newline. Counts include plan, delivery and coverage outputs, but exclude SKILL entries, tool request text and hosting wrappers. Fully covered stages are not re-read.

| Staged sequence | Old new-body total | New new-body total | Old output incl. JSON | New output incl. JSON | Outputs old → new |
| --- | ---: | ---: | ---: | ---: | ---: |
| Router core → writing with task/language/abstract | 7,879 | 6,331 | 15,805 | 15,464 | 7 → 7 |
| Writing core → same skill with task/language/abstract | 11,026 | 5,020 | 20,433 | 13,154 | 7 → 6 |
| Same complete writing route twice | 6,170 | 5,020 | 14,789 | 14,237 | 6 → 6 |

Metadata has a real cost: the router-to-writing output reduction is modest even though fewer body characters are delivered. Do not start staging merely to avoid repeating a short core. Once the needed instructions are fully present and current, later paragraphs should reuse them without another plan/coverage ceremony. The repeated-route benchmark measures a deliberately repeated request, not a recommended workflow.

## Behavior check and limits

Fresh-context assistants used the same fictional language-only task before and after the change. The author required interpretation → result → practical suggestion order. Both versions preserved that order, gave a language candidate, added no audit disclaimer and did not initiate a separate evidence review. The baseline already passed: this does not establish improved writing quality or prove reduced long-term drift.

The local-edit / Chinese / discussion route loaded eight resources: 6,406 body characters before, 5,212 after. The updated assistant also attempted the required candidate-format/check resources in one request; the 12,951-character request was correctly rejected. The existing stage planner then split those same necessary resources into whole groups of 3,604 / 1,608 / 2,267 / 5,472 characters. The failed ordinary request was not counted as a completed read. Staging recovery is recorded separately from the prose comparison.

During recovery a manifest newline normalization invalidated the old receipt, despite unchanged decoded resource bodies. With a fresh context the assistant read all four stages, explicitly acknowledged each actual output, and obtained `ACKNOWLEDGED` with no pending stages. It did not run candidate-file validation: the prose sample is a behavior smoke check, not a completed end-to-end manuscript delivery.

The 2026-11-10 validation did not change manuscripts or source data, install the plugin, refresh caches or publish remotely; the subsequent installation is recorded above. Longitudinal author-led writing performance and actual usage cost remain unmeasured.
