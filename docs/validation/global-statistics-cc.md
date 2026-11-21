# Shared statistics and Claude Code: development validation

This record preserves development after the 0.5.2 baseline, including host attempts on 2026-11-14 and follow-up checkpoints. The author accepted the Codex A/B assistance cases and seven additional boundary cases, and authorized release 0.6.0 on 2026-11-16. **Claude Code business-effect evaluation is deferred by the author; cross-host behavioral acceptance is not claimed.** Release scope for CC is basic loading and shared helper entry support. All 48 historical first attempts and their failures remain recorded; later acceptance does not rewrite them. The same five Skills retain their existing roles; no new agent, hook or permission preset is introduced.

## Implemented behavior

All five Skills share intent and analysis contracts rather than maintaining separate scientific specifications. `METHOD_REVIEW` supports learning and comparing methods without requiring data or project initialization. `CANDIDATE_ANALYSIS` supports authorized calculation with documented assumptions, without requiring advance adoption of every field interpretation or a formal software choice. `FORMAL_ANALYSIS` requires the adopted specification and authoritative source. `VERIFICATION` checks that specification without replacing it. Unresolved ambiguity that prevents meaningful computation must still be resolved.

The controlled Python runner implements six methods: `descriptive`, `scale_score`, `welch_t`, `student_t`, `paired_t` and `pearson`. Method learning is open beyond this executable list: the model can investigate an unfamiliar method and assess applicability, evidence and implementation requirements. A recommendation does not establish executable backend support. Formal source selection remains authoritative; a Python runner cannot silently substitute itself for a selected external backend.

The shared specification records design, observation unit, field mapping, scoring, sample, model, inference and authorization. Results record analysis/result identity, scientific specification, input/specification hashes and execution provenance. Successful computation produces a candidate artifact; it does not adopt findings, alter the authoritative source or write manuscript files. Source data remain unchanged. Registry updates require the author's separate adoption confirmation and actual artifacts with matching hashes; hand-entered result claims alone do not satisfy that check.

Controlled-run registration uses the six-method result contract. External SPSS/R/Python or other author-selected analyses use `external_analysis`, binding the scientific specification, actual code/output files and hashes without a software, method or extension whitelist. An optional verification source may use different software, with its own real output and hash. External entries remain `AUTHOR_ATTESTED`, `EXTERNAL_ARTIFACTS_REGISTERED_NUMERICS_UNVERIFIED` and `NOT_ASSESSED`; recorded roles do not prove numerical agreement or actual execution. Missing verification code remains explicitly unverified. This restores existing external-source registration without pretending that the controlled runner implements those methods.

Runtime preflight checks the actual input, dependencies and authorized output scope. Legacy preflight no longer treats a structurally complete specification as executable `READY_FOR_ANALYSIS`; structural readiness and runtime readiness are different evidence. Dependencies are optional and no missing package is automatically installed. The local environment did not have R or statsmodels; no R/statsmodels execution is claimed.

Comparisons preserve the formal source, require matching scientific specifications and result identities, and distinguish specification changes from numerical discrepancies. Same-engine reproduction is explicitly labeled and is not an independent verification. Sample counts must match exactly. Ordinary numerical fields use the caller's absolute tolerance; p values use relative tolerance `1e-6` with zero absolute tolerance, so a blanket absolute tolerance cannot conceal a materially different tiny p value.

## Developer interface examples

From the repository root, inspect capabilities and submit a specification using the shared interfaces:

```powershell
python -X utf8 scripts/analysis_runner.py methods
python -X utf8 scripts/analysis_runner.py methods --method paired_t
python -X utf8 scripts/analysis_runner.py preflight --spec "<spec.json>"
python -X utf8 scripts/analysis_runner.py run --spec "<spec.json>"
python -X utf8 scripts/compare_analysis_results.py --authoritative "<formal-run.json>" --verification "<verification-run.json>" --tolerance 1e-6
```

