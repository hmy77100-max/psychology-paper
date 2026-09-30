# Journal profile schema

Store a compact approved profile in `.psychology-paper/JOURNAL_PROFILE.md` with:

- `journal_name`
- `verified_on`
- `official_requirements`: each item with official URL and verification date
- `observed_style`: each pattern with the compared article DOI or stable URL
- `manuscript_fit`: question, audience, evidence, and contribution match
- `revision_implications`: concrete manuscript locations or decisions
- `largest_submission_risk`
- `status`: candidate or approved

For whole-manuscript preflight, use JSON frontmatter with these fields plus `body_budget`: `limit`, `unit` (words or characters), `counting_scope`, `source_url` and `verified_on`. These must reflect a verified journal rule and a compatible counting convention, not a global default. Keep missing or incompatible rules unresolved; do not mark the profile approved merely to pass the checker. The adopted project baseline is separate from this journal policy record.

Official requirements and observed style must remain in separate sections. Article examples support observations; they do not become formal policy.
