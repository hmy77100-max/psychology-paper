# Evidence note contract

Compact fields, not a mandatory JSON report: `issue_id`, `question`, `manuscript_location`, `search_note` (searched/reused/not searched), `sources`, `counterevidence` (or not-found/not-checked), `evidence_status` (shared vocabulary; model-assigned), `conclusion`, `coverage_limit`, `stop_reason`. Empty sources are allowed for unresolved access-limited notes.

Each source: unique `source_id`; `reference` (URL/DOI/citation/path); `access_level` (full_text/excerpt/abstract/snippet/unavailable); `locator` (page/section/paragraph, abstract or table row/column); `observed_support` (marked original short quote or inspected table cells); `applicability` (supported claim, version/attribution limits, separate inference); `relation` (supports/challenges/qualifies/context/unresolved). Unavailable sources have empty-string locator and observed_support. Follow external-evidence for quotation, access and attribution; deliver the excerpt and locator with the recommendation, not only in an internal record.

Optional `scripts/review_evidence.py --record PATH` or `--record -` reads existing JSON/stdin without writes/network. It checks field completeness, not quotation authenticity or scientific support: `record_complete=true` still has `scientific_verification=false`. No new file is required.
