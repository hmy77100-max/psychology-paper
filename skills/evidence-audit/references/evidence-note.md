# Evidence note contract

Compact note fields (not a mandatory JSON user report): `issue_id`, `question`, `manuscript_location`, `search_note` (searched/reused/not searched), `sources`, `counterevidence` (or not-found/not-checked), `evidence_status` (shared status vocabulary, model-assigned), `conclusion`, `coverage_limit`, `stop_reason`. Empty sources are allowed for unresolved offline/access-limited notes.

Source fields: unique `source_id`; `reference` (URL/DOI/citation/supplied path); `access_level` (full_text/excerpt/abstract/snippet/unavailable); `locator` (passage location); `observed_support` (inspected content); `applicability` (match/limits); `relation` (supports/challenges/qualifies/context/unresolved). Unavailable sources have empty-string locator and observed_support, never fabricated content.

Optional plugin-root helper: `scripts/review_evidence.py --record PATH` reads existing JSON; `--record -` reads stdin. No writes/network. It checks completeness, IDs and access fields, not source existence, scientific truth or acceptance. `record_complete=true` still has `scientific_verification=false`. Do not create a file just to run it.
