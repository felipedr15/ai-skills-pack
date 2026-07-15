"""Append-only, hash-chained audit trail (Phase 8, Part 12).

Local runtime state under `.ai-os/audit/audit-<n>.log` (JSONL, git-ignored).
Each line embeds a hash of the previous line so `validate_chain` can detect
tampering. Rotates to a new numbered file once a file reaches
`AUDIT_MAX_ENTRIES_PER_FILE` entries. Never records secrets, tokens, full
file contents, full memory bodies, or full chat transcripts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import AUDIT_MAX_ENTRIES_PER_FILE
from .utils import ensure_dir, ensure_scripts_path, now_iso, runtime_dir, sanitize_text

ensure_scripts_path()
from ai_os_service.permissions import redact_sensitive_content  # noqa: E402

GENESIS_HASH = "0" * 64

EVENT_TYPES = {
    "workflow-created", "workflow-selected", "agent-selected",
    "knowledge-retrieved", "approval-requested", "approval-approved",
    "approval-rejected", "validation-run", "session-completed",
    "memory-suggested", "memory-approved", "memory-rejected",
    "feedback-added", "knowledge-gap-detected",
}


class AuditError(ValueError):
    pass


def _audit_dir(root: Path) -> Path:
    return runtime_dir(root, "audit")


def _log_files(root: Path) -> list:
    directory = _audit_dir(root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("audit-*.log"), key=lambda p: int(p.stem.split("-")[1]))


def _current_log_file(root: Path) -> Path:
    files = _log_files(root)
    if not files:
        ensure_dir(_audit_dir(root))
        return _audit_dir(root) / "audit-1.log"
    last = files[-1]
    with last.open(encoding="utf-8") as handle:
        line_count = sum(1 for _ in handle)
    if line_count >= AUDIT_MAX_ENTRIES_PER_FILE:
        index = int(last.stem.split("-")[1]) + 1
        return _audit_dir(root) / f"audit-{index}.log"
    return last


def _last_hash(root: Path) -> str:
    files = _log_files(root)
    if not files:
        return GENESIS_HASH
    last_file = files[-1]
    last_line = None
    with last_file.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last_line = line
    if last_line is None:
        return GENESIS_HASH
    return json.loads(last_line)["hash"]


def _compute_hash(prev_hash: str, event: dict) -> str:
    payload = json.dumps({"prevHash": prev_hash, **event}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_event(root: Path, event_type: str, *, details: dict | None = None) -> dict:
    """Append a redacted audit event. Never stores secrets or raw content."""
    if event_type not in EVENT_TYPES:
        raise AuditError(f"unknown audit event type: {event_type} (allowed: {sorted(EVENT_TYPES)})")

    safe_details = {}
    for key, value in (details or {}).items():
        if isinstance(value, str):
            safe_details[key] = redact_sensitive_content(sanitize_text(value, 300))
        elif isinstance(value, (int, float, bool)) or value is None:
            safe_details[key] = value
        elif isinstance(value, list):
            safe_details[key] = [
                redact_sensitive_content(sanitize_text(v, 200)) if isinstance(v, str) else v
                for v in value[:20]
            ]
        # dicts/other nested structures are intentionally dropped to avoid
        # accidentally logging full objects (file contents, memory bodies).

    event = {"event": event_type, "createdAt": now_iso(), "details": safe_details}
    prev_hash = _last_hash(root)
    event["prevHash"] = prev_hash
    event["hash"] = _compute_hash(prev_hash, {"event": event["event"], "createdAt": event["createdAt"], "details": event["details"]})

    log_path = _current_log_file(root)
    ensure_dir(log_path.parent)
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def list_events(root: Path, *, event_type: str | None = None, limit: int = 100) -> list:
    events = []
    for path in _log_files(root):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                event = json.loads(line)
                if event_type and event.get("event") != event_type:
                    continue
                events.append(event)
    return events[-limit:] if limit else events


def get_event(root: Path, index: int) -> dict:
    events = list_events(root, limit=0)
    if index < 0 or index >= len(events):
        raise AuditError(f"audit event index out of range: {index}")
    return events[index]


def summary(root: Path) -> dict:
    events = list_events(root, limit=0)
    by_type: dict = {}
    for event in events:
        by_type[event["event"]] = by_type.get(event["event"], 0) + 1
    chain_ok, _ = validate_chain(root)
    return {
        "totalEvents": len(events),
        "byType": by_type,
        "logFiles": [p.name for p in _log_files(root)],
        "chainValid": chain_ok,
    }


def validate_chain(root: Path) -> tuple:
    """Recompute the hash chain across all log files. Returns (valid, errors)."""
    errors: list = []
    prev_hash = GENESIS_HASH
    for path in _log_files(root):
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path.name}:{line_number}: invalid JSON ({exc})")
                    continue
                if event.get("prevHash") != prev_hash:
                    errors.append(f"{path.name}:{line_number}: prevHash mismatch (chain broken)")
                expected_hash = _compute_hash(prev_hash, {
                    "event": event.get("event"), "createdAt": event.get("createdAt"), "details": event.get("details"),
                })
                if event.get("hash") != expected_hash:
                    errors.append(f"{path.name}:{line_number}: hash mismatch (possible tampering)")
                prev_hash = event.get("hash", prev_hash)
    return (len(errors) == 0), errors


def export_events(root: Path, dest_path: Path) -> Path:
    """Export the full (already-redacted) event log to a caller-specified path."""
    events = list_events(root, limit=0)
    ensure_dir(dest_path.parent)
    dest_path.write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return dest_path
