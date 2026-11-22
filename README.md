# Psychology Paper

**Codex 最低建议使用配置 / Minimum recommended Codex configuration:** **GPT-5.6-Sol** (`gpt-5.6-sol`), **medium** reasoning effort（中等推理强度）. Claude Code has no evaluated model minimum yet.

Early-stage research assistant. Current release: **0.7.0**. This release extends direct statistical analysis, literature search and the author's personal library. Previous releases remain available from the [release archive](https://github.com/hmy77100-max/psychology-paper/releases).

Psychology Paper supports evidence-calibrated psychology manuscript work in Codex and Claude Code. It diagnoses the task, learns the target journal's writing style, audits the manuscript against the study design, prepares bilingual revision candidates, and supports reproducible quantitative-analysis reconstruction. Authors can keep readings across manuscripts and look up highlights in local Zotero. The plugin does not modify source data or manuscript files.

Version 0.6.0 connects understanding the research design to noticing useful information in retained data, shares analysis contracts and controlled statistical helpers across the existing modules, and packages the same five Skills for Claude Code. Existing installations need an explicit update. Author decisions govern analysis adoption and manuscript changes; no fixed argument or preferred model is imposed.

The author accepted two ordinary-request simulations on 2026-11-15 and seven additional boundary scenarios on 2026-11-16, covering five experimental designs, an empirical literature review and a theoretical review. These observed Codex sessions support the accepted assistance behavior, not every method's numerical accuracy or other models' performance. Claude Code business-effect evaluation is deferred by the author; release checks cover basic plugin discovery and loadability without paid model calls. Historical failures and the scope of these checks remain documented in [the validation record](docs/validation/global-statistics-cc.md).

## Minimum performance for author-facing work

The project owner set **GPT-5.6-Sol at medium reasoning effort** as the minimum performance benchmark for author-facing work. The benchmark concerns what an author experiences on an ordinary request. For example, when an author keeps consulting one paper, the assistant should answer the research question first, notice when keeping the paper would help, and offer to save the available version. The author chooses what to keep. A successful save leaves a record the author can retrieve in another project.

In the observed Sol session, the assistant offered after its first substantive answer, waited for consent, and saved the selected PDF. The recovered copy matched the original. GPT-5.6-Terra (medium) answered all three research questions in its own case and loaded the reminder, but never offered to save the paper. The owner marked that initiative behavior below the benchmark. GPT-6-Luna (medium) also missed the offer in its tested case. These observations cover the personal-library task. Other modules and models need their own evidence for claims about performance.

## Implemented modules

- `psychology-paper`: routes the request and maintains authorization boundaries.
- `journal-fit-style`: profiles the manuscript, evaluates journal fit, and learns journal writing patterns at light or deep depth.
- `evidence-audit`: reviews the paper with design-appropriate checks, targeted external-source verification, and evidence-grounded advice within the requested scope/risk threshold.
- `manuscript-writing`: prepares section-specific Chinese, English, or bilingual candidates within the author's scope and the available evidence.
- `analysis-adapter`: supports method review, authorized candidate computation, formal analysis and verification through a shared analysis contract; preserves separate computation, result-adoption and manuscript-editing decisions.

One module is primary for each task. Other modules receive only the smallest necessary handoff, preferably a file path and exact location rather than duplicated manuscript text.

## Review evidence support

Review-only requests go directly to `evidence-audit`, including whole-paper review. Existing article/journal profiles and project memory are reused selectively; no second journal-positioning workflow or mandatory project setup is introduced. Six internal responsibilities organize review, not six new agents or Skills. The model remains responsible for scientific judgment and may recommend a different journal, argument, analysis or experiment; the author chooses adoption.

For material external questions the model uses available browsing/retrieval tools to check original sources, versions and applicability. It records inspected support, competing evidence and access limits. Offline requests and unavailable full texts produce bounded findings. The author can save a selected candidate for use in another project.

The optional `python -X utf8 scripts/review_evidence.py --record -` command reads a JSON evidence note from stdin and checks provenance-field completeness without writing files. `record_complete` never means scientific verification. Review ends at feedback; a later editing request asks full versus targeted revision only when scope is unspecified, then follows the existing revision workflow. Agreement with advice alone does not start editing.

