"""Explicit approval engine (Phase 8, Part 7).

Approvals are local runtime state under `.ai-os/approvals/approvals.json`.
There is no auto-approve path anywhere in this module — every approval
starts `pending` and only moves to `approved`/`rejected` via an explicit
call from a human-invoked CLI command.
"""
from __future__ import annotations

from pathlib import Path

from . import APPROVAL_TYPES
from .models import validate_approval_shape
from .utils import atomic_write_json, load_json, next_sequential_id, now_iso, runtime_dir, sanitize_text


class ApprovalError(ValueError):
    pass


def _store_path(root: Path) -> Path:
    return runtime_dir(root, "approvals", "approvals.json")


def _load_all(root: Path) -> list:
    return load_json(_store_path(root), []) or []


def _save_all(root: Path, approvals: list) -> None:
    atomic_write_json(_store_path(root), approvals)


def request_approval(root: Path, *, approval_type: str, target: str, reason: str = "") -> dict:
    if approval_type not in APPROVAL_TYPES:
        raise ApprovalError(f"invalid approval type: {approval_type} (allowed: {APPROVAL_TYPES})")
    approvals = _load_all(root)
    approval_id = next_sequential_id([a["approvalId"] for a in approvals], "approval", target or approval_type)
    approval = {
        "approvalId": approval_id,
        "type": approval_type,
        "status": "pending",
        "requestedAt": now_iso(),
        "approvedAt": None,
        "approvedBy": None,
        "reason": sanitize_text(reason, 500),
        "target": sanitize_text(target, 300),
        "metadata": {},
    }
    failures, _warnings = validate_approval_shape(approval)
    if failures:
        raise ApprovalError("; ".join(failures))
    approvals.append(approval)
    _save_all(root, approvals)
    return approval


def list_approvals(root: Path, *, status: str | None = None, approval_type: str | None = None) -> list:
    approvals = _load_all(root)
    if status:
        approvals = [a for a in approvals if a.get("status") == status]
    if approval_type:
        approvals = [a for a in approvals if a.get("type") == approval_type]
    return sorted(approvals, key=lambda a: a["approvalId"])


def get_approval(root: Path, approval_id: str) -> dict:
    for approval in _load_all(root):
        if approval["approvalId"] == approval_id:
            return approval
    raise ApprovalError(f"approval not found: {approval_id}")


def _update(root: Path, approval_id: str, new_status: str, approved_by: str | None) -> dict:
    approvals = _load_all(root)
    for approval in approvals:
        if approval["approvalId"] == approval_id:
            if approval["status"] != "pending":
                raise ApprovalError(f"approval {approval_id} is not pending (status: {approval['status']})")
            approval["status"] = new_status
            approval["approvedAt"] = now_iso()
            approval["approvedBy"] = sanitize_text(approved_by or "local-user", 100)
            _save_all(root, approvals)
            return approval
    raise ApprovalError(f"approval not found: {approval_id}")


def approve(root: Path, approval_id: str, *, approved_by: str | None = None) -> dict:
    """Explicitly approve a pending approval. Never called automatically."""
    return _update(root, approval_id, "approved", approved_by)


def reject(root: Path, approval_id: str, *, reason: str = "", approved_by: str | None = None) -> dict:
    approval = _update(root, approval_id, "rejected", approved_by)
    if reason:
        approval["reason"] = sanitize_text(reason, 500)
        approvals = _load_all(root)
        for item in approvals:
            if item["approvalId"] == approval_id:
                item["reason"] = approval["reason"]
        _save_all(root, approvals)
    return approval


def cancel(root: Path, approval_id: str) -> dict:
    return _update(root, approval_id, "cancelled", None)


def is_approved(root: Path, *, approval_type: str, target: str) -> bool:
    """True only if an explicitly approved approval exists for this target."""
    for approval in _load_all(root):
        if approval["type"] == approval_type and approval["target"] == target and approval["status"] == "approved":
            return True
    return False
