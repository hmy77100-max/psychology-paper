# Revision checks and records

Use the installed plugin's `scripts/revision_check.py`. It reads files and proposes state; it never writes manuscript or project state. A successful mechanical check is not scientific, translation or author-approval verification. The agent interprets unrestricted author language; the script must not be presented as a reply grammar.

Before delivering any revision, run `candidate --project-root ROOT --record RECORD.json`. The UTF-8 JSON record contains:

```json
{
  "mode": "chinese",
  "source": {"path": "paper.docx", "sha256": "actual file SHA256"},
  "extraction": {"path": "derived/source.txt", "sha256": "actual extraction SHA256", "source_sha256": "same source hash"},
  "unit": {"id": "intro-question", "section": "introduction", "function": "establish the question", "closure": "premise and resulting question stay together", "spans": [[0, 100]]},
  "artifact": {"path": "derived/candidate.txt", "sha256": "actual candidate SHA256"}
}
```

Offsets are half-open Unicode character offsets in UTF-8 extraction text after CRLF/CR normalization to LF. Ordered, non-overlapping spans join with two newlines. Preserve complete paragraphs/tables and source locators (paragraph IDs, table cells, pages when available) in extraction metadata. Check extraction fidelity against the original once; a hash does not establish fidelity. A logical unit can cross layout paragraphs; record its function and why the argument closes at its boundary. Do not choose boundaries simply because Word inserted a paragraph break.

Use exact plain headings: Chinese `中文原文`, `修改后中文`, `必要说明`; English `Original English`, `Revised English`, `Chinese Translation`; Chinese-to-English `中文原文`, `修改后英文`, `中文回译`. Original text must match the entire selected unit, without ellipses, summary, deleted openings or “same as above”. Explain additions, deletions, reordered logic and unresolved issues in the notes (or after the third part for translation modes), not inside revised prose. Correct any failed candidate before delivery or approval.

For whole-manuscript work also run `preflight --project-root ROOT`. Read the standard `.psychology-paper/PROJECT.md`, actual approved journal profile and actual adopted counted baseline. State requires source_sha256, author-confirmed framing (status, statement, author_response), and revision (content_revision, units). Every unit has the above ID, section, function, closure and spans plus status; mark counted_in_budget explicitly if not following body-in/abstract-keywords-title-out scope. The journal profile's JSON frontmatter has approved status, matching journal_name and body_budget (limit, unit, counting_scope, source_url, verified_on). State body_budget mirrors the rule and includes baseline_status CURRENT and baseline {path, sha256, source_sha256, adoption_status USER_ADOPTED}. Count words by whitespace or characters excluding whitespace; document this convention and ensure the journal's rule is compatible. Never invent a journal limit.

Before recording an author's full-manuscript decision, run `decision --project-root ROOT --record RECORD.json --intent INTENT --author-response "actual words"`. Internal intents: APPROVE_CURRENT, RETAIN_CURRENT, PARTIAL, REJECT, DEFER, ADVANCE_ONLY. Ambiguous references require clarification; “next” alone does not approve. Partial acceptance creates a new mixed candidate for review, not blanket approval. Only save a returned proposed state within existing project-state authorization. Keep the author's actual words and local/cross-unit preferences; persistent personal style requires their approval, using the style-delta route. Do not demand candidate IDs from the author when the referent is clear.

The body-budget utility alone is only arithmetic. This checker additionally binds authority, profile, adopted baseline and contribution direction. A counted candidate's extraction hash must equal the current adopted baseline hash: its “original” is the author's current approved mainline, not a superseded draft. After an adopted counted change, refresh that derived baseline, its hash/count and affected unit spans; set baseline_status CURRENT only after reconciling approved content. Keep the original-file hash and adoption provenance. Do not replace the source manuscript. REFRESH_REQUIRED blocks the next acceptance, preventing stale/double counting. Repeating the same accepted artifact and decision is idempotent. Body changes invalidate abstract/keywords; abstract changes invalidate keywords. Default order is body → abstract → keywords. An explicit author request can override stage order via --explicit-stage-request, without approving unfinished units.

For bilingual sync, `sync --record RECORD.json` takes authorized, unit_id, chinese {path, sha256}, chinese_status (CANDIDATE/APPROVED), english {path, sha256} if it exists, and english_based_on_sha256. It verifies both supplied file versions and reports freshness only. Missing English requires a new candidate; an altered English file is unresolved until reconciled. Updated English stays candidate-only. No watcher is installed.

Before drafting each full-mode unit, run `stage --project-root ROOT --section SECTION`; a stage error blocks drafting. If the author explicitly requests a different order, supply their actual instruction via --explicit-stage-request and persist it with the approved decision. Never fabricate an exception to bypass the body-first rule.
