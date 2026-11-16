# Learning and assessing methods

Follow questions grounded in the study's design and retained data. Find methods in studies with comparable questions, designs and measures; assess transfer and explanatory gain. Novelty, complexity or significance alone do not justify changing the analysis.

Use original method sources and relevant applications, supporting applicability and implementation claims with inspected primary passages and versions. Distinguish findings from inference; check assumptions behind labels such as "exact". Explain data needs, cost and likely gain. Recommend keeping, investigating or changing the analysis; the author decides. Consultation needs no data or formal source.

Distinguish runner methods from external implementations requiring reviewed syntax. Within existing authorization, run useful candidates and compare what they actually add; revise the recommendation with the author. Computation does not require prior formal adoption. Keep candidate artifacts separate; adopting specifications, results and manuscript edits remain distinct decisions.

## Shared computation interface

Resolve `scripts/analysis_runner.py` from the same plugin root as the loader. `methods` lists implementations; `methods --method <name>` returns the compact field contract without reading implementation files. `run --spec <absolute-json>` checks inputs/runtime and saves a separate candidate; use `preflight --spec <absolute-json>` separately when diagnosis is needed, not as a duplicate step before every run. Read the JSON business status: exit 0 alone is not success. No installation is automatic. Host permissions remain in force.

Reuse the runner's provenance, sample audit and artifact references; do not create parallel ledgers merely to repeat them. An external implementation needs its actual code, inputs, settings and output recorded, but can keep these in a compact shared record. Record enough to reproduce the calculation without making documentation the task.

Minimal candidate request (replace paths, hash, mappings and authorization with actual task evidence):

```json
{"schema_version":2,"analysis_id":"candidate-1","revision":1,"intent":"CANDIDATE_ANALYSIS","design":{"design_tags":["survey"],"observation_unit":"participant","research_question_type":"description","variables":[{"name":"score","role":"outcome"}]},"data":{"path":"<absolute-csv>","sha256":"<actual-content-sha256>","format":"csv","read_options":{"encoding":"utf-8","delimiter":",","missing_values":[""]}},"field_map":[{"variable":"score","column":"score","confirmation_status":"DOCUMENTED","evidence_ref":"<mapping-basis>"}],"scoring":{"method":"none"},"sample":{"missing":"complete_case","filters":[]},"model":{"method":"descriptive","columns":["score"]},"inference":{"alpha":0.05,"confidence_level":0.95,"alternative":"two-sided"},"sources":[],"authorization":{"data_read":true,"compute":true,"output_dir":"<authorized-absolute-candidate-folder>","reference":"<actual-user-scope>"}}
```

Mappings cover every design/model variable. `paired_t` uses model `x`, `y`, `subject_id` (unique paired rows); `pearson` uses `x`, `y`; `welch_t` and `student_t` use `outcome`, `group`, explicit two-label `group_order`. Contrasts follow x-minus-y or first-minus-second. `scale_score` uses `columns` equal to scoring `items`, plus scoring `method:scale`, `reverse_items`, `minimum`, `maximum`, `aggregation:mean|sum`, and `min_answered`. XLSX requires `sheet_name` and explicit `formula_policy:cached_values`. Unsupported model options are rejected, not ignored. Intervals are two-sided; p values follow `alternative`. The current runner does not implement adjusted regression, mixed models or bootstrap.

Formal/verification requests additionally bind `authorization.formal_spec_hash` to `analysis_contracts.spec_hash(spec)` and retain one AUTHORITATIVE source. A declared approval hash is not evidence of user consent: reuse the actual decision. The Python runner cannot impersonate a different formal engine. A supplied execution host label is metadata, not proof of a real host trial.
