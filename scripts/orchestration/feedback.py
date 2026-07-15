"""Local feedback capture (Phase 8, Part 11).

Feedback is local runtime state under `.ai-os/feedback/feedback.json`. No
telemetry, no upload, no automatic modification of source knowledge —
feedback can only ever *suggest* a knowledge gap (see knowledge_gaps.py);
it never edits a document itself.
"""
from __future__ import annotations

from pathlib import Path

from . import FEEDBACK_TYPES, MAX_COMMENT_CHARS
from .models import validate_feedback_shape
from .utils import (
    atomic_write_json, ensure_scripts_path, load_json, next_sequential_id,
    now_iso, runtime_dir, sanitize_text,
)

ensure_scripts_path()
from ai_os_service.permissions import redact_sensitive_content  # noqa: E402


class FeedbackError(ValueError):
    pass


def _store_path(root: Path) -> Path:
    return runtime_dir(root, "feedback", "feedback.json")


def _load_all(root: Path) -> list:
    return load_json(_store_path(root), []) or []


def _save_all(root: Path, entries: list) -> None:
    atomic_write_json(_store_path(root), entries)


def add_feedback(root: Path, *, feedback_type: str, target_type: str, target_id: str,
                  query: str = "", comment: str = "", related_session_id: str | None = None) -> dict:
    if feedback_type not in FEEDBACK_TYPES:
        raise FeedbackError(f"invalid feedback type: {feedback_type} (allowed: {FEEDBACK_TYPES})")
    entries = _load_all(root)
    feedback_id = next_sequential_id([e["feedbackId"] for e in entries], "feedback", target_id or feedback_type)

    clean_comment = redact_sensitive_content(sanitize_text(comment, MAX_COMMENT_CHARS))
    entry = {
        "feedbackId": feedback_id,
        "createdAt": now_iso(),
        "type": feedback_type,
        "targetType": sanitize_text(target_type, 100),
        "targetId": sanitize_text(target_id, 300),
        "query": sanitize_text(query, 500),
        "comment": clean_comment,
        "status": "open",
        "relatedSessionId": related_session_id,
        "metadata": {},
    }
    failures, _warnings = validate_feedback_shape(entry)
    if failures:
        raise FeedbackError("; ".join(failures))
    entries.append(entry)
    _save_all(root, entries)
    return entry


def list_feedback(root: Path, *, status: str | None = None, feedback_type: str | None = None) -> list:
    entries = _load_all(root)
    if status:
        entries = [e for e in entries if e.get("status") == status]
    if feedback_type:
        entries = [e for e in entries if e.get("type") == feedback_type]
    return sorted(entries, key=lambda e: e["feedbackId"])


def get_feedback(root: Path, feedback_id: str) -> dict:
    for entry in _load_all(root):
        if entry["feedbackId"] == feedback_id:
            return entry
    raise FeedbackError(f"feedback not found: {feedback_id}")


def resolve_feedback(root: Path, feedback_id: str) -> dict:
    entries = _load_all(root)
    for entry in entries:
        if entry["feedbackId"] == feedback_id:
            entry["status"] = "resolved"
            _save_all(root, entries)
            return entry
    raise FeedbackError(f"feedback not found: {feedback_id}")


def feedback_stats(root: Path) -> dict:
    entries = _load_all(root)
    by_type: dict = {}
    by_status: dict = {}
    for entry in entries:
        by_type[entry["type"]] = by_type.get(entry["type"], 0) + 1
        by_status[entry["status"]] = by_status.get(entry["status"], 0) + 1
    return {
        "total": len(entries),
        "byType": by_type,
        "byStatus": by_status,
        "open": by_status.get("open", 0),
        "resolved": by_status.get("resolved", 0),
    }
