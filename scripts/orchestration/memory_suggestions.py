"""Memory suggestion engine (Phase 8, Part 8).

Suggestions are local runtime state under
`.ai-os/memory-suggestions/<id>.json`. Approving a suggestion is the ONLY
code path in Phase 8 that writes into `memory/` — and it requires an
explicitly approved `permanent-memory` approval first. It reuses
`scripts/memory-add.py`'s `create_record` (imported the same way
`validate-all.py` imports `index-repository.py`) instead of re-implementing
memory-file creation.
"""
from __future__ import annotations

import importlib.util
import re
import types
from pathlib import Path

from . import SCHEMA_VERSION
from .approvals import ApprovalError, is_approved
from .utils import (
    atomic_write_json, ensure_scripts_path, load_json, next_sequential_id,
    now_iso, runtime_dir, sanitize_text,
)

ensure_scripts_path()
from ai_os_service.permissions import redact_sensitive_content  # noqa: E402


class MemorySuggestionError(ValueError):
    pass


def _suggestions_dir(root: Path) -> Path:
    return runtime_dir(root, "memory-suggestions")


def _suggestion_path(root: Path, suggestion_id: str) -> Path:
    return _suggestions_dir(root) / f"{suggestion_id}.json"


def _existing_ids(root: Path) -> list:
    directory = _suggestions_dir(root)
    if not directory.is_dir():
        return []
    return [p.stem for p in directory.glob("*.json")]


