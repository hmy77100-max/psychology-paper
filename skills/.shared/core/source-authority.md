# Source authority

## Roles

- `AUTHORITATIVE`: the current source whose content or parameters govern the deliverable.
- `VERIFICATION`: an independent source used only to check the authoritative source.
- `HISTORICAL`: an earlier manuscript, thesis, output, or decision retained for comparison.
- `REFERENCE`: a journal article, guideline, template, or other source used for context rather than manuscript authority.
- `RAW`: unmodified source data or source material that must not be overwritten.
- `DERIVED`: a reproducible transformation or analysis output created from another source.
- `UNKNOWN`: a source whose role has not yet been confirmed.

One manuscript task has one authoritative manuscript. One formal analysis has one authoritative analysis source and may have one verification source. Never mix parameters from different software, samples, scoring rules, or models merely because they are individually favorable.

User approval adopts a decision; it does not silently change a source role. A raw or historical source becomes an output target only after the user explicitly redesignates it. Record the source path and role before handing work to another module.