Specification paths for source data and output scope must be explicit absolute paths in the local case. Use a dedicated output directory outside source data, manuscript and plugin locations. The actual author request supplies authorization; a Boolean in a specification is not evidence of consent. Load the authoritative Skill manifests through `scripts/load_skill_resources.py` for the current detailed contract rather than copying rules from this summary.

## Evidence obtained

- **Repository regressions:** the 2026-11-15 suite before the analysis-opportunity guidance passed **253 tests in 31.656 seconds**, including four field-query checks. The prior 249/252-test runs and 192/243/246 counts are historical checkpoints. The later guidance-only increment is recorded below. Test counts and elapsed times are not evidence of universal statistical correctness or improved model efficiency.
- **Numerical references:** independent Wolfram calculations were actually obtained for representative Welch, Student and paired t tests and Pearson correlation, including representative two-sided p values and confidence intervals. Hand calculations checked descriptive summaries and reverse scoring. This supports the tested examples; it does not validate every dataset, tail behavior, assumption, missing-data case or statistical method.
- **Claude Code:** the CLI bundled with the VS Code Insiders Claude Code extension reported `2.1.312 (Claude Code)`. Running `plugin validate <development-repository> --strict` actually returned `Validation passed`, exit 0. It also reported a directory icon warning and marketplace-install advice that explicitly did not change the verdict. Authentication status reported a logged-in first-party OAuth session; no identity or credential values are included here. Authentication availability is not a successful model call.
- **Codex discovery:** `codex-cli 0.169.0-alpha.11.1` actually rendered all five local Skill paths with `debug prompt-input` in an independent controlled repository. No model was called for this discovery check. The layout was `.agents/skills/<skill-name>`, `.agents/skills/.shared` and `.agents/scripts`, preserving relative loader paths. This proves initial discovery in that execution environment, not subsequent Skill use or computation. A different execution identity must recheck its actual Skill list for duplicate installed versions.
- **Additional static validation:** the initial five official `quick_validate.py` attempts lacked PyYAML. A later, explicitly authorized 2026-11-15 check installed PyYAML 6.0.3 only in a temporary isolated virtual environment; all five official Skill checks returned `Skill is valid!`, exit 0. The original Python still has no PyYAML. This is basic Skill format validation, separate from repository tests, CC packaging or scientific/host behavior.

## Claude Code packaging and pending host acceptance

The minimal `.claude-plugin/plugin.json` uses name, version, description, author, repository and license. Claude Code discovers the existing root `skills/` directory by default. Codex interface metadata stays in `.codex-plugin/plugin.json`; no Skill tree is duplicated for Claude Code.

```powershell
claude --version
claude plugin validate . --strict
claude --plugin-dir "."
```

The last command opens an interactive host session and is separate from local manifest validation. Actual host acceptance must establish discovery, routing, loading, authorization boundaries and requested behavior. The fixed 24 cases were attempted in both hosts: **48 first-attempt receipts exist**, with their original inputs, prompts, tool traces and failures retained privately. No evaluation rubric was supplied to the tested models. Labels are source-informed internal assessments, not external expert annotations.

First-attempt process outcomes were Codex: 23 exit-0 results and one timeout; Claude Code: 15 exit-0 results, one timeout, one authentication failure and seven API 402 insufficient-balance interruptions. Exit 0 does not mean scientific or workflow acceptance. In Codex G12, the stream contains a complete answer and `turn.completed` despite the timeout receipt and empty native final file; the process/collection mismatch remains an execution issue, not a numerical failure. CC G12 completed calculations but did not deliver a final interpretation before the time limit.

First attempts and targeted retests are recorded separately. The first Claude Code attempt could not authenticate under restricted configuration; its normal logged-in configuration then exercised the plugin. The first Codex attempt could not read local resources under its chosen policy; an automatic-review workspace configuration subsequently loaded them. These infrastructure failures are not successful plugin trials. Approval is never bypassed. Claude Code allow-lists add preapprovals and do not override existing user permission settings; they are not a complete sandbox.

