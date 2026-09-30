---
{
  "schema": "psychology-paper-project",
  "schema_version": 1,
  "project_root": "",
  "current_stage": "INTAKE",
  "primary_module": null,
  "authoritative_manuscript": "",
  "source_sha256": null,
  "sources": [],
  "optional_state_files": {
    "journal_profile": null,
    "literature_map": null,
    "analysis_registry": null,
    "style_delta": null
  },
  "paper_and_design_tags": [],
  "journal": {
    "name": null,
    "status": "UNCONFIRMED"
  },
  "body_budget": {
    "limit": null,
    "unit": null,
    "counting_scope": null,
    "current": null,
    "status": "UNSET"
  },
  "formal_analysis_source": null,
  "framing": {
    "status": "UNCONFIRMED",
    "statement": null,
    "author_response": null
  },
  "revision": {
    "content_revision": 0,
    "units": []
  },
  "issued_candidate_ids": [],
  "current_action": null,
  "approved_decisions": [],
  "intentional_holds": [],
  "unresolved_issues": [],
  "next_action": null
}
---
# Authority

The frontmatter is the machine-readable project state. This body is a compact human view of the same approved information.

# Approved decisions

Record only decisions explicitly approved by the user. Rejected AI drafts and full chat history do not belong here.

# Intentional holds and unresolved issues

Record only issues the user intentionally held or issues that still change the next decision.

# Next action

Record one current next action after it has been agreed.

# Whole-manuscript readiness

Initialization is not full-revision readiness. Before full-mode drafting, load the manuscript-writing revision_checks resource and run revision_check.py preflight. Complete the approved journal profile, author-confirmed contribution direction, logical-unit plan, and adopted counted baseline with actual file hashes. Legacy projects may still pass structural validation but require these records for full revision. Do not auto-approve missing values or replace the manuscript.
