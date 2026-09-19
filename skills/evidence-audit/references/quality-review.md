# Review quality and continuity

Before delivery, check important findings for source/locator support, applicable design, alternatives, scope, evidence ceiling and duplicate/conflicting advice. Reuse inspected material. This is a bounded check of the review, not a mandatory second full-paper audit. Stop when material contradictions are reconciled or explicitly unresolved.

## One issue across responsibilities and rounds

The model matches issues by affected claim, location and analysis identity, not wording or ID alone. Preserve one stable canonical ID and sources from contributing notes. Link duplicates to that issue; do not count them as new independent defects. Similar text may concern different samples/models and must remain distinct.

When reviewers disagree, compare inspected sources and study/sample/outcome/model/contrast/scale. Do not vote by number or authority of reviewers. Explain reconciliation; if evidence cannot decide, retain the conflicting bases and the missing fact in one unresolved issue. A checker cannot make that scientific decision.

For repeat reviews, reuse the relevant prior record and manuscript version. Inspect changes and necessary dependent claims; report new, changed, resolved or reopened findings without repeating unchanged review history. A resolved concern is reopened only when identified new evidence, a relevant version/context change or a demonstrated error in the earlier resolution undermines its basis. Another reviewer merely repeating it is not new evidence. Preserve the prior resolution and explain the change. Without prior records, disclose unavailable continuity; do not invent history or force project setup.

## Compact record

Keep the record in the conversation or reuse existing project memory. No parallel database or automatic state writes. Persist adopted changes only through existing authorized project-state handling. A standalone audit needs no prior history.

Top-level fields: `manuscript_version` (known identifier or explicitly unknown), `coverage` (inspected/uninspected sources), `issues` (may be empty; not journal clearance).

Issue fields: `issue_id`, `location`, `claim`, `analysis_identity` (describe non-statistical context when applicable), `kind` (methods-review vocabulary), `basis`, `evidence_refs` (inspected source locators or existing evidence-note IDs), `status`, `status_basis`.

Statuses are proposed review dispositions, not adoption/write permission:

- `OPEN`: active supported question/concern.
- `AWAITING_MATERIAL`: identified missing material prevents resolution.
- `HELD`: author deliberately deferred/retained it; record the author's instruction. It is not resolved. Resurface only for a relevant requested risk review or when blocking the requested action.
- `RESOLVED`: inspected evidence addresses the issue; record `resolution_evidence`, not just an author's promise to fix it.
- `WITHDRAWN`: objection refuted/not applicable; record `resolution_evidence` and why it was withdrawn.
- `REOPENED`: record `previous_status` and `change_basis`, retain prior evidence. May include an explicit author request to reconsider a held issue, but not generic assent to advice.

The shared risk-reporting term `INTENTIONAL_HOLD` corresponds to `HELD` in this review record. Preserve the existing project vocabulary when reusing memory; translate explicitly at this record boundary without rewriting project state. Neither label means resolved.

Optional `duplicate_of` points directly to a canonical ID in the same record; aliases share its reconciled status. Keep the canonical record in a delta packet if including aliases. For resumed closed/held issues, never reset silently to OPEN. Only set `previous_status` when the status is changing in this record, not as a permanent last-round field.

Optional plugin-root `scripts/review_quality.py --record PATH|-` reads an existing JSON record or stdin. It checks IDs, explicit links, required bases and state consistency; it does not infer duplicates, verify evidence, decide closure, save state or score readiness. `record_complete` is structural, always `scientific_verification=false`. No file creation is required to run it.
