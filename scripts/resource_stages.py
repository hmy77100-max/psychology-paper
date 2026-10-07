"""Read-only, manifest-bound resource stages and caller read attestations.

Receipts are not proof of comprehension. No plan, delivery or coverage result
authorizes manuscript edits or establishes scientific verification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import load_skill_resources as loader


class ReceiptError(RuntimeError):
    """A receipt is stale, incomplete, malformed or outside this read context."""


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _prepare(*, skill, selectors, context_id, plugin_root=None):
    if not isinstance(context_id, str) or not context_id.strip():
        raise ReceiptError("a nonempty current context_id is required")
    root = (plugin_root or loader.PLUGIN_ROOT).resolve()
    selectors = list(dict.fromkeys(selectors))
    # Resolve all requested groups before returning any body or plan. This also
    # enforces manifest identity, declared paths, existence and root containment.
    union, manifest_hash, _ = loader._resolve_resources(
        skill=skill, selectors=selectors, plugin_root=root)

    axes = [s for s in selectors if s.startswith("axes.")]
    groups = [("core", [])]
    if axes:
        groups.append(("task-context", axes))
    groups.extend((s, [s]) for s in selectors if s != "always_load" and s not in axes)

    emitted = set()
    bodies = {}
    stages = []
    for name, selected in groups:
        result, current_hash, _ = loader._resolve_resources(
            skill=skill, selectors=selected, plugin_root=root)
        if current_hash != manifest_hash:
            raise loader.ResourceResolutionError("manifest changed while planning; stop")
        records = []
        for resource in result.resources:
            path = (root / "skills" / skill / resource.relative_path).resolve()
            key = path.relative_to(root).as_posix()
            if key in emitted:
                continue
            emitted.add(key)
            bodies[key] = resource.content
            records.append({"path": key, "chars": len(resource.content),
                            "sha256": hashlib.sha256(resource.content.encode("utf-8")).hexdigest()})
        if not records:
            continue
        chars = sum(r["chars"] for r in records)
        if chars > loader.DEFAULT_MAX_CHARS:
            raise loader.ResourceBudgetError(
                f"indivisible stage {name} requires {chars} characters; "
                f"budget is {loader.DEFAULT_MAX_CHARS}; repair the resource group, do not slice it")
        stages.append({"id": len(stages), "name": name, "selectors": selected,
                       "resources": records, "chars": chars})

    # Detect a resource change during the multi-group planning read, too.
    union_bodies = {(root / "skills" / skill / r.relative_path).resolve().relative_to(root).as_posix(): r.content
                    for r in union.resources}
    if bodies != union_bodies:
        raise loader.ResourceResolutionError("resources changed while planning; stop")
    plan = {"schema": "resource-stage-plan-v1", "plugin_root": str(root),
            "skill": skill, "context_id": context_id, "selectors": selectors,
            "manifest_sha256": manifest_hash, "budget": loader.DEFAULT_MAX_CHARS,
            "stages": stages, "total_unique_chars": sum(s["chars"] for s in stages)}
    plan["plan_id"] = _digest(plan)
    return plan, bodies


def build_plan(**kwargs):
    """Return costs and whole-resource stages, not instruction text or receipts."""
    return _prepare(**kwargs)[0]


def _acknowledged(plan, receipts):
    if not isinstance(receipts, list):
        raise ReceiptError("receipts must be a JSON list")
    known = {s["id"]: s for s in plan["stages"]}
    seen = set()
    acknowledged = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ReceiptError("each receipt must be an object")
        stage_id = receipt.get("stage_id")
        if type(stage_id) is not int or stage_id not in known or stage_id in seen:
            raise ReceiptError("unknown or duplicate stage_id")
        seen.add(stage_id)
        if (receipt.get("plan_id") != plan["plan_id"] or
                receipt.get("context_id") != plan["context_id"] or
                receipt.get("resources") != known[stage_id]["resources"]):
            raise ReceiptError("stale plan/context/resource receipt; replan in the current context")
        if type(receipt.get("read_complete")) is not bool:
            raise ReceiptError("read_complete must be an explicit boolean")
        if receipt["read_complete"]:
            ref = receipt.get("output_ref")
            if not isinstance(ref, str) or not ref.strip():
                raise ReceiptError("complete read requires an actual output_ref")
            acknowledged.add(stage_id)
    # A later attestation cannot make up for a missing predecessor.
    for stage_id in acknowledged:
        if not set(range(stage_id)).issubset(acknowledged):
            raise ReceiptError("acknowledged stage has an unread predecessor")
    return acknowledged


def load_stage(*, stage_id, receipts, **kwargs):
    """Return exactly one complete stage; never auto-acknowledge tool delivery."""
    plan, bodies = _prepare(**kwargs)
    if type(stage_id) is not int or not 0 <= stage_id < len(plan["stages"]):
        raise ReceiptError("unknown stage_id")
    acknowledged = _acknowledged(plan, receipts)
    if not set(range(stage_id)).issubset(acknowledged):
        raise ReceiptError("read and acknowledge every predecessor before this stage")
    stage = plan["stages"][stage_id]
    content = "\n\n".join(f"--- resource: {r['path']} ---\n{bodies[r['path']]}"
                            for r in stage["resources"])
    template = {"plan_id": plan["plan_id"], "context_id": plan["context_id"],
                "stage_id": stage_id, "resources": stage["resources"],
                "read_complete": False, "output_ref": None}
    return {"status": "DELIVERED_NOT_ACKNOWLEDGED", "stage_id": stage_id,
            "chars": stage["chars"], "content": content, "receipt_template": template}


def check_coverage(*, receipts, **kwargs):
    """Validate declared read coverage, not task scope or scientific completion."""
    plan, _ = _prepare(**kwargs)
    acknowledged = _acknowledged(plan, receipts)
    pending = [s["id"] for s in plan["stages"] if s["id"] not in acknowledged]
    return {"status": "INCOMPLETE" if pending else "ACKNOWLEDGED",
            "plan_id": plan["plan_id"], "pending_stages": pending,
            "acknowledged_stages": sorted(acknowledged),
            "meaning": "caller-attested resource coverage only; not comprehension or task verification"}