The two hosts use the same frozen plugin core and case data. Their configured models and available tool sets differ: observed Claude Code responses report `deepseek-v4-pro`; Codex uses the user's `gpt-6-astra` configuration. This checks these concrete host/model combinations, not an isolated causal effect of host choice and not a Claude-model scientific review. Runtime logs distinguish actual plugin use, computation, scientific reasoning and file preservation. Correct numerical output alone does not establish correct interpretation.

## First-attempt behavioral findings

In the table, Pass is scoped to the case's supplied evidence and requested task; Partial includes an identified issue. Not assessed means the service did not deliver enough content. Input hashes stayed unchanged in all 48 attempts. Neither host adopted a candidate as formal or edited a manuscript. These observations do not prove a complete operating-system sandbox: CC G13/G14 attempted a receipt write with another tool after a denial, and both attempts were denied.

| Case | Codex content / execution | Claude Code content / execution |
| --- | --- | --- |
| G01 Cross-sectional inference | Content pass; local-resource access failed | Authentication failed; content not assessed |
| G02 Repeated design | Pass / pass | Core pass with overbroad ancillary advice / loaded |
| G03 Hierarchy | Pass / pass | Partial: incorrect group level and unsupported sample adequacy / loaded |
| G04 Analysis choice | Pass / pass | Partial: complexity and fixed power rules / loaded |
| G05 Missingness | Pass / pass | Partial: MAR and imputation claims too definite / loaded |
| G06 Scale versions | Pass / pass | Fail: missing-response problem changed into missing-item problem / loaded |
| G07 Coding | Pass / pass | Partial: coding and trend equivalence overgeneralized / loaded |
| G08 Small sample | Pass / pass | Core pass with absolute power/exploration claims / loaded |
| G09 Reproduction | Pass / pass | Partial: same-engine work called independent / computed |
| G10 Method learning | Pass / pass | Partial: exact-Wilcoxon applicability overstated / computed |
| G11 Alternative comparison | Pass / pass | Partial: wrong W+ label in JSON and nongeneral rank code / computed |
| G12 Exploratory value | Content pass / complete streamed answer, timeout receipt | Partial: symmetry-free robustness claims / computed, final answer absent |
| G13 Abstract support | Pass / recovered loading | Partial: prediction/generalization boundaries absolute / loading and denied-write recovery issues |
| G14 Counterevidence | Pass / pass | Partial: unknown significance/covariates/precision stated as facts / loading and denied-write issues |
| G15 Source lineage | Pass / recovered loading | Partial: source support expanded beyond supplied passage / loaded |
| G16 Handoff state | Pass / pass | Fail: NOT ADOPTED became REJECTED; project-A ceiling carried into B / recovered loading |
| G17 Translation | Pass / pass | Content pass / wrong initial path and unsubstantiated registration claim |
| G18 Tense and voice | Pass / pass | Not assessed / API 402 after partial loading |
| G19 Terms and numbers | Pass / pass | Not assessed / API 402 after partial loading |
| G20 Local edit | Pass / pass | Not assessed / API 402 |
| G21 Citation distribution | Pass / pass | Not assessed / API 402 before input reading |
| G22 Journal dialogue | Pass / pass | Not assessed / API 402 before input reading |
| G23 Irrelevant citations | Pass / pass | Not assessed / API 402 before input reading |
| G24 Cross-project scope | Pass / pass | Not assessed / API 402 before input reading |

The synthetic paired data's t test and exact sign enumeration were actually computed: mean change 2, t(5) = 5.4772255751, two-sided p = .0027649603, 95% CI [1.0613562285, 2.9386437715]; 64 sign assignments give p = .03125 under the stated sign-symmetry null. Equal p values do not make the mean and sign hypotheses identical. One generated CC G11 artifact mislabeled min(W+, W−) = 0 as W+; the actual positive-rank sum is 21. These generated artifacts are retained as failed evidence, not promoted into the plugin's backend.

## Repairs, retests and remaining limits

