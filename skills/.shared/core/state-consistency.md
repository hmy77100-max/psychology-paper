---
{
  "schema": "psychology-paper-state-rules",
  "version": 1,
  "rules": [
    {
      "id": "SC-001",
      "scope": "current_action",
      "all": [
        {"path": "write_permission", "op": "eq", "value": "WRITE_ALLOWED"},
        {"path": "decision_status", "op": "ne", "value": "APPROVED"}
      ],
      "any": [],
      "message": "Writing requires an approved decision.",
      "components": ["router", "project-validator", "document-patcher"]
    },
    {
      "id": "SC-002",
      "scope": "current_action",
      "all": [
        {"path": "write_permission", "op": "eq", "value": "WRITE_ALLOWED"},
        {"path": "source_role", "op": "in", "value": ["RAW", "HISTORICAL"]},
        {"path": "explicit_output_target", "op": "ne", "value": true}
      ],
      "any": [],
      "message": "Raw or historical sources require explicit redesignation before output.",
      "components": ["router", "project-validator", "document-patcher"]
    },
    {
      "id": "SC-003",
      "scope": "current_action",
      "all": [
        {"path": "decision_status", "op": "in", "value": ["REJECTED", "INTENTIONAL_HOLD"]},
        {"path": "write_permission", "op": "eq", "value": "WRITE_ALLOWED"}
      ],
      "any": [],
      "message": "Rejected or held decisions cannot be written.",
      "components": ["router", "project-validator", "document-patcher"]
    },
    {
      "id": "SC-004",
      "scope": "current_action",
      "all": [
        {"path": "evidence_status", "op": "in", "value": ["CONTRADICTED", "OUTSIDE_EVIDENCE"]},
        {"path": "write_permission", "op": "eq", "value": "WRITE_ALLOWED"},
        {"path": "evidence_boundary_applied", "op": "ne", "value": true}
      ],
      "any": [],
      "message": "Unsupported claims require a bounded rewrite before approval.",
      "components": ["router", "project-validator", "document-patcher"]
    },
    {
      "id": "SC-005",
      "scope": "current_action",
      "all": [
        {"path": "patch_status", "op": "in", "value": ["PATCHED_UNVERIFIED", "PATCHED_VISUAL_PENDING"]},
        {"path": "patch_receipt_present", "op": "ne", "value": true}
      ],
      "any": [],
      "message": "A patched state requires a receipt.",
      "components": ["project-validator", "document-patcher"]
    },
    {
      "id": "SC-006",
      "scope": "current_action",
      "all": [
        {"path": "patch_status", "op": "eq", "value": "DELIVERY_VERIFIED"},
        {"path": "required_verification_complete", "op": "ne", "value": true}
      ],
      "any": [],
      "message": "Delivery cannot be verified before required checks.",
      "components": ["project-validator", "document-patcher"]
    },
    {
      "id": "SC-007",
      "scope": "current_action",
      "all": [
        {"path": "patch_status", "op": "in", "value": ["ROLLBACK_PENDING", "ROLLBACK_FAILED"]},
        {"path": "new_patch_requested", "op": "eq", "value": true}
      ],
      "any": [],
      "message": "New writes are blocked until recovery is resolved.",
      "components": ["router", "project-validator", "document-patcher"]
    },
    {
      "id": "SC-008",
      "scope": "current_action",
      "all": [
        {"path": "check_status", "op": "eq", "value": "PASS"},
        {"path": "risk_level", "op": "in", "value": ["R0", "R1"]},
        {"path": "issue_resolved", "op": "ne", "value": true}
      ],
      "any": [],
      "message": "Submission cannot be marked passed with unresolved R0/R1 risk.",
      "components": ["router", "project-validator"]
    }
  ]
}
---
# State consistency rules

The JSON frontmatter is the single authoritative definition of illegal state combinations. The orchestrator, project validator, future document patcher, and tests must parse or cite this file; they must not maintain copied condition tables.

Approval, write permission, patch execution, source role, evidence status, risk level, and check status are independent namespaces. A user approval permits the current decision but does not silently change source authority, evidence strength, or delivery status.
