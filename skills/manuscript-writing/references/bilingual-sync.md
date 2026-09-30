# Task-scoped bilingual synchronization

Offer paired English candidates when the author requests ongoing Chinese–English alignment. Record the standing scope (units, language direction, output destination) and keep it until changed; do not ask again for each in-scope update. This is task-level synchronization when new text is supplied or an authorized file is read, not a background file watcher or automatic TXT monitoring.

Bind each pair to a stable logical-unit ID, the Chinese file hash/version and its adoption state. Run `revision_check.py sync` against the actual observed Chinese file. A changed authorized version requires an updated English candidate; an unchanged hash requires no regeneration. A missing/unreadable version is unresolved, never silently current. A content hash match only establishes freshness, not translation accuracy.

Compare argument order, construct names, qualifiers, sample descriptors, numbers, statistics and citations sentence by sentence. Translate the current Chinese text, not an older English draft's stronger claim. Preserve author changes and flag conflicting meanings rather than picking one silently. Update the terminology ledger only within its authorization.

If Chinese remains a candidate, English remains a candidate; approval of Chinese is not automatic approval of English. Provide the normal language-specific three-part candidate and brief alignment notes outside manuscript prose. No source-document overwrites, invented real-time service, automatic English adoption or repeated full-manuscript output. Broader filesystem monitoring requires a separate explicit implementation request.