Code defects were repaired with failing regressions first: invalid/empty results, incomplete identities and uncertainty fields, unknown options, inconsistent formal-source provenance, input/output scope, registry binding and external-source compatibility. Prompt conflicts were consolidated in existing resources: standalone consultation is not blocked by manuscript setup; candidate calculation does not require adoption; software is execution provenance rather than scientific identity. No fixed writing sequence or additional agent layer was added.

Thirteen retests are separate from the 48 first attempts: three address initial host setup and ten use separately hashed `core-v3`. They never overwrite first attempts or change the 24-case quota. Codex G01 now reads the intended inputs/resources and preserves unknown significance and scale direction. CC G01/G03/G04/G05/G06 all load resources, but none qualifies for unreserved behavioral acceptance: invented significance/randomization, mechanical analysis rules and the missing-response misreading persist. Some earlier sample-size and hierarchy claims improved; that is partial improvement, not resolution. CC retests G09/G10/G12 ended with API 402; repairs for independence wording, exact-method conditions and redundant bookkeeping remain unverified there. No automatic retry follows the balance errors.

The initial G12 workflow also expanded unnecessarily: Codex generated 61 output files and CC started a full audit ledger after calculation. Existing provenance-reuse guidance was tightened in place, without a new record system or fixed artifact quota. Codex G12's v3 retest completed in 561.3 seconds, exit 0, with a complete answer and 28 hash-matched artifacts. Content, computation and permissions passed internal review. Statistical subprocess calls fell from 27 to 18 and redundant ledgers disappeared, but shell calls rose from 15 to 20 and cumulative input-token usage stayed similar. Record reuse improved; overall loading/time efficiency is **not resolved**. This is a single targeted observation, not a performance benchmark.

| Capability | Evidence obtained | Boundary / outstanding work |
| --- | --- | --- |
| Six controlled Python methods | Actual runner tests; independent representative t/correlation references and hand-checked summaries/scoring | No claim for all inputs, mixed models, regression, bootstrap or R execution |
| Candidate output and adoption separation | Negative contract tests, registry tests and unchanged real-case inputs | Host must establish actual user authorization; a supplied Boolean is not consent |
| External formal/verification records | Actual artifact/hash/role tests, optional verifier retained | Author-attested provenance; external numerical agreement remains unverified |
| CC packaging and resource use | Actual strict CLI validation and successful Skill/resource calls | Current configuration has substantive behavioral failures; not production acceptance |
| Codex case use | Actual requested workflows with explicit first-attempt access/collection failures | Final-v3 coverage is targeted, not a second full 24-case run |
| Cross-host release readiness | First attempts retained and internally reviewed | Not passed; unresolved behavior and service-blocked cases remain |

No raw host logs, account details or research data are distributed with this document. The private optimization log holds local evidence paths, current decisions and remaining work. A resumed evaluation must identify its configuration and affected cases; it must not replace failed first-attempt records or imply an untested model behaves the same way.

## 2026-11-15 offline follow-up

No CC or Codex model run was started. The follow-up deliberately separates three causes:

- **Plugin interface gap:** `methods` exposed names without a concise field description; an observed G12 run read 29,244 characters of implementation source. `methods --method <name>` now returns 1,040–1,161 characters, sharing model-field and role definitions with validation. It neither recommends a method nor authorizes/runs one. A query works with `python -S` and writes nothing. Scoring metadata remains compatible: outside `scale_score`, mapped values are used without re-scoring. Existing conditional guidance explains that `run` already checks inputs/runtime; separate preflight is optional diagnosis. Default resource loading and the numerical backend are unchanged. Lower interface volume is measured; improved real-host cost/time is not yet demonstrated.
- **Evaluation harness defects:** the temporary harness formerly counted error text as an available final answer and ignored completed streamed Codex answers when the native final file was empty. It now records protocol completion, answer availability and process status separately. A shared per-host lock coordinates final dispatch with service-stop transitions, including tasks still preparing; already-running jobs remain separately recorded. Calls default to serial, with parallelism only when explicitly selected. Seven mocked/offline tests cover classification and stop propagation. Replaying all 61 retained records identified 11 API errors without answers and the one Codex process/protocol mismatch. All 182 original receipt/stream/final files were hash-identical before and after replay. These are test-facility repairs, not statistical-plugin fixes or new successful host attempts.
- **Execution deviations:** G06's question misreading, G16's state/project carryover, invented significance and denied-write tool switching already conflict with loaded instructions. No case-specific writing or statistics rules were added. Read-only tasks interacting with file-based receipts remain a possible interface friction, not an established cause of the tool-switching behavior; permissions were not relaxed.

