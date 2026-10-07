# Psychology Paper

Psychology Paper is a Codex plugin project for evidence-calibrated psychology manuscript work. It diagnoses the task, learns the target journal's writing style, audits the manuscript against the study design, prepares bilingual revision candidates, and supports reproducible quantitative-analysis reconstruction. It does not modify source data or manuscript files, maintain a literature database, or prepare submission files yet. Version 0.5.0 adds on-demand prose diagnostics, author-led collaboration guidance and bounded staged resource loading within the existing modules.

## Implemented modules

- `psychology-paper`: routes the request and maintains authorization boundaries.
- `journal-fit-style`: profiles the manuscript, evaluates journal fit, and learns journal writing patterns at light or deep depth.
- `evidence-audit`: reviews the paper with design-appropriate checks, targeted external-source verification, and evidence-grounded advice within the requested scope/risk threshold.
- `manuscript-writing`: prepares section-specific Chinese, English, or bilingual candidates after the evidence boundary is approved.
- `analysis-adapter`: confirms design and data fields, locks one formal analysis source, routes design-appropriate methods, records adopted specifications, and supports independent verification.

One module is primary for each task. Other modules receive only the smallest necessary handoff, preferably a file path and exact location rather than duplicated manuscript text.

## Review evidence support

Review-only requests go directly to `evidence-audit`, including whole-paper review. Existing article/journal profiles and project memory are reused selectively; no second journal-positioning workflow or mandatory project setup is introduced. Six internal responsibilities organize review, not six new agents or Skills. The model remains responsible for scientific judgment and may recommend a different journal, argument, analysis or experiment; the author chooses adoption.

For material external questions the model uses available browsing/retrieval tools to check original sources, versions and applicability. It records inspected support, competing evidence and access limits. Offline requests and unavailable full texts produce bounded findings. This is targeted review support, not a new search service or literature-management module.

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

Journal-guided full revision follows journal confirmation → contribution recommendations → author's own view and chosen direction → outline → body → abstract → keywords. An explicit author request may override order without approving unfinished units. Recommendations compare the journal's relevant research trajectory and direct field predecessors; fit is not a novelty claim.

Introduction work prioritizes evidence supporting the research-question and hypothesis chain. Each recommended source needs a specific claim, verified support, evidence distance, incremental value, claim ceiling and deletion impact. Necessary caveats serve the chain without suppressing contradictory evidence. Existing search authorization is reused; citation adoption remains a separate author decision.

`scripts/revision_check.py` checks actual files, not caller-supplied success flags:

```powershell
python -X utf8 scripts/revision_check.py candidate --project-root "C:\path\to\project" --record "candidate-record.json"
python -X utf8 scripts/revision_check.py preflight --project-root "C:\path\to\project"
python -X utf8 scripts/revision_check.py stage --project-root "C:\path\to\project" --section introduction
python -X utf8 scripts/revision_check.py decision --project-root "C:\path\to\project" --record "candidate-record.json" --intent APPROVE_CURRENT --author-response "Use this version"
```

These are internal commands, not required author replies. Load `conditional_loads.revision_checks` through the manuscript-writing loader for the record contract. Full-mode acceptance binds the standard project file, approved journal profile, actual source hash, author-confirmed framing and adopted counted baseline. After counted adoption, refresh the derived baseline before accepting another candidate. The checker returns proposed state; it never writes manuscript/state or judges scientific truth. Initialization/legacy structural validation alone does not mean full-revision readiness.

Task-scoped bilingual sync checks observed Chinese and English versions under standing authorization. It generates corresponding English candidates after an in-scope change; it is not a background watcher, automatic adoption or Word overwrite.

## Efficient resource execution

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

Each delivery contains `content` and a `receipt_template` with `read_complete: false` and `output_ref: null`. Only after the assistant has read the entire untruncated output may it copy that template into a task-local JSON list, set `read_complete: true`, and name the actual tool output in `output_ref`. The script never writes or confirms receipts itself. This internal bookkeeping imposes no response format or approval step on the author.

Receipts bind the current read context, plugin root, entire plan, manifest and resource hashes. Missing predecessors block later stages. Lost context, a different resource selection or changed files invalidate reuse; replan and read the required instructions. Earlier ordinary loads cannot be silently converted into staged receipts. Reuse a completed unchanged plan within the same read context instead of repeating this cycle for every unit. Coverage returns exit 1 / `INCOMPLETE` for pending reads, or exit 0 / `ACKNOWLEDGED` for complete caller attestations. It does not verify the output reference, comprehension, selection sufficiency, author approval or manuscript quality.

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

Preflight stops before calculation when the research design is missing, field mappings are not user-confirmed, or the formal analysis source is unresolved. The registry accepts a formal result only after explicit user adoption.

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

Statistical support is active through `analysis-adapter`, but actual analyses remain gated by confirmed design, field mapping, scoring, sample, model, and source. Targeted literature verification is available inside read-only evidence review. Standalone literature management, formal reviewer-response workflows, submission checks, and document patching remain absent until their separate stages are approved.

## License

MIT License. See `LICENSE`.
