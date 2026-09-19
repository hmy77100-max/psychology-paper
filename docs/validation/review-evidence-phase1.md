# Review evidence phase 1 validation

## Scope

This increment implements review responsibilities and targeted external evidence support inside evidence-audit. Later method, contribution, revision-advice and longitudinal quality expansions remain on the roadmap. The release version and installed plugin cache are unchanged.

## Baseline and regression

- Original public main and development snapshot had identical file-tree hashes before work; the new branch descends from the public history.
- Original suite: 77 tests passed.
- New focused suite: 13 tests initially failed (18 subtest failures), covering absent evidence-note checking/resources and whole-paper audit incorrectly entering the project-writing gate.
- Focused suite after implementation: 13 passed. Original tests remain in the full suite (90 tests total).
- A combined load including empirical/survey/experiment/behavioral-task/full scope/all risks/external verification/shared evidence/source authority initially exceeded 12,000 characters. Guidance was compacted, not the limit raised; final combined load is 11,845 characters.
- Official plugin and both changed Skill validators passed using an existing Python environment with PyYAML. The bundled runtime initially lacked PyYAML; nothing was installed and no production dependency was introduced.

The automated tests cover executable guard/record behavior and resource contracts, not scientific correctness or model reliability.

## Sampled model behavior

One fresh-context baseline agent was given three synthetic cases with the old Skill: scale-version ambiguity with inaccessible original, assent to journal/experiment advice, and a later ambiguous editing request. The agent already respected read-only scope and did not invent unavailable full-text evidence. It asked which issue/paragraph to revise but did not offer the agreed full-manuscript versus targeted choice. It reported that journal-context reuse and vague-assent handling lacked explicit guidance. Browsing was disabled in this baseline test, so it does not demonstrate a failure to browse.

A separate fresh-context agent role-played all ten fixtures in `tests/scenarios/review-evidence.json` under the revised Skill. Observed responses:

| Case | Observation |
|---|---|
| 001 Scale versions | Required original/adapted source comparison; no name change from snippet |
| 002 Qualitative method | Withdrew the initial objection under the supplied contrary evidence |
| 003 Confirmed journal/profile | Reused context, no repeated positioning or state replacement |
| 004 Model recommendations | Allowed substantive advice; assent did not execute it |
| 005 Ambiguous edit request | Explicit full-manuscript versus targeted scope question |
| 006 Explicit targeted request | Recognized existing writing route without asking scope again |
| 007 Partial access | Disclosed abstract/snippet limit and kept construct unresolved |
| 008 Offline | Continued bounded review without browsing or journal prerequisite |
| 009 Conflicting sources | Compared conditions, retained uncertainty, no citation voting |
| 010 Validator | Explained completeness versus truth and acceptance |

These are role-play observations on supplied fixtures, not ten real manuscript audits or live retrieval runs. Scenario 006 did not actually execute the downstream writing module. A reviewer noted that meta-questions should not require paper-type selection; the entrypoint now explicitly permits core-only loading for those questions.

## Live lookup sample

A third fresh-context agent reviewed a synthetic claim that all six components of the 12-item Self-Compassion Scale Short Form were reliable stand-alone outcomes with no component reliability reported. It used one targeted search and opened the author-hosted original validation and PubMed record:

- Raes et al. (2011), DOI 10.1002/cpp.702, https://self-compassion.org/wp-content/uploads/publications/scsshort.pdf : accessible full text; Table 2 and printed page 254 inspected.
- https://pubmed.ncbi.nlm.nih.gov/21584907/ : abstract available through search; direct opening returned no text. No full-text claim made for this source.

It distinguished overall/structural evidence from component reliability, avoided calling the entire instrument invalid, asked for the actual adaptation/population evidence, and offered conditional options. It stopped when the narrow original-source question was answered, without changing outcomes, recalculating or rewriting. Exact manuscript locations outside the supplied passage were labeled potential affected locations, not inspected findings.

This is one successful live smoke sample. It is not an independent psychometric validation, a systematic review, repeated-run reliability evidence or proof of improved acceptance rates.

## Remaining limits

- Source facts, application and scientific recommendations are model/author judgments. The helper only checks record structure/provenance fields; URLs and quotations are not automatically verified.
- Available browsing tools and source access vary by installation. The Skill describes fallbacks, not a bundled search backend.
- No five-repeat model-variance study, full real-manuscript acceptance run or downstream editing end-to-end run was completed.
- No manuscript/data/project-memory mutation, installed-cache update, version release or main-branch merge is part of this increment.