The field interface and local harness fixes passed offline checks; CC behavior, permission recovery and end-to-end loading efficiency remain pending controlled retests after service recovery. The initial PyYAML installation failures were later traced to socket permission error `WinError 10013` when reaching PyPI, not package incompatibility. An approved download obtained the matching Python 3.12 Windows wheel from PyPI; its SHA-256 matched published metadata. Offline installation into a temporary virtual environment resolved the dependency and all five official Skill format checks passed. The checker and 217 plugin files were unchanged during validation; the original Python package inventory remained unchanged and could still not import yaml. The private optimization log retains exact paths and receipts. No CC/model calls were made. The separately documented legacy `plugin-creator/scripts/validate_plugin.py` path is absent locally and is not claimed to have run. No global environment, installed plugin, frozen host core, original case output or manuscript was changed.

## Analysis-opportunity guidance, 2026-11-15

The existing analysis entry/core and conditional method-learning resource now prompt agents to notice relevant information left unused by an analysis, without waiting for the author to name another model. The existing task-routing row includes that purpose. Guidance favors explanatory value and design/data fit, preserves narrow requests and author adoption, and adds no backend, selector or mandatory search workflow.

The final complete suite passed **254 tests in 32.303 seconds**; an earlier 254-test run preceded a clarification preserving computation authorization. The added test checks optional loading, deduplication and character budgets, not scientific judgment. The modified analysis Skill passed the official basic validator in the existing temporary environment; diff checks passed. Runner, contracts and backend hashes did not change in this increment.

Default analysis resource text decreased from 2,341 to 2,140 characters. Including optional method learning changed 6,344 to 6,383; including the entry as well changed 7,923 to 7,895. Other Skills' default resource costs stayed unchanged; the existing optional routing row grew by 18 characters. These are character measurements, not observed token or runtime improvements.

Business simulations have **not run**. Proposed synthetic inputs and the run plan are awaiting the author's review; the author judges the usefulness of the actual responses. The prior host trials do not validate this new guidance. No simulated dataset was generated or model service called in this increment.

### Follow-up: design understanding before opportunity discovery

The author rejected an over-prompted simulation request that explicitly asked for statistical review. Proposed cases ROUTE-014/015 now start only with `帮我改这篇论文` and a synthetic manuscript; retained raw or summary data are supplied later in response to the agent's own relevant questions. Both remain `AWAITING_AUTHOR_APPROVAL`, with the author as business judge. No case has run and no dataset has been generated.

The existing default router and direct writing/review entries connect design understanding to read-only method support. The analysis core checks how observations arose, which records were retained, and which information the reported analysis used or aggregated. Old explicit-request-only and no-analysis-handoff statements were narrowed without granting computation, adoption or manuscript edits. The same resources and backends are reused.

Two technical regressions first exposed missing proposal records and the conflicting writing gate. The complete suite then passed **256 tests in 34.458 seconds**. These checks validate input/status contracts and removal of blocking statements, not model judgment. The two changed Skill entries passed the official basic validator in the existing temporary environment; diff checks passed. Router default resource text changed 1,644→1,609 characters; analysis core 2,140→2,248; core plus conditional method learning 6,383→6,330. Other professional default resource bodies were unchanged; entry text also changed, so these are not total-token or speed claims. Numerical implementation hashes were unchanged.

External double-blind review, remote release and daily plugin installation are outside this development stage and have not been performed.

