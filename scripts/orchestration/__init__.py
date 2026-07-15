"""Continuous learning and agent orchestration modules (Phase 8).

This package plans, classifies, and tracks work — it does not execute it.
No module here performs Git operations, arbitrary shell execution, network
access, or automatic writes to source-of-truth documents. The only file
this package may create under `memory/` is via an explicitly approved
memory-suggestion promotion (see `memory_suggestions.approve`).
"""
from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
GENERATOR = "ai-os-orchestration"

# Local runtime state (git-ignored) vs. generated/ (committed, deterministic).
RUNTIME_DIR = ".ai-os"

# Bounds — keep local runtime artifacts small and predictable.
MAX_LIST_ITEMS = 200
MAX_TASK_CHARS = 2000
MAX_COMMENT_CHARS = 1000
MAX_EXCERPT_CHARS = 2000
DEFAULT_RETRIEVAL_LIMIT = 20
MAX_RETRIEVAL_LIMIT = 100
AUDIT_MAX_ENTRIES_PER_FILE = 500

INTENTS = [
    "feature-development",
    "bug-fix",
    "troubleshooting",
    "documentation",
    "release",
    "validation",
    "research",
    "project-planning",
    "incident-response",
    "knowledge-maintenance",
    "procedure-creation",
    "unknown",
]

WORKFLOW_TYPES = [
    "feature-development",
    "bug-fix",
    "documentation-update",
    "release-preparation",
    "incident-response",
    "knowledge-maintenance",
    "project-onboarding",
    "procedure-creation",
]

# intent -> default workflow id, used when a suggested workflow isn't overridden.
INTENT_WORKFLOW = {
    "feature-development": "workflow:feature-development",
    "bug-fix": "workflow:bug-fix",
    "troubleshooting": "workflow:incident-response",
    "documentation": "workflow:documentation-update",
    "release": "workflow:release-preparation",
    "validation": "workflow:knowledge-maintenance",
    "research": "workflow:knowledge-maintenance",
    "project-planning": "workflow:project-onboarding",
    "incident-response": "workflow:incident-response",
    "knowledge-maintenance": "workflow:knowledge-maintenance",
    "procedure-creation": "workflow:procedure-creation",
    "unknown": None,
}

SESSION_STATUSES = [
    "planned", "approved", "active", "blocked", "validation",
    "completed", "failed", "cancelled", "archived",
]

# Allowed status transitions (from -> set of allowed next statuses).
SESSION_TRANSITIONS = {
    "planned": {"approved", "cancelled"},
    "approved": {"active", "cancelled"},
    "active": {"blocked", "validation", "failed", "cancelled"},
    "blocked": {"active", "cancelled", "failed"},
    "validation": {"completed", "failed", "active"},
    "completed": {"archived"},
    "failed": {"archived"},
    "cancelled": {"archived"},
    "archived": set(),
}

APPROVAL_TYPES = [
    "plan",
    "source-modification",
    "permanent-memory",
    "knowledge-document-update",
    "workflow-continuation",
    "controlled-validation",
    "session-completion",
]

APPROVAL_STATUSES = ["pending", "approved", "rejected", "expired", "cancelled"]

FEEDBACK_TYPES = [
    "helpful", "incorrect", "outdated", "missing-information",
    "wrong-project", "wrong-procedure", "unsafe", "incomplete", "ranking-problem",
]

FEEDBACK_STATUSES = ["open", "resolved"]

AGENT_ROLES = [
    "planning", "architecture", "building", "review", "quality-assurance",
    "documentation", "security", "release", "project-management", "research",
]

# Universal restrictions applied to every agent regardless of role — these
# mirror AGENTS.md / SECURITY.md, which forbid them for all roles.
UNIVERSAL_FORBIDDEN_ACTIONS = [
    "git_commit",
    "git_push",
    "git_merge",
    "git_tag",
    "arbitrary_shell_execution",
    "secret_access",
    "network_access",
    "automatic_approval",
]