Review responsibilities and external evidence support are implemented. Methods review and quality/continuity guidance now cover: unit/analysis comparability, error-versus-gap classification, duplicate/conflict reconciliation and evidence-based closure/reopening. `scripts/review_quality.py --record -` optionally checks model-authored issue records without writing state or making scientific judgments. Records can remain in the conversation and reuse existing project memory. Contribution/journal comparison (step 4) now distinguishes official requirements, observed publication practices and model inference while preserving confirmed context. Revision advice (step 5) organizes meaningful options by benefits, unresolved evidence, feasibility and dependencies. These are conditional review resources, not repeated positioning, a decision engine or automatic editing. All six planned responsibilities now have an initial implementation; longitudinal real-manuscript evaluation remains future work.

## GitHub distribution and another Codex computer

The supported distribution scope is deliberately narrow:

- A private GitHub repository may store the source. A second computer must have permission to clone that repository.
- A public GitHub repository may store the same source after the portability and privacy checks pass.
- The plugin may run on another computer with Codex by cloning it into a configured local marketplace and installing it through the Codex plugin command.

The repository remains a Codex plugin and is not intended to run independently of Codex. Publishing the source does not upload manuscripts, project-state files, or research data unless a user separately adds those files to the repository.

On the destination computer, create or choose a local marketplace root, clone the repository into its plugin directory, and make sure the marketplace manifest points to `./plugins/psychology-paper`:

```powershell
git clone https://github.com/hmy77100-max/psychology-paper.git "<marketplace-root>\plugins\psychology-paper"
codex plugin marketplace add "<marketplace-root>"
codex plugin add psychology-paper@<marketplace-name>
```

The marketplace manifest is `<marketplace-root>\.agents\plugins\marketplace.json`. Its marketplace name supplies `<marketplace-name>`. A private GitHub repository requires Git authentication before cloning; a public repository does not. Start a new Codex task after installation so the newly installed Skills are discovered.

## Claude Code

### Install from GitHub

In Claude Code (including the VS Code extension), run these commands one at a time:

```text
/plugin marketplace add hmy77100-max/psychology-paper
/plugin install psychology-paper@psychology-paper-github
```

Choose the user scope for access across projects. Open a new Claude Code session in your paper project. Type `/psychology-paper:psychology-paper` and add your request to start. Sending that request uses your model account.

To install and inspect the plugin from a terminal, run:

```sh
claude plugin marketplace add hmy77100-max/psychology-paper
claude plugin install psychology-paper@psychology-paper-github
claude plugin details psychology-paper
```

The details command lists the installed skills without sending a prompt. Launch `claude` from the project directory when you are ready to work.

### Load a local copy for one session

The repository contains a minimal Claude Code manifest at `.claude-plugin/plugin.json`. Claude Code uses the existing root `skills/` directory by default, sharing the five Skills, resource manifests and Python helpers with Codex. The wrapper adds no agents, hooks, permission presets or duplicated Skill tree. Codex-specific interface metadata stays in `.codex-plugin/plugin.json`. Both manifests declare version `0.7.0`.

From the cloned repository root, use an installed Claude Code CLI for local manifest validation:

```powershell
claude --version
claude plugin validate . --strict
```

Load the cloned or extracted plugin in a fresh Claude Code session:

```powershell
claude --plugin-dir "."
```

To inspect the loaded component inventory without a model call:

```powershell
claude --plugin-dir "." plugin details psychology-paper
```

Claude Code 2.1.312 has discovered all five Skills from this shared tree using that command. The shared Python loader and method-contract query are also checked locally; earlier CC host attempts exercised resource loading and calculations, with successes and failures recorded separately. These facts establish the bounded loading/entry support, not consistent scientific reasoning or equivalent business performance across hosts. No paid CC model evaluation is required for this release. Python and any optional statistics dependencies must be available in the user's environment; the plugin does not install them automatically.

