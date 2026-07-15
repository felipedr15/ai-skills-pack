"""Shared schema field lists and generic structural validation helpers.

Each concrete module (session.py, approvals.py, memory_suggestions.py,
feedback.py, audit.py) owns its own construction and business logic; this
module only centralizes the field lists so validate.py can check every
artifact type without duplicating the schema in two places.
"""
from __future__ import annotations

from . import (
    APPROVAL_STATUSES,
    APPROVAL_TYPES,
    FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    SESSION_STATUSES,
)

SESSION_REQUIRED_FIELDS = [
    "schemaVersion", "sessionId", "createdAt", "updatedAt", "task", "project",
    "intent", "workflowId", "status", "agents", "knowledgeUsed", "steps",
    "approvals", "filesObserved", "filesChanged", "validations", "warnings",
    "failures", "memorySuggestions", "feedback", "metadata",
]

SESSION_LIST_FIELDS = [
    "agents", "knowledgeUsed", "steps", "approvals", "filesObserved",
    "filesChanged", "validations", "warnings", "failures",
    "memorySuggestions", "feedback",
]

APPROVAL_REQUIRED_FIELDS = [
    "approvalId", "type", "status", "requestedAt", "approvedAt", "approvedBy",
    "reason", "target", "metadata",
]

MEMORY_SUGGESTION_REQUIRED_FIELDS = [
    "id", "status", "title", "summary", "problem", "cause", "resolution",
    "validation", "project", "relatedEntities", "sourceSessionId",
    "sensitivity", "confidence", "reasons", "proposedPath", "createdAt",
]

FEEDBACK_REQUIRED_FIELDS = [
    "feedbackId", "createdAt", "type", "targetType", "targetId", "query",
    "comment", "status", "relatedSessionId", "metadata",
]

AUDIT_EVENT_REQUIRED_FIELDS = ["event", "createdAt", "details", "prevHash", "hash"]


def require_fields(obj: dict, fields: list) -> list:
    """Return a list of failure messages for any missing required field."""
    if not isinstance(obj, dict):
        return ["object must be a dict"]
    return [f"missing required field: {field}" for field in fields if field not in obj]


def check_enum(obj: dict, field: str, allowed) -> list:
    if field in obj and obj[field] not in allowed:
        return [f"invalid {field}: {obj.get(field)!r} (allowed: {sorted(allowed)})"]
    return []


def validate_session_shape(obj: dict) -> tuple[list, list]:
    failures = require_fields(obj, SESSION_REQUIRED_FIELDS)
    failures += check_enum(obj, "status", SESSION_STATUSES)
    warnings: list = []
    for field in SESSION_LIST_FIELDS:
        if field in obj and not isinstance(obj[field], list):
            failures.append(f"{field} must be a list")
    return failures, warnings


def validate_approval_shape(obj: dict) -> tuple[list, list]:
    failures = require_fields(obj, APPROVAL_REQUIRED_FIELDS)
    failures += check_enum(obj, "type", APPROVAL_TYPES)
    failures += check_enum(obj, "status", APPROVAL_STATUSES)
    return failures, []


def validate_memory_suggestion_shape(obj: dict) -> tuple[list, list]:
    failures = require_fields(obj, MEMORY_SUGGESTION_REQUIRED_FIELDS)
    warnings = []
    confidence = obj.get("confidence")
    if isinstance(confidence, (int, float)) and confidence < 0.5:
        warnings.append(f"low-confidence memory suggestion: {confidence}")
    return failures, warnings


def validate_feedback_shape(obj: dict) -> tuple[list, list]:
    failures = require_fields(obj, FEEDBACK_REQUIRED_FIELDS)
    failures += check_enum(obj, "type", FEEDBACK_TYPES)
    failures += check_enum(obj, "status", FEEDBACK_STATUSES)
    return failures, []


def validate_audit_event_shape(obj: dict) -> tuple[list, list]:
    failures = require_fields(obj, AUDIT_EVENT_REQUIRED_FIELDS)
    return failures, []
