# Candidate output format

Use plain, copyable, TXT-ready sections in the order required by the task:

```text
English edit: Original English → Revised English → Chinese Translation
Chinese edit: Original Chinese → Revised Chinese → Necessary Notes
Chinese-to-English: Chinese Source → Revised English → Chinese Back-translation
```

Keep author queries, data checks, and unresolved problems outside the revised body. Do not insert internal workflow labels into manuscript prose.

Do not expose internal field names, machine statuses, snake_case keys, or risk codes in user-facing output. Render them as brief natural-language labels and sentences; retain the machine fields only in project state and inter-module packets.

Match the candidate length to the requested scope. By default, a revision should not materially expand the source passage unless the user approved new content. Never generate the full three-part manuscript in one response; divide it by section or subsection and enforce the target journal's recorded body budget. If the user authorizes a future point patch, do not repeat the whole source merely to satisfy the candidate format.

A next-step preview may be included to set expectations, but keep it under 300 Chinese characters or an equivalently brief English passage. It previews the next agreed writing unit; it does not add analysis, repeat prior decisions, or expand the manuscript.