The wrapper follows the official [plugin manifest reference](https://code.claude.com/docs/en/plugins-reference). The [GitHub marketplace](.claude-plugin/marketplace.json) points to this same plugin at the repository root.

## Deterministic resource loading

Every implemented Skill loads internal rules through `scripts/load_skill_resources.py`. The caller selects logical Manifest groups; the loader resolves exact declared paths relative to its installed plugin root and includes only that Skill's `always_load` resources plus the selected groups.

Runtime loading never enumerates directories, guesses similar filenames, or falls back to repository-wide search. Unknown selectors and invalid paths fail as bounded plugin-integrity errors. The default ceiling is 12,000 instruction-body characters per load; labels and JSON metadata are additional, so this is not a token limit or a bound on the serialized tool response. Build-time tests separately verify that every Manifest-declared resource exists.

Example:

```powershell
python -X utf8 .\scripts\load_skill_resources.py --skill manuscript-writing --select axes.task.local-edit --select axes.language.english --select axes.section.discussion
```

## Candidate output

For English manuscript revision, the default TXT order is:

1. Original English
2. Revised English
3. Chinese Translation

For Chinese manuscript revision, the required order is complete original Chinese, revised Chinese, and necessary notes. Chinese-to-English work includes the Chinese source, revised English, and a Chinese back-translation. Full manuscripts are processed in argument-complete logical units (which may cross layout paragraphs). The author may reply in their own words; no approval command or candidate-ID syntax is required.

## Author-led revision and literature support

Choose a literature source for the author's question. Crossref resolves DOI metadata, OpenAlex traces citations, and Europe PMC locates passages in covered open articles. PubMed filters health research by MeSH topic and publication type. arXiv retrieves computational-methods preprints, including a specified version. Start with a compact shortlist and retrieve details for selected papers. For Chinese scale adaptations and theses, the host browser can search CNKI when the site is accessible. The personal library can identify the copy the author recorded as read.

Results from different indexes can be compared locally. Matching records share one entry in the shortlist, with each source identified. Related preprints and conflicting citations stay visible for the author's decision. Ask “Save the second paper under sample-size justification” or, in a later chat, “Find the paper I kept on sensitivity analysis.” The personal library is created on first save at `~/PsychologyPaper/literature.sqlite3` and retains the edition, attachment and reading location. With Zotero desktop open and local communication enabled, the plugin can also return highlighted text, a separate comment and a link to that PDF annotation. [Library commands](skills/psychology-paper/references/literature-library.md)

When an author keeps coming back to a paper, Psychology Paper can offer to keep it for another project. The author chooses whether to save the citation or include an available PDF. The save receipt identifies the local library and what it kept. The library uses the author's disk space and requires no database server.

The author chooses the argument, theoretical role and revision order in the target journal's context. The plugin supplies sources, recommendations and consistency checks, not a compulsory paper outline. Body-first revision can reduce summary rework when it fits the author's plan; it is not a prerequisite for drafting or adopting an abstract. Stage checks report pending synchronization as `stage_notes`, while actual source, candidate and authorization errors remain blocking. Adopting one unit never approves the others; later content changes still invalidate dependent summaries. Recommendations compare relevant journal research and direct field predecessors; fit is not a novelty claim.

Introduction work prioritizes evidence supporting the research-question and hypothesis chain. Each recommended source needs a specific claim, verified support, evidence distance, incremental value, claim ceiling and deletion impact. Necessary caveats serve the chain without suppressing contradictory evidence. Existing search authorization is reused; citation adoption remains a separate author decision.

`scripts/revision_check.py` checks actual files, not caller-supplied success flags:

```powershell
python -X utf8 scripts/revision_check.py candidate --project-root "C:\path\to\project" --record "candidate-record.json"
python -X utf8 scripts/revision_check.py preflight --project-root "C:\path\to\project"
python -X utf8 scripts/revision_check.py stage --project-root "C:\path\to\project" --section introduction
python -X utf8 scripts/revision_check.py decision --project-root "C:\path\to\project" --record "candidate-record.json" --intent APPROVE_CURRENT --author-response "Use this version"
```

These are internal commands, not required author replies. Load `conditional_loads.revision_checks` through the manuscript-writing loader for the record contract and reuse it across unchanged units. Full-mode acceptance binds the standard project file, approved journal profile, actual source hash, author-confirmed framing and adopted counted baseline. After counted adoption, refresh the derived baseline before accepting another candidate. The checker returns proposed state; it never writes manuscript/state or judges scientific truth. Stage notes are planning advice, not a compulsory drafting sequence. Initialization/legacy structural validation alone does not mean full-revision readiness.

Task-scoped bilingual sync checks observed Chinese and English versions under standing authorization. It generates corresponding English candidates after an in-scope change; it is not a background watcher, automatic adoption or Word overwrite.

## Efficient resource execution

### Version 0.5.2: optional theory reasoning and source attribution

Journal contribution planning, evidence review and manuscript writing can select the same `shared_loads.theory_reasoning` resource for assumptions, competing predictions and interpretation. `shared_loads.theory_examples` is separate and optional. The agent judges need from the task; keywords and a fixed writing sequence are not required. Examples preserve synthetic facts and illustrate author choices, not mandatory paragraph patterns. These resources are absent from default loads.

Literature support and contribution planning reuse the existing targeted external-verification resource without invoking a full review. Source-specific claims receive brief original evidence and locators, keeping the actual version used distinct from its earlier developers and adapters. When only an abstract is available, retain useful affirmative recommendations with an abstract-level/full-text-unavailable label; adoption and further checking remain the author's decision. A source note is not a manuscript outline or proof that the scientific inference is correct. Version 0.5.2 also bundles a blue-teal and gold quill for the plugin listing and composer. Installing the release is separate from merging source.

### Version 0.5.1: shared author guidance and resource reuse

Router, direct writing and review entries use one short author-led core. It replaces overlapping stance instructions; section guidance describes what to consider without fixing paragraph order or adding a defensive conclusion. Scientific wording changes receive the necessary in-scope verification, not an automatic new audit workflow. Detailed prose diagnostics remain optional. The author decides substantive direction; factual accuracy and manuscript-file protection remain intact.

Keep ordinary bounded loads for short tasks. Do not create a staged-read cycle solely to avoid a short repeated prompt: plan and receipt metadata also cost context. When already using staged preparation, V2 receipts can reuse unchanged complete resources across modules and selector changes within one valid read context. Reuse existing content across subsequent paragraphs without calling the loader again merely to demonstrate that it was read.

### Version 0.5.0 writing and collaboration additions

Focused `conditional_loads.prose_diagnostics` adds concrete repairs, protections against over-editing and sample-based author-voice observations to manuscript-writing. It preserves the full source comparison, logical units, citations and statistical reporting; observations become lasting style rules only after explicit author approval. See [third-party notice](THIRD_PARTY_NOTICES.md).

The router's `conditional_loads.collaboration` handles explicitly requested perspectives, mixed feedback and revision-milestone checks. Names are configurable; there is no mandatory four-role exchange or independent agent panel. Existing project records retain scoped decisions, rejections, supersession and unresolved evidence separately. State is reported saved only after readback; revision completion requires checking the actual candidate against applicable decisions, not merely having discussed them.

These additions require installing version 0.5.0; merging source alone does not refresh an existing installation. See [pre-release validation scope](docs/validation/writing-collaboration.md).

Use the loader's `--list-selectors` for exact keys and `--describe` for complete per-resource costs, hashes and first overflow. For a multi-stage preparation, `--plan` deterministically separates core, task axes and requested conditional/shared groups without duplicate core output. Select all required groups, in preparation order; do not omit requirements to fit a load. Each stage stays within 12,000 instruction-body characters and contains whole resources; an oversized indivisible group fails for resource repair.

Example of planning the three supplementary groups implicated in the capacity failure (include the applicable task/language/section axes when planning a whole writing task):

```powershell
$stageArgs = @('--skill', 'manuscript-writing', '--context-id', 'current-task-read-1', '--select', 'conditional_loads.bilingual_sync', '--select', 'conditional_loads.revision_checks', '--select', 'conditional_loads.literature_support')
python -X utf8 .\scripts\load_skill_resources.py @stageArgs --plan
python -X utf8 .\scripts\load_skill_resources.py @stageArgs --stage 0
# After actually reading the complete output, record its explicit attestation.
python -X utf8 .\scripts\load_skill_resources.py @stageArgs --stage 1 --receipts '<task-temp>\resource-reads.json'
# Continue the remaining stage IDs from the plan; attest each complete read.
python -X utf8 .\scripts\load_skill_resources.py @stageArgs --check-coverage --receipts '<task-temp>\resource-reads.json'
```

When a delivery includes unread resources, it contains `content` and a `receipt_template` with `read_complete: false` and `output_ref: null`. Only after reading the entire untruncated output may the assistant append that template to the existing task-local JSON list, set `read_complete: true`, and name the actual output in `output_ref`. V2 templates include the originating skill, selectors and plugin root; their `resources` cover only bodies actually delivered. Retain earlier receipts for reused resources. The script never writes or confirms receipts itself. This internal bookkeeping imposes no response format or approval step on the author.

V2 receipts are validated by rebuilding their origin against the same context and plugin root, including the original manifest and resource hashes. The loader reuses only identical resource paths, hashes and lengths; unchanged resources can carry over to a new module or selector list. Legacy receipts remain valid only for their original plan. Lost context or changed origin files invalidates reuse; start with current instructions. Earlier ordinary loads cannot be silently converted into staged receipts.

Missing predecessors still block later stages. `load_stage` reports newly delivered `chars`, complete `stage_chars`, and `reused_chars`; a fully covered stage returns `ALREADY_ACKNOWLEDGED`, empty content and a null template, which must not be appended as a receipt. Coverage returns exit 1 / `INCOMPLETE` for pending reads, or exit 0 / `ACKNOWLEDGED` for complete caller attestations. It does not verify the output reference, comprehension, selection sufficiency, author approval or manuscript quality. See [author-led core validation](docs/validation/author-led-core.md) for scope and measured costs.

Failures return exit 2 with `ARGUMENT_ERROR`, `RESOLUTION_ERROR`, `BUDGET_EXCEEDED` or `READ_RECEIPT_INVALID`. Stop the failed invocation and correct its specific cause. Budget failure can transition to a metadata stage plan; it cannot justify raising the limit, guessing selectors or dropping required rules. Retain the simpler ordinary load for small tasks. See [stage validation](docs/validation/resource-stages.md) for verified scope and limitations.

Reuse source-hashed extraction records while returning to originals for disputed evidence. Ordinary prose does not require a fixed multi-agent team or repeated status polling. Do not economize by removing original comparison or factual verification.

See [0.4.0 validation and boundaries](docs/validation/author-led-workflow.md). Installing/updating the plugin in Codex is separate from merging the GitHub source.

## Project state

Long manuscript, reanalysis, revision, and submission tasks may use a small `.psychology-paper/PROJECT.md` state file. It records only the current authoritative manuscript, confirmed journal, approved decisions, authoritative analysis source, unresolved issues, and next step. It is not a copy of the chat or a version archive.

Create state only with explicit confirmation:

```powershell
python -X utf8 .\scripts\init_project.py --project-root "C:\path\to\manuscript-project" --manuscript "C:\path\to\manuscript-project\paper.docx" --confirm-create
python -X utf8 .\scripts\validate_project.py --project-root "C:\path\to\manuscript-project"
```

The template never overwrites an existing project state.

Initialize an analysis registry only after entering project mode:

```powershell
python -X utf8 .\scripts\analysis_registry.py init --project-root "C:\path\to\manuscript-project" --confirm-create
python -X utf8 .\scripts\analysis_preflight.py --spec "C:\path\to\analysis-spec.json"
```

Choose the intent first: `METHOD_REVIEW` needs no dataset or formal source; `CANDIDATE_ANALYSIS` may compute within authorized data/output scope while documenting scientific assumptions; `FORMAL_ANALYSIS` requires the adopted specification and one authoritative source; `VERIFICATION` checks that specification without replacing its authority. Candidate computation does not require prior adoption of every field interpretation or a formal software choice. Ambiguity that prevents meaningful computation still needs resolution.

The original six Python helpers remain descriptive statistics, scale scoring, Welch and Student independent-samples t tests, paired t tests, and Pearson correlation. The release also offers an **optional local R adapter**, through the same `methods`, `preflight` and `run` interface:

| Family | Direct scope | Outside this implementation |
| --- | --- | --- |
| ANOVA | Between-subject, complete repeated and mixed factorial designs; II/III sums of squares; explicit GG/HF/none; specified conditional comparisons | Automatic trial aggregation or incomplete within-person designs; ANCOVA uses regression |
| Regression | OLS/conventional or HC3; binomial logit and Poisson ML; explicit factors, interactions, binomial denominators and log offsets | Automatic selection, penalized models, unlisted distributions |
| Mixed models | Gaussian LMM, binomial/Poisson GLMM; crossed/grouped intercepts and slopes; ML/REML where applicable; constrained ML nested fixed-effect tests | GAMM, Bayesian/nonlinear models, residual AR structures; uncorrelated categorical slopes |
| Mediation/moderation | Independent-observation simple/parallel continuous mediation with percentile bootstrap; moderation reuses supported regression families and specified slopes/comparisons | General causal mediation, serial/multilevel mediation, all PROCESS templates, moderated mediation |
| CFA/SEM | Single-group CFA/basic recursive SEM; continuous ML/MLR, explicit FIML; ordered WLSMV with complete observations | Multigroup invariance, growth/mixture/multilevel/Bayesian SEM, automatic path changes |

Query one method, for example `python -X utf8 scripts/analysis_runner.py methods --method linear_mixed`, for its small field contract. Only the selected R module and method resource are loaded. Dependencies are checked, never installed automatically; see `requirements-statistics-r.json` for the tested local profile. A new environment requires its own dependency and numerical checks. The default six-method Python profile is unchanged.

New analysis opportunities arising after inspecting results are exploratory. Existing prior-plan replication, correction and sensitivity work retain their documented origins; adoption does not turn an exploratory result into a prespecified one. Runs, failures and interruptions stay in their existing candidate output directories. The summary counts observed attempts and distinct specifications; unobserved history, options merely considered and author adoption are not inferred. No model is selected because it produces significance.

Windows PowerShell (using an already prepared project environment):

```powershell
$env:PSYCHOLOGY_PAPER_RSCRIPT = 'C:\path\to\project-R\bin\Rscript.exe'
$env:R_LIBS_USER = 'C:\path\to\project-R-library'
python -X utf8 scripts/analysis_runner.py preflight --spec 'C:\project\analysis-spec.json'
python -X utf8 scripts/analysis_runner.py run --spec 'C:\project\analysis-spec.json'
```

macOS/Linux bash or zsh:

```bash
export PSYCHOLOGY_PAPER_RSCRIPT="$(command -v Rscript)"
export R_LIBS_USER="$HOME/project-r-library"
python3 -X utf8 scripts/analysis_runner.py methods --method linear_mixed
python3 -X utf8 scripts/analysis_runner.py preflight --spec "$HOME/project/analysis-spec.json"
python3 -X utf8 scripts/analysis_runner.py run --spec "$HOME/project/analysis-spec.json"
```

These commands are usage examples, not evidence of macOS/Linux acceptance. Numerical validation so far is local Windows work; CI configuration is separate from an executed CI result. Method learning and external-analysis registration remain available beyond the direct methods. Runtime preflight checks actual inputs, dependencies and output scope; results remain candidates until author adoption. See [the validation record](docs/validation/global-statistics-cc.md) for reference calculations and limits.

## Validation

Run the regression suite:

```powershell
python -X utf8 -m unittest discover -s tests -v
```

Run the official Skill and plugin validators:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\psychology-paper"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\journal-fit-style"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\evidence-audit"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\manuscript-writing"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\analysis-adapter"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" "."
```

These checks validate structure and declared workflow behavior. They do not by themselves prove that the workflow performs correctly on a real manuscript.

## Development policy

Full review now judges the current submitted manuscript (or the current approved manuscript in a project), independently of older profiles and prior approval. It covers contribution, applicable sections, competing explanations and prioritized advice. Explicit screening, local and incremental requests remain bounded; a requested deep review of unchanged text is not reduced to a diff. No issue-count quota applies. See `docs/validation/review-depth.md` for checks and remaining behavioral validation.

Every later behavior or rule change begins with a failing automated test or scenario. Implement the smallest change that makes it pass, then run the complete regression suite. Local manuscript edits remain candidate-only. Direct document patching stays disabled until the separate write-safety stage is approved.

## Stage boundary

Statistical support is active through `analysis-adapter` under intent-specific authorization and evidence requirements. Candidate calculation, formal-source adoption and manuscript editing remain separate decisions; neither a successful calculation nor adoption authorizes a manuscript write. Targeted literature verification is available inside read-only evidence review. Systematic literature mapping, formal reviewer-response workflows, submission checks, and document patching remain deferred.

## License

MIT License. See `LICENSE`.
