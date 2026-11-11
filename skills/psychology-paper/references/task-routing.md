# Task routing table

| User goal | Primary module | Current outcome |
|---|---|---|
| Diagnose manuscript or passage | `evidence-audit` | Read-only issues at requested risk threshold |
| Recommend or assess journal | `journal-fit-style` | Manuscript profile, candidates, or confirmed journal profile |
| Learn target-journal writing style | `journal-fit-style` | Official requirements separated from observed style |
| Revise or translate approved text | `manuscript-writing` | TXT-ready candidate, never a file write |
| Record approval or choose route | `psychology-paper` | Compact approved state or routing decision |
| Verify a material source question during review | `evidence-audit` | Targeted lookup with provenance and access limits; reuse journal/profile context |
| Standalone literature management or systematic mapping | unavailable until Stage 2 | Explain boundary and stop |
| Recalculate data or verify fields | `analysis-adapter` | Confirm design and fields, lock one formal source, then produce reproducible analysis outputs |
| Patch DOCX/TXT/Markdown | unavailable until Stage 1B | Prepare minimal handoff; do not edit |
| Formal response letter or submission audit | unavailable until Stage 3 | Explain boundary and stop |

For a writing request, inspect actual meaning and dependencies. A material unresolved evidence conflict warrants focused `evidence-audit`; already verified changes within the user's scope can proceed in `manuscript-writing`. Do not require a new turn or approval merely because the text concerns scientific content. Substantive choices and additional write scope remain the author's decision.
