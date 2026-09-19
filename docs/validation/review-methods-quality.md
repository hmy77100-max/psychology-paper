# Methods and review continuity validation

## Scope

Approved steps 3 and 6 extend evidence-audit with conditional methods review and bounded quality/continuity guidance. Steps 4 and 5 remain deferred. No new project initialization, journal positioning, persistent database, analysis execution or installed-plugin update is introduced.

## Automated verification

- Baseline: all 90 existing tests passed.
- Before implementation, 16 new tests produced 14 failures and 2 errors because the checker and conditional resource selectors were absent.
- After implementation: all 106 tests passed, including the existing routing and evidence-provenance tests.
- Official plugin and evidence-audit Skill validators passed; whitespace checks passed.
- The mixed-design methods load measured 10,468 content characters. Focused quality and external loads remained below the unchanged 12,000-character per-load ceiling. Resources are selected by stage and reused; this does not establish a measured reduction in total conversation tokens.
- The optional checker validates explicit record fields and relationships. It does not verify source truth, semantic identity, author intent or scientific closure. Tests cannot establish those abilities.

## Behavioral observations

A fresh-context baseline agent already handled three supplied cases correctly: clustered/repeated observations, resolved/held issues and conflicting analysis identities. The gap was missing explicit reusable guidance, not demonstrated inability of the model to reason about these cases.

A separate fresh-context agent loaded resources through the canonical loader and role-played all ten scenarios in `tests/scenarios/review-methods-quality.json`:

| Scenario | Observed disposition |
|---|---|
| Clustered trial | Distinguished assignment/observation units; treated missing analysis detail as unresolved reporting, not proven invalidity |
| Coefficient scales | Withdrew false mismatch when standardized and raw coefficients explained it |
| Qualitative design | Rejected universal power, saturation and coding-agreement requirements |
| Scale interpretation | Limited total alpha evidence; requested only evidence relevant to actual score/claim |
| Meta-analysis | Identified dependent effects without imposing a single model |
| Unchanged duplicate and hold | Preserved canonical resolution, linked duplicate and kept held distinct from resolved |
| Changed scoring | Reopened the same issue with prior status and change basis; limited dependent review |
| Reviewer disagreement | Compared analysis identity and preserved unresolved evidence rather than voting |
| Partial re-review | Disclosed unread material; did not claim full-paper clearance or create a database |
| Checker boundaries | Distinguished structural completeness from semantic deduplication and journal readiness |

The agent found no substantive workflow conflict. It noted different names for intentional holds; guidance now explicitly maps shared `INTENTIONAL_HOLD` to review-record `HELD` without rewriting project state. Existing design fragments were sufficient alongside the new common guidance and were not duplicated.

## Limits

The ten scenarios expose their expected/forbidden actions: this was a criteria-aware synthetic rehearsal, not a blind evaluation. No real manuscript, appendix, figure, statistical output or persistent project history was inspected in this increment. No repeated-run drift study, acceptance-rate evaluation or downstream editing end-to-end test was conducted. The earlier targeted live lookup is documented separately and is not evidence of a new real-manuscript methods audit.

Model reasoning and author decisions remain necessary. Delivery is a development-branch update to the existing draft PR, not a main-branch merge or installed-plugin release.