def _token_set(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _similarity(a: str, b: str) -> float:
    ta, tb = _token_set(a), _token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _find_similar_memories(root: Path, title: str, summary: str, *, threshold: float = 0.55) -> list:
    memory_index = load_json(root / "generated" / "memory-index.json", {}) or {}
    matches = []
    probe = f"{title} {summary}"
    for record in memory_index.get("records", []):
        candidate = f"{record.get('title', '')} {record.get('summary', '')}"
        score = _similarity(probe, candidate)
        if score >= threshold:
            matches.append({"id": record.get("id"), "title": record.get("title"), "similarity": round(score, 2)})
    matches.sort(key=lambda m: -m["similarity"])
    return matches


def generate_suggestion(root: Path, session: dict) -> dict:
    """Generate a pending memory suggestion from a completed session."""
    task = redact_sensitive_content(session.get("task", ""))
    title = task[:100].strip() or f"session {session.get('sessionId', 'unknown')}"
    failures = session.get("failures", [])
    validations = session.get("validations", [])
    passed_validations = [v["name"] for v in validations if v.get("passed")]

    problem = sanitize_text(task, 500)
    cause = redact_sensitive_content(sanitize_text(failures[0]["reason"], 500)) if failures else ""
    resolution_parts = [v.get("detail", "") for v in validations if v.get("passed") and v.get("detail")]
    resolution = redact_sensitive_content(
        sanitize_text("; ".join(resolution_parts) or "Validation passed; see session record.", 800))
    summary = sanitize_text(f"{task[:150]}", 300)

    related_entities = [item.get("id") for item in session.get("knowledgeUsed", [])[:10] if item.get("id")]

    confidence = 0.0
    reasons = []
    if session.get("status") == "completed":
        confidence += 0.3
        reasons.append("session completed")
    if passed_validations:
        confidence += 0.3
        reasons.append(f"{len(passed_validations)} validation(s) passed")
    if not failures:
        confidence += 0.2
        reasons.append("no recorded failures")
    if resolution:
        confidence += 0.2
        reasons.append("resolution captured")
    confidence = round(min(1.0, confidence), 2)

    duplicates = _find_similar_memories(root, title, summary)
    if duplicates:
        reasons.append(f"similar to existing memory: {duplicates[0]['id']} (similarity {duplicates[0]['similarity']})")
        confidence = round(max(0.0, confidence - 0.2), 2)

    if confidence < 0.5:
        reasons.append("low-confidence suggestion — review carefully before approving")

    suggestion_id = next_sequential_id(_existing_ids(root), "memory-suggestion", task or "session")
    proposed_path = f"memory/lessons/{suggestion_id.replace('memory-suggestion-', 'lesson-')}.md"

    suggestion = {
        "schemaVersion": SCHEMA_VERSION,
        "id": suggestion_id,
        "status": "pending",
        "title": title,
        "summary": summary,
        "problem": problem,
        "cause": cause,
        "resolution": resolution,
        "validation": passed_validations,
        "project": session.get("project"),
        "relatedEntities": related_entities,
        "sourceSessionId": session.get("sessionId"),
        "sensitivity": "internal",
        "confidence": confidence,
        "reasons": reasons,
        "duplicates": duplicates,
        "proposedPath": proposed_path,
        "createdAt": now_iso(),
    }
    atomic_write_json(_suggestion_path(root, suggestion_id), suggestion)

    session.setdefault("memorySuggestions", []).append(suggestion_id)
    return suggestion


def get_suggestion(root: Path, suggestion_id: str) -> dict:
    suggestion = load_json(_suggestion_path(root, suggestion_id))
    if suggestion is None:
        raise MemorySuggestionError(f"memory suggestion not found: {suggestion_id}")
    return suggestion


def list_suggestions(root: Path, *, status: str | None = None) -> list:
    directory = _suggestions_dir(root)
    if not directory.is_dir():
        return []
    suggestions = []
    for path in sorted(directory.glob("*.json")):
        data = load_json(path)
        if data is None:
            continue
        if status and data.get("status") != status:
            continue
        suggestions.append(data)
    suggestions.sort(key=lambda s: s["id"])
    return suggestions


def reject(root: Path, suggestion_id: str, *, reason: str = "") -> dict:
    suggestion = get_suggestion(root, suggestion_id)
    if suggestion["status"] != "pending":
        raise MemorySuggestionError(f"suggestion {suggestion_id} is not pending (status: {suggestion['status']})")
    suggestion["status"] = "rejected"
    suggestion["rejectionReason"] = sanitize_text(reason, 500)
    atomic_write_json(_suggestion_path(root, suggestion_id), suggestion)
    return suggestion


def _load_memory_add_module():
    # Always load the real installed script (this module lives at
    # <repo>/scripts/orchestration/memory_suggestions.py), never a path
    # derived from the data `root` — the same pattern tests/test_memory_add.py
    # uses so the code under test stays real while the data root can be a
    # temporary, isolated directory.
    real_scripts_dir = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("ai_os_memory_add", real_scripts_dir / "memory-add.py")
    if spec is None or spec.loader is None:
        raise MemorySuggestionError("unable to load scripts/memory-add.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def approve(root: Path, suggestion_id: str, *, approved_by: str | None = None) -> dict:
    """Promote a pending suggestion into a real memory file.

    Requires an explicitly approved `permanent-memory` approval whose target
    is this suggestion id. Raises otherwise — there is no auto-approve path.
    """
    suggestion = get_suggestion(root, suggestion_id)
    if suggestion["status"] != "pending":
        raise MemorySuggestionError(f"suggestion {suggestion_id} is not pending (status: {suggestion['status']})")

    if not is_approved(root, approval_type="permanent-memory", target=suggestion_id):
        raise ApprovalError(
            f"no approved 'permanent-memory' approval found for target {suggestion_id}; "
            "run `ai-os approval approve <id>` first")

    memory_add = _load_memory_add_module()
    args = types.SimpleNamespace(
        type="lesson",
        title=suggestion["title"][:120],
        scope="project" if suggestion.get("project") else "global",
        project=suggestion.get("project"),
        summary=suggestion["summary"],
        tags="phase-8,memory-suggestion",
        sensitivity=suggestion.get("sensitivity", "internal"),
        retention=None,
        source=f"memory-suggestion:{suggestion_id}",
    )
    memory_add.create_record(root, args)

    suggestion["status"] = "approved"
    suggestion["approvedAt"] = now_iso()
    suggestion["approvedBy"] = sanitize_text(approved_by or "local-user", 100)
    atomic_write_json(_suggestion_path(root, suggestion_id), suggestion)
    return suggestion


def export_suggestion(root: Path, suggestion_id: str, dest_path: Path) -> Path:
    """Write a suggestion to a caller-specified path for human review/editing."""
    suggestion = get_suggestion(root, suggestion_id)
    atomic_write_json(dest_path, suggestion)
    return dest_path
