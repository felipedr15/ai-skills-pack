"""Aggregate structural validation for Phase 8 artifacts (Part 18).

Called by `scripts/orchestration-validate.py` (wired into
`scripts/validate-all.py` like every other `*-validate.py`). Read-only —
never modifies any file.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import MAX_LIST_ITEMS
from .approvals import list_approvals
from .audit import validate_chain
from .knowledge_gaps import build_knowledge_health, compare_reports_ignoring_generated_at, validate_knowledge_health
from .models import (
    validate_approval_shape, validate_feedback_shape,
    validate_memory_suggestion_shape, validate_session_shape,
)
from .registry import build_agent_registry, compare_registries_ignoring_generated_at, validate_agent_registry
from .utils import ensure_scripts_path, load_json, runtime_dir
from .workflow import build_workflow_registry
from .workflow import compare_registries_ignoring_generated_at as compare_workflow_registries
from .workflow import validate_workflow_registry

ensure_scripts_path()
from ai_os_service.permissions import SECRET_PATTERN  # noqa: E402

MAX_SESSION_FILE_BYTES = 500_000


def _contains_secret(obj) -> bool:
    return bool(SECRET_PATTERN.search(json.dumps(obj, ensure_ascii=False)))


def validate_generated_registries(root: Path) -> tuple:
    """Compare fresh builds of agent/workflow/knowledge-health against the committed artifacts."""
    failures: list = []
    warnings: list = []

    agent_json = root / "generated" / "agent-registry.json"
    if agent_json.is_file():
        fresh = build_agent_registry(root)
        saved = load_json(agent_json, {})
        if not compare_registries_ignoring_generated_at(fresh, saved):
            failures.append("stale generated file: generated/agent-registry.json")
    else:
        warnings.append("generated/agent-registry.json not yet built")

    workflow_json = root / "generated" / "workflow-registry.json"
    if workflow_json.is_file():
        fresh = build_workflow_registry(root)
        saved = load_json(workflow_json, {})
        if not compare_workflow_registries(fresh, saved):
            failures.append("stale generated file: generated/workflow-registry.json")
    else:
        warnings.append("generated/workflow-registry.json not yet built")

    health_json = root / "generated" / "knowledge-health.json"
    if health_json.is_file():
        fresh = build_knowledge_health(root, include_live=False)
        saved = load_json(health_json, {})
        if not compare_reports_ignoring_generated_at(fresh, saved):
            failures.append("stale generated file: generated/knowledge-health.json")
    else:
        warnings.append("generated/knowledge-health.json not yet built")

    return failures, warnings


def validate_sessions(root: Path) -> tuple:
    failures: list = []
    warnings: list = []
    directory = runtime_dir(root, "sessions")
    if not directory.is_dir():
        return failures, warnings
    for path in sorted(directory.glob("*.json")):
        data = load_json(path)
        if data is None:
            failures.append(f"malformed session file: {path.name}")
            continue
        session_failures, _warnings = validate_session_shape(data)
        failures += [f"session {path.name}: {m}" for m in session_failures]
        if path.stat().st_size > MAX_SESSION_FILE_BYTES:
            failures.append(f"session {path.name}: exceeds size limit ({path.stat().st_size} bytes)")
        if _contains_secret(data):
            failures.append(f"session {path.name}: possible secret content detected")
        for field in ("filesObserved", "filesChanged", "warnings", "failures", "knowledgeUsed"):
            if len(data.get(field, [])) > MAX_LIST_ITEMS:
                failures.append(f"session {path.name}: {field} exceeds bounded size limit")
    return failures, warnings


def validate_approvals(root: Path) -> tuple:
    failures: list = []
    warnings: list = []
    for approval in list_approvals(root):
        approval_failures, _warnings = validate_approval_shape(approval)
        failures += [f"approval {approval.get('approvalId')}: {m}" for m in approval_failures]
    return failures, warnings


def validate_memory_suggestions(root: Path) -> tuple:
    failures: list = []
    warnings: list = []
    directory = runtime_dir(root, "memory-suggestions")
    if not directory.is_dir():
        return failures, warnings

    approvals = list_approvals(root, status="approved", approval_type="permanent-memory")
    approved_targets = {a["target"] for a in approvals}

    approved_paths: dict = {}
    for path in sorted(directory.glob("*.json")):
        data = load_json(path)
        if data is None:
            failures.append(f"malformed memory suggestion: {path.name}")
            continue
        suggestion_failures, suggestion_warnings = validate_memory_suggestion_shape(data)
        failures += [f"suggestion {data.get('id', path.name)}: {m}" for m in suggestion_failures]
        warnings += [f"suggestion {data.get('id', path.name)}: {m}" for m in suggestion_warnings]

        if data.get("status") == "approved":
            if data["id"] not in approved_targets:
                failures.append(f"suggestion {data['id']}: approval bypass — no approved permanent-memory approval on record")
            proposed = data.get("proposedPath", "")
            if proposed in approved_paths:
                failures.append(f"suggestion {data['id']}: duplicate approved memory path {proposed!r} (also used by {approved_paths[proposed]})")
            else:
                approved_paths[proposed] = data["id"]
    return failures, warnings


def validate_feedback(root: Path) -> tuple:
    failures: list = []
    warnings: list = []
    path = runtime_dir(root, "feedback", "feedback.json")
    entries = load_json(path, []) or []
    for entry in entries:
        entry_failures, _warnings = validate_feedback_shape(entry)
        failures += [f"feedback {entry.get('feedbackId')}: {m}" for m in entry_failures]
        if _contains_secret(entry):
            failures.append(f"feedback {entry.get('feedbackId')}: possible secret content detected")
    return failures, warnings


def validate_audit(root: Path) -> tuple:
    failures: list = []
    warnings: list = []
    directory = runtime_dir(root, "audit")
    if not directory.is_dir():
        return failures, warnings
    ok, errors = validate_chain(root)
    if not ok:
        failures.extend(f"audit chain failure: {e}" for e in errors)
    return failures, warnings


def validate_mcp_registration(root: Path) -> tuple:
    """Every schema-declared tool/resource must have a matching adapter handler."""
    failures: list = []
    warnings: list = []
    try:
        from mcp_server import schemas
        from mcp_server.adapter import McpAdapter
    except ImportError as exc:
        warnings.append(f"MCP modules not importable: {exc}")
        return failures, warnings

    adapter_methods = {name for name in dir(McpAdapter) if name.startswith("_tool_")}
    for tool in schemas.TOOLS:
        method_name = f"_tool_{tool['name']}"
        if method_name not in adapter_methods:
            failures.append(f"MCP registration mismatch: tool {tool['name']!r} has no adapter handler")

    resource_uris = {r["uri"] for r in schemas.RESOURCES}
    adapter = McpAdapter(root)
    handlers = adapter._resource_handlers() if hasattr(adapter, "_resource_handlers") else {}
    for uri in resource_uris:
        if uri not in handlers:
            failures.append(f"MCP registration mismatch: resource {uri!r} has no adapter handler")
    return failures, warnings


def validate_dashboard_orchestration_data(root: Path) -> tuple:
    failures: list = []
    warnings: list = []
    data = load_json(root / "generated" / "dashboard-data.json")
    if data is None:
        warnings.append("generated/dashboard-data.json not yet built")
        return failures, warnings
    if "orchestration" not in data:
        failures.append("dashboard Phase 8 data mismatch: 'orchestration' key missing from generated/dashboard-data.json")
        return failures, warnings
    required_keys = {"agentCount", "workflowCount", "knowledgeHealthScore"}
    missing = required_keys - set(data["orchestration"].keys())
    if missing:
        failures.append(f"dashboard Phase 8 data mismatch: missing keys {sorted(missing)}")
    return failures, warnings


def validate_all(root: Path) -> tuple:
    """Run every Phase 8 structural check. Returns (failures, warnings)."""
    checks = [
        validate_agent_registry(build_agent_registry(root)),
        validate_workflow_registry(build_workflow_registry(root)),
        validate_generated_registries(root),
        validate_sessions(root),
        validate_approvals(root),
        validate_memory_suggestions(root),
        validate_feedback(root),
        validate_audit(root),
        validate_mcp_registration(root),
        validate_dashboard_orchestration_data(root),
    ]
    failures: list = []
    warnings: list = []
    for check_failures, check_warnings in checks:
        failures.extend(check_failures)
        warnings.extend(check_warnings)
    return failures, warnings
