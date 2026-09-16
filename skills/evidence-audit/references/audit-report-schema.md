# Audit report schema

Report only issues within the user's risk threshold. Each issue contains:

1. `location`: exact file and section, paragraph, table, figure, or field.
2. `observed_fact`: what the available source directly shows.
3. `why_it_matters`: the claim, analysis, or submission decision affected.
4. `evidence_status`: one approved evidence status.
5. `risk_level`: R0–R4.
6. `affected_claim`: the narrow claim whose ceiling changes.
7. `author_question`: the missing fact only the author or source can resolve; null when none.

Recommendations are optional and follow the factual issue. Do not edit text, select an analysis, or accuse misconduct.