The local wrapper follows the official [Claude Code manifest reference](https://code.claude.com/docs/en/plugins-reference). Repository-scoped Skill discovery follows the official [Codex Skill documentation](https://learn.chatgpt.com/docs/build-skills). These references explain configuration; the local CLI checks above supply the bounded runtime evidence actually obtained.


### Approved ordinary-request business trials, 2026-11-15

The author subsequently approved the two proposed cases. Earlier “not run” states above describe the pre-approval checkpoints. Both began with exactly `帮我改这篇论文` and the same synthetic manuscript, without statistical hints. Independent Codex CLI sessions used the development package, gpt-6-astra/ultra and retained general host collaboration settings, but not this project conversation or scoring rubric. Raw versus aggregate-only data were provided only after each agent's own relevant question.

Five turns ran: A had three, B two. A1/A3/B2 reached the 300-second cap without a complete final answer; A2/B1 completed. Both identified contrast information omitted by averaging. After reading data, A described a low/high-contrast reversal; B withdrew interaction/threshold suggestions because the available summary did not retain contrast. These are observed behaviors, **not business acceptance**. The author judges usefulness from the complete visible conversations, including scope questions, loading overhead and timeouts.

Six web calls returned five source texts, a blocked PMC entry and a 17-result keyword search; search-only hits were not labeled full-text reading. No new mixed model or psychometric fit ran. Original paired comparisons were recomputed. Latest recorded input across the two sessions was 3,268,652 tokens, of which 3,105,024 cached and 163,628 uncached; output was 27,162, including reasoning. Session cumulative totals were counted once. Timeout in-flight usage and orchestration overhead are not covered, so this is not a final bill or evidence of low cost.

Input/package hashes remained unchanged; 121 development runtime files still matched the frozen package. There was no paper edit, CC run, installation, release, prompt repair or business retry. The existing private optimization log records exact artifacts, startup-network interruption, fixture newline issue, loader errors and remaining uncertainty. Business status is awaiting the author's judgment; no rule changes are inferred automatically from individual model errors.


The author subsequently rejected wall-clock limits for manuscript-assistance business tasks. The 300-second cutoff was imposed by the temporary trial harness, not the plugin or an author requirement. It has now been removed from that harness; only elapsed time is recorded. Historical timeout artifacts remain unchanged and cannot establish inability to finish. This correction involved local syntax/path checks only, with no further model trial or manuscript change.


### Same-session continuations completed, 2026-11-15

The author authorized finishing the interrupted responses without a business time limit. A resumed its original thread as turn 4; B resumed its original thread as turn 3. Both received only `请接着完成上一轮尚未交付的答复。`, with no new statistical hint, input or plugin change. Both naturally completed and emitted final answers (A 176.20 seconds; B 74.88 seconds). A produced contrast-wise descriptive tables/plots and participant-bootstrap pointwise intervals, while leaving mixed/psychometric modeling as candidates. B completed the aggregate comparison and revision advice without reconstructing unavailable contrast information. No new web calls occurred during continuation.

All prior turn files, inputs and frozen runtime hashes were unchanged; returned session IDs matched the originals. Complete visible transcripts include all 10 A messages and 9 B messages, plus author replies and interruption history. Latest cumulative input was 4,323,619 tokens (4,150,656 cached; 172,963 uncached), output 33,269. Relative to the last recorded interruption checkpoints, continuation added 9,335 uncached input and 6,107 output; these are telemetry, not a complete bill. No manuscript, installed plugin, global environment or core prompt was changed. Protocol completion is confirmed; business usefulness remains for the author to judge.


### Author acceptance and local integration, 2026-11-15

The author explicitly accepted both completed ordinary-request simulations and authorized integration into the currently used Codex plugin. ROUTE-014/015 now record AUTHOR_ACCEPTED, with the author remaining the business judge. This acceptance covers these two observed cases; previous statistical and Claude Code failures remain open.

The tested Codex skills/scripts and their existing dependency closure were merged unchanged into the main local source, local marketplace package and enabled installation on the 0.5.2 baseline. There are 27 runtime-file differences from the previous installation; no new runtime rule, Skill, workflow or backend was added during integration. The existing Claude manifest remains package metadata, not a Claude Code installation or a successful CC trial. No remote release or GitHub push was performed.

The merged source passed all 256 regression tests (30.887 seconds), and all five installed Skill entries passed the official basic validator. Each installed default resource set, conditional method-learning load, duplicate-selection reuse and compact paired-test contract were checked from the installed path. These local checks do not replace the author's business decision or prove every statistical implementation accurate. The private optimization log and local integration receipts retain backups, hashes, exact installation paths and unresolved items.

## Release 0.6.0 acceptance and checks, 2026-11-16

The author spot-checked and accepted seven additional ordinary-request cases: an independent-groups experiment with a copied response-code definition; a within-subject crossover misanalyzed as independent groups; a mixed design with difficulty mistaken for a batch field; a longitudinal intervention linked by unstable export rows; a cluster-randomized classroom experiment; a literature review counting multiple reports as independent studies; and a theoretical review treating mechanism and boundary conditions as mutually exclusive. Each first request was exactly `帮我改这篇论文`. Five experiments had two turns each, with factual replies and retained files supplied only after relevant agent questions; both reviews completed in one turn through their own source checking. No statistical hint or evaluation answer was supplied to the agent.

All 12 turns naturally completed in independent case sessions using Codex CLI with gpt-6-astra/ultra. There was no business time limit. The synthetic drafts, source observations and 121 non-cache runtime files per case were unchanged during the conversations. Preparation corrections and unsuccessful infrastructure starts were retained separately before valid answers, rather than overwritten or graded as business results. General host collaboration settings remained present; the cases do not establish performance for other models.

Observed work included coding and dependency checks, data-structure inspection, longitudinal identity repair checks and descriptive summaries, literature checking and justified analysis suggestions. The new candidate models were not fitted in these cases; author acceptance does not validate their implementations or establish general numerical accuracy. Complete private transcripts, tool traces and source-access records were provided to the author. They are not distributed as manuscript data or public evidence of universal capability.

The author explicitly deferred CC business-effect evaluation and further paid CC trials. The release instead checks basic loadability: Claude Code 2.1.312 returned `Validation passed` from `plugin validate . --strict`; `claude --plugin-dir "." plugin details psychology-paper` discovered version 0.6.0 and the five existing Skills. The shared analysis-resource loader and compact paired-test contract query returned successfully. These commands made no CC model call. Historical successful and unsuccessful CC executions above remain historical; broad cross-host behavior has not been accepted.

The release source passed 256 repository tests (31.626 seconds) and five official basic Skill validators, with dependencies reused from the existing temporary validation environment. A separately invoked repository diff check passed; an earlier Git invocation launched from the Python check wrapper failed to recognize the repository and is retained as a wrapper issue, not a regression failure. These checks validate release structure and the bounded tested behavior, not scientific quality or every statistical method. No new Skill, workflow, computation backend or global dependency was added while preparing this release.

## Direct-analysis development, 2026-11-16 — not a release

The author subsequently approved five bounded analysis families, optional R execution, named implementation paths, exploratory-origin records and attempt summaries. Development is on `codex/direct-statistics`, based on release commit `fc2be78c0eb2d5a109e7bbd9495486e321d664aa`. Installed/released version 0.6.0 is unchanged. This later approval supersedes the earlier no-new-backend boundary for this scoped extension only. No manuscript, paid CC trial, business simulation, installation update, commit or publication was performed in this development step.

The existing runner now dispatches 13 additional method identifiers to five lazily sourced R files. Existing Python methods remain unchanged. AnalysisSpec v3 and AnalysisRun v2 preserve analysis origin separately from statistical parameters; v2/v1 records stay readable with unknown historical origin. Successful, failed and interrupted authorized v3 attempts use the original candidate run directory. Missing dependencies do not trigger installation. Source files are hash checked; outputs remain candidates. Adoption preserves origin, and comparisons now include model fit summaries while ignoring output-row order.

**Local numerical environment:** Windows x64 UCRT, R 4.6.2; jsonlite 2.0.0, afex 1.5.1, car 3.1.5, emmeans 2.0.4, sandwich 3.1.3, lme4 2.1.0, lmerTest 3.2.1, lavaan 0.7.3 and detectseparation 0.4.0. R was extracted and packages installed only in a temporary verification environment, with process-local library/locale configuration. No global R/Python installation, registry or PATH change. The dependency JSON records tested top-level versions, not a complete transitive lockfile. The local setup receipt retains installer provenance, hashes, package inventory and session information.

**Final code run:** 289 repository tests passed in 101.617 seconds with the optional R environment enabled, including 18 R numerical/boundary tests in `tests/test_analysis_methods.py`; none of those 18 were skipped. Five official basic Skill validators and `git diff --check` also passed. Test counts are coverage records, not evidence of universal statistical correctness. Relevant evidence is:

| Checks | Reference and practical limit |
| --- | --- |
| OLS and HC3 | Independent NumPy matrix estimates and covariance; coefficient/SE absolute tolerances at 1e-10. |
| Binomial and Poisson regression | Independent SciPy likelihood optimization, coefficient tolerance 1e-6; analytic two-group checks for binomial denominators and log offsets. |
| ANOVA | Hand F/partial eta squared; unbalanced II/III projection calculations; repeated-measures sums of squares; HF epsilon calculation; mixed GG design; four contrasts in one Holm family. Statistical comparisons are checked to 1e-7 or tighter where declared in tests. |
| Mixed models | All three families execute; balanced random-slope LMM fixed slope matches the mean of independent per-group OLS slopes to 1e-6; crossed groups and ML nested LRT share observations and satisfy the likelihood/chi-square identities. These checks do not independently validate every GLMM variance/SE or Satterthwaite calculation. |
| Mediation/moderation | Parallel indirect point estimates against independent OLS path products (1e-5); seeded bootstrap repeatability; conditional moderation slope against an uncentered matrix fit (1e-7). A 40-replicate bootstrap is a fast code test, not a recommended scientific analysis. Repeatability is not independent CI coverage validation. |
| CFA/SEM | Three-indicator ML loadings match the independent covariance identity to 1e-5. MLR/FIML and ordered WLSMV execute through the wrapper; unidentified models are rejected and saturated-model fit indices are explicitly marked non-informative. Robust/WLSMV SE and fit calculations are delegated to lavaan and have not all been cross-validated in another engine. |
| Failure and contract behavior | Rank deficiency, separation, missing observations/conditions, duplicate repeated cells without explicit aggregation, missing declared factor levels, unusual/numeric labels, permissions, legacy origin, failed attempts, malformed neighboring records, incomplete output and adoption-origin changes. |

The implementation was corrected in response to actual failing tests: raw and adjusted contrast p values were separated; declared ANOVA factor levels can no longer disappear silently; no-intercept factor coverage and numeric factor labels were repaired; malformed attempt neighbors no longer destroy summaries; coefficient completeness is checked independently of the backend inventory; fit-summary comparison no longer treats row reordering as a discrepancy. These were code defects, not reasons to add new author-facing rules.

Default analysis resource length is 2,298 characters, compared with the approved 2,248-character baseline (+50). Five separate method resources are selected only on demand, each below 3,000 characters; no new Skill/Agent/workflow layer is added. Existing staged reads remain necessary if optional resources together exceed the original 12,000-character ceiling.

Windows/Ubuntu R numerical jobs and a smaller macOS representative job are configured in CI, but have **not run remotely** in this step. They must not be cited as cross-platform acceptance. The author has not evaluated the new five-family business behavior; proposed cases remain in the private optimization log pending approval. CC effect evaluation remains deferred.

Primary implementation references include [afex ANOVA documentation](https://cran.r-project.org/web/packages/afex/refman/afex.html), [lme4 model-comparison documentation](https://lme4.github.io/lme4/reference/merMod-class.html), and the method-specific official references in the five conditional resources. In particular, different fixed-effect structures are compared only using explicitly requested ML; the wrapper does not silently refit REML. Documentation capability is separate from the numerical evidence listed above.
