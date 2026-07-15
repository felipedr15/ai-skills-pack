"""Work session tracking (Phase 8, Part 6).

Sessions are local runtime state under `.ai-os/sessions/` (git-ignored) —
never a source of truth, never committed. Starting a session never modifies
any source file; it only records a plan snapshot and tracks status through
an explicit, validated transition graph.
"""
from __future__ import annotations

from pathlib import Path

from . import MAX_LIST_ITEMS, SCHEMA_VERSION, SESSION_TRANSITIONS
from .models import SESSION_LIST_FIELDS, validate_session_shape
from .utils import (
    bounded_list, ensure_scripts_path, load_json, next_sequential_id,
    now_iso, runtime_dir, sanitize_text,
)

ensure_scripts_path()
from ai_os_service.permissions import redact_sensitive_content  # noqa: E402


class SessionError(ValueError):
    pass


def _sessions_dir(root: Path) -> Path:
    return runtime_dir(root, "sessions")


def _session_path(root: Path, session_id: str) -> Path:
    return _sessions_dir(root) / f"{session_id}.json"


def _existing_ids(root: Path) -> list:
    directory = _sessions_dir(root)
    if not directory.is_dir():
        return []
    return [p.stem for p in directory.glob("*.json")]


def _apply_bounds(session: dict) -> dict:
    for field in SESSION_LIST_FIELDS:
        items, truncated = bounded_list(session.get(field, []), MAX_LIST_ITEMS)
        session[field] = items
        if truncated:
            note = f"{field} truncated to {MAX_LIST_ITEMS} entries"
            if note not in session.get("warnings", []):
                session.setdefault("warnings", []).append(note)
    return session


def create_session(root: Path, task: str, *, project: str | None = None, plan: dict | None = None) -> dict:
    """Create a new session from a plan (or bare task). Writes no source file."""
    task_clean = redact_sensitive_content(sanitize_text(task, 2000))
    session_id = next_sequential_id(_existing_ids(root), "session", task_clean or "task")
    timestamp = now_iso()
    plan = plan or {}

    session = {
        "schemaVersion": SCHEMA_VERSION,
        "sessionId": session_id,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "task": task_clean,
        "project": project,
        "intent": plan.get("intent", "unknown"),
        "workflowId": (plan.get("selectedWorkflow") or {}).get("id"),
        "status": "planned",
        "agents": [a["id"] for a in plan.get("selectedAgents", [])],
        "knowledgeUsed": [
            {"id": item.get("id"), "type": item.get("type"), "sourcePath": item.get("sourcePath")}
            for item in plan.get("retrievedKnowledge", [])
        ],
        "steps": plan.get("steps", []),
        "approvals": [],
        "filesObserved": [],
        "filesChanged": [],
        "validations": [],
        "warnings": list(plan.get("risksAndWarnings", [])),
        "failures": [],
        "memorySuggestions": [],
        "feedback": [],
        "metadata": {"taskId": plan.get("taskId")},
    }
    session = _apply_bounds(session)
    failures, _warnings = validate_session_shape(session)
    if failures:
        raise SessionError("; ".join(failures))

    _session_path(root, session_id).parent.mkdir(parents=True, exist_ok=True)
    from .utils import atomic_write_json
    atomic_write_json(_session_path(root, session_id), session)
    return session


def get_session(root: Path, session_id: str) -> dict:
    session = load_json(_session_path(root, session_id))
    if session is None:
        raise SessionError(f"session not found: {session_id}")
    return session


def list_sessions(root: Path, *, status: str | None = None) -> list:
    directory = _sessions_dir(root)
    if not directory.is_dir():
        return []
    sessions = []
    for path in sorted(directory.glob("*.json")):
        data = load_json(path)
        if data is None:
            continue
        if status and data.get("status") != status:
            continue
        sessions.append(data)
    sessions.sort(key=lambda s: s.get("sessionId", ""))
    return sessions


def _save(root: Path, session: dict) -> None:
    from .utils import atomic_write_json
    session["updatedAt"] = now_iso()
    session = _apply_bounds(session)
    failures, _warnings = validate_session_shape(session)
    if failures:
        raise SessionError("; ".join(failures))
    atomic_write_json(_session_path(root, session["sessionId"]), session)


def transition_status(root: Path, session_id: str, new_status: str) -> dict:
    session = get_session(root, session_id)
    current = session["status"]
    allowed = SESSION_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise SessionError(f"invalid transition: {current} -> {new_status} (allowed: {sorted(allowed) or 'none'})")
    session["status"] = new_status
    _save(root, session)
    return session


def record_validation(root: Path, session_id: str, *, name: str, passed: bool, detail: str = "") -> dict:
    session = get_session(root, session_id)
    session.setdefault("validations", []).append({
        "name": sanitize_text(name, 200),
        "passed": bool(passed),
        "detail": redact_sensitive_content(sanitize_text(detail, 500)),
        "recordedAt": now_iso(),
    })
    if not passed:
        session.setdefault("failures", []).append({
            "step": sanitize_text(name, 200),
            "reason": redact_sensitive_content(sanitize_text(detail, 500)),
            "recordedAt": now_iso(),
        })
    _save(root, session)
    return session


def record_files_observed(root: Path, session_id: str, paths: list) -> dict:
    session = get_session(root, session_id)
    for path in paths:
        clean = sanitize_text(path, 300)
        if clean and clean not in session.setdefault("filesObserved", []):
            session["filesObserved"].append(clean)
    _save(root, session)
    return session


_HAPPY_PATH = ["planned", "approved", "active", "validation", "completed", "archived"]


def advance_toward(root: Path, session_id: str, target_status: str) -> dict:
    """Hop forward through legal transitions toward target_status.

    Stops early (without error) if a required hop isn't a legal transition
    from the current status — callers should check the returned status.
    """
    session = get_session(root, session_id)
    if target_status not in _HAPPY_PATH or session["status"] not in _HAPPY_PATH:
        return session
    while _HAPPY_PATH.index(session["status"]) < _HAPPY_PATH.index(target_status):
        current = session["status"]
        next_status = _HAPPY_PATH[_HAPPY_PATH.index(current) + 1]
        if next_status not in SESSION_TRANSITIONS.get(current, set()):
            break
        session = transition_status(root, session_id, next_status)
    return session


def complete_session(root: Path, session_id: str) -> dict:
    return transition_status(root, session_id, "completed")


def archive_session(root: Path, session_id: str) -> dict:
    return transition_status(root, session_id, "archived")
