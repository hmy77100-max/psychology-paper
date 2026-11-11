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


def _receipt_source(plan, receipt, cache):
    """Rebuild a portable receipt's origin; legacy receipts stay plan-bound.

    No receipts are recursively imported. A source request is resolved against
    this plugin root and context, so the original plan digest must still match.
    """
    if receipt.get("context_id") != plan["context_id"]:
        raise ReceiptError("stale context receipt; read in the current context")
    if "schema" not in receipt and "source" not in receipt:
        if receipt.get("plan_id") != plan["plan_id"]:
            raise ReceiptError("legacy receipt is valid only for its original plan")
        return plan, False
    if receipt.get("schema") != "resource-read-receipt-v2":
        raise ReceiptError("unknown read receipt schema")
    source = receipt.get("source")
    if not isinstance(source, dict) or set(source) != {"skill", "selectors", "plugin_root"}:
        raise ReceiptError("portable receipt requires its exact source request")
    if (not isinstance(source["skill"], str) or
            not isinstance(source["selectors"], list) or
            not all(isinstance(s, str) for s in source["selectors"]) or
            not isinstance(source["plugin_root"], str)):
        raise ReceiptError("invalid receipt source request")
    try:
        if Path(source["plugin_root"]).resolve() != Path(plan["plugin_root"]):
            raise ReceiptError("receipt belongs to a different plugin root")
    except (OSError, ValueError) as exc:
        raise ReceiptError("invalid receipt plugin root") from exc
    key = (source["skill"], tuple(source["selectors"]))
    if key not in cache:
        try:
            cache[key], _ = _prepare(skill=source["skill"], selectors=source["selectors"],
                                     context_id=plan["context_id"],
                                     plugin_root=Path(plan["plugin_root"]))
        except (loader.ResourceResolutionError, loader.ResourceBudgetError) as exc:
            raise ReceiptError("receipt source can no longer be resolved") from exc
    origin = cache[key]
    if receipt.get("plan_id") != origin["plan_id"]:
        raise ReceiptError("stale source plan/manifest/resource receipt; read again")
    return origin, True


def _resource_identity(resource):
    # A source can still validate against a different on-disk snapshot than the
    # already-prepared target. Never transfer coverage by path alone.
    return resource["path"], resource["sha256"], resource["chars"]


def _read_resources(plan, receipts):
    """Validate explicit reads, without inheriting bodies omitted by reuse.

    V2 receipts attest only bodies actually delivered. Earlier receipts must
    remain present for reused resources. Resolve predecessor coverage
    iteratively so circular claims cannot manufacture an initial read.
    """
    if not isinstance(receipts, list):
        raise ReceiptError("receipts must be a JSON list")
    cache = {(plan["skill"], tuple(plan["selectors"])): plan}
    seen = {}
    pending = []
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ReceiptError("each receipt must be an object")
        origin, portable = _receipt_source(plan, receipt, cache)
        stage_id = receipt.get("stage_id")
        if type(stage_id) is not int or not 0 <= stage_id < len(origin["stages"]):
            raise ReceiptError("unknown stage_id")
        stage = origin["stages"][stage_id]
        resources = receipt.get("resources")
        if not isinstance(resources, list) or not resources:
            raise ReceiptError("receipt requires a nonempty resource list")
        expected = {r["path"]: r for r in stage["resources"]}
        paths = []
        for resource in resources:
            if not isinstance(resource, dict) or not isinstance(resource.get("path"), str):
                raise ReceiptError("malformed receipt resource")
            path = resource["path"]
            if path in paths or resource != expected.get(path):
                raise ReceiptError("duplicate or stale receipt resource")
            paths.append(path)
        ordered = [r for r in stage["resources"] if r["path"] in paths]
        if resources != ordered or (not portable and resources != stage["resources"]):
            raise ReceiptError("receipt resources do not match their source stage")
        key = (origin["plan_id"], stage_id)
        previous = seen.setdefault(key, set())
        if previous.intersection(paths):
            raise ReceiptError("duplicate read receipt resources")
        previous.update(paths)
        if type(receipt.get("read_complete")) is not bool:
            raise ReceiptError("read_complete must be an explicit boolean")
        if receipt["read_complete"]:
            ref = receipt.get("output_ref")
            if not isinstance(ref, str) or not ref.strip():
                raise ReceiptError("complete read requires an actual output_ref")
            prerequisites = {_resource_identity(r) for s in origin["stages"][:stage_id]
                             for r in s["resources"]}
            pending.append(({_resource_identity(r) for r in resources}, prerequisites))
    read = set()
    while pending:
        remaining = []
        for paths, prerequisites in pending:
            if prerequisites.issubset(read):
                read.update(paths)
            else:
                remaining.append((paths, prerequisites))
        if len(remaining) == len(pending):
            raise ReceiptError("acknowledged stage has an unread or cyclic predecessor")
        pending = remaining
    return read


def _covered_stages(plan, read):
    return {s["id"] for s in plan["stages"]
            if {_resource_identity(r) for r in s["resources"]}.issubset(read)}


def load_stage(*, stage_id, receipts, **kwargs):
    """Return unread whole resources; delivery never auto-acknowledges reading."""
    plan, bodies = _prepare(**kwargs)
    if type(stage_id) is not int or not 0 <= stage_id < len(plan["stages"]):
        raise ReceiptError("unknown stage_id")
    read = _read_resources(plan, receipts)
    acknowledged = _covered_stages(plan, read)
    if not set(range(stage_id)).issubset(acknowledged):
        raise ReceiptError("read and acknowledge every predecessor before this stage")
    stage = plan["stages"][stage_id]
    reused = [r for r in stage["resources"] if _resource_identity(r) in read]
    unread = [r for r in stage["resources"] if _resource_identity(r) not in read]
    content = "\n\n".join(f"--- resource: {r['path']} ---\n{bodies[r['path']]}" for r in unread)
    template = None
    if unread:
        template = {"schema": "resource-read-receipt-v2", "plan_id": plan["plan_id"],
                    "context_id": plan["context_id"], "stage_id": stage_id,
                    "source": {"skill": plan["skill"], "selectors": plan["selectors"],
                               "plugin_root": plan["plugin_root"]},
                    "resources": unread, "read_complete": False, "output_ref": None}
    return {"status": "DELIVERED_NOT_ACKNOWLEDGED" if unread else "ALREADY_ACKNOWLEDGED",
            "stage_id": stage_id, "chars": sum(r["chars"] for r in unread),
            "stage_chars": stage["chars"], "reused_chars": sum(r["chars"] for r in reused),
            "reused_resources": reused, "content": content, "receipt_template": template}


def check_coverage(*, receipts, **kwargs):
    """Validate declared read coverage, not task scope or scientific completion."""
    plan, _ = _prepare(**kwargs)
    acknowledged = _covered_stages(plan, _read_resources(plan, receipts))
    pending = [s["id"] for s in plan["stages"] if s["id"] not in acknowledged]
    return {"status": "INCOMPLETE" if pending else "ACKNOWLEDGED",
            "plan_id": plan["plan_id"], "pending_stages": pending,
            "acknowledged_stages": sorted(acknowledged),
            "meaning": "caller-attested resource coverage only; not comprehension or task verification"}
