"""Field lists and enums for professional profile and expertise records."""
from __future__ import annotations

import re

# Fixed evidence-based proficiency levels (REQ-003). Do not extend without
# updating requirements.md/design.md first — this set is a resolved decision.
PROFICIENCY_LEVELS = ["foundational", "working", "proficient", "advanced", "lead"]

# Fixed evidence-pointer types (design.md Data Model). "ref" values under
# each type are normalized identifiers, never free text or file paths.
EVIDENCE_TYPES = ["project", "role", "source", "session", "workActivity", "memory"]

EXPERTISE_SOURCE_VALUES = ["user", "agent-suggested"]
EXPERTISE_STATUS_VALUES = ["proposed", "approved"]

# Professional-context data defaults to high sensitivity (NFR Security/Privacy);
# this is currently the only allowed value.
SENSITIVITY_VALUES = ["high"]

# Forward-looking approval target types for scripts/orchestration/approvals.py
# (wired in a later Phase 9 task group). Hyphenated to match the existing
# APPROVAL_TYPES convention in scripts/orchestration/__init__.py.
APPROVAL_TARGET_TYPES = ["profile-write", "expertise-write", "profile-switch"]

# Profile-only front-matter keys that must never appear in a memory/ record
# (REQ-001/REQ-005 boundary). Shared with scripts/memory_utils.py so the
# reserved-key list is defined exactly once.
RESERVED_PROFILE_KEYS = ("role", "team", "reportingTo")

REGISTRY_REQUIRED_FIELDS = ["schemaVersion", "profiles"]
REGISTRY_ENTRY_REQUIRED_FIELDS = ["id", "path", "active", "createdAt"]

PROFILE_REQUIRED_FIELDS = [
    "id", "schemaVersion", "role", "team", "responsibilities",
    "reportingTo", "sensitivity", "createdAt", "updatedAt",
]

EXPERTISE_FILE_REQUIRED_FIELDS = ["schemaVersion", "profileId", "updatedAt", "entries"]

EXPERTISE_ENTRY_REQUIRED_FIELDS = [
    "id", "name", "level", "evidence", "source", "status", "createdAt", "updatedAt",
]

EVIDENCE_POINTER_REQUIRED_FIELDS = ["type", "ref"]

_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_normalized_identifier(value: object) -> bool:
    """Return True if value is a lowercase, hyphenated identifier (a slug).

    Used for profile/registry ids and evidence pointer `ref` values — never
    free text, whitespace, or a file path, so identifiers cannot smuggle in
    raw source material (REQ-003, design.md Security).
    """
    if not isinstance(value, str) or not value:
        return False
    if ".." in value or "/" in value or "\\" in value:
        return False
    return bool(_ID_PATTERN.match(value))
