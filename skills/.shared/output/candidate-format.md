# Candidate output format

Use plain, copyable, TXT-ready sections in the order required by the task:

```text
English edit: Original English → Revised English → Chinese Translation
Chinese edit: Original Chinese → Revised Chinese → Necessary Notes
Chinese-to-English: Chinese Source → Revised English → Chinese Back-translation
```

Keep author queries, data checks, and unresolved problems outside the revised body. Do not insert internal workflow labels into manuscript prose.

Do not expose internal field names, machine statuses, snake_case keys, or risk codes in user-facing output. Render them as brief natural-language labels and sentences; retain the machine fields only in project state and inter-module packets.

The original must include the complete selected logical unit, in its original order and wording; no ellipses, summaries or “see above”. Use 中文原文 → 修改后中文 → 必要说明 for Chinese edits. Explain substantive additions, removals and reordered reasoning; for translation modes place necessary queries after the required third part. Before delivery run the manuscript-writing candidate checker against the real source/extraction/artifact. Repair format failures before seeking approval. Mechanical checks do not establish scientific correctness.

Match the candidate length to the requested scope. Do not materially expand it without approval. Split long work into argument-complete logical units, not physical paragraph breaks; never output an entire three-part manuscript at once. Even a point edit includes the full selected unit. Source comparison preserves the author's thinking and decision rights and cannot be dropped to save tokens.

Accept natural-language decisions. Fixed commands or candidate IDs may help internal tracking but must not be mandatory user syntax. Resolve clear references in context; ask only if materially ambiguous. Partial adoption is not full approval. Preserve the author's actual wording and distinguish local feedback from approved reusable style preferences.

A next-step preview may be included to set expectations, but keep it under 300 Chinese characters or an equivalently brief English passage. It previews the next agreed writing unit; it does not add analysis, repeat prior decisions, or expand the manuscript.
