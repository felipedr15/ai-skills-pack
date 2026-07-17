"""Structural validation for profile records, the registry, and expertise entries.

Validation here is deliberately conservative: it never asserts a proficiency
level or professional fact is *true*, only that the record is well-formed,
that evidence is present in the shape design.md requires, and that the
`profile/` vs `memory/` boundary (REQ-001/REQ-005) holds. Expertise claims
are only ever as credible as the evidence attached to them — this module
enforces that evidence exists and is well-formed, not that it is sufficient.
"""
from __future__ import annotations

from .schema import (
    EVIDENCE_POINTER_REQUIRED_FIELDS,
    EVIDENCE_TYPES,
    EXPERTISE_ENTRY_REQUIRED_FIELDS,
    EXPERTISE_FILE_REQUIRED_FIELDS,
    EXPERTISE_SOURCE_VALUES,
    EXPERTISE_STATUS_VALUES,
    PROFICIENCY_LEVELS,
    PROFILE_REQUIRED_FIELDS,
    REGISTRY_ENTRY_REQUIRED_FIELDS,
    REGISTRY_REQUIRED_FIELDS,
    SENSITIVITY_VALUES,
    is_normalized_identifier,
)


def _require_fields(obj: object, fields: list[str], label: str) -> list[str]:
    if not isinstance(obj, dict):
        return [f"{label} must be an object"]
    return [f"{label} missing required field: {field}" for field in fields if field not in obj]


def validate_registry_shape(data: object) -> tuple[list[str], list[str]]:
    """Validate profile/registry.json. An empty profiles list is valid."""
    failures = _require_fields(data, REGISTRY_REQUIRED_FIELDS, "registry")
    warnings: list[str] = []
    if failures:
        return failures, warnings

    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        return ["registry.profiles must be a list"], warnings

    seen_ids: set[str] = set()
    active_count = 0
    for entry in profiles:
        failures += _require_fields(entry, REGISTRY_ENTRY_REQUIRED_FIELDS, "registry entry")
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id")
        if entry_id is not None:
            if not is_normalized_identifier(entry_id):
                failures.append(f"registry entry id must be a normalized identifier: {entry_id!r}")
            elif entry_id in seen_ids:
                failures.append(f"duplicate profile id in registry: {entry_id!r}")
            seen_ids.add(entry_id)
        if not isinstance(entry.get("active"), bool):
            failures.append(f"registry entry active must be a boolean: {entry.get('id')!r}")
        elif entry.get("active") is True:
            active_count += 1

    # Exactly one profile must be active once at least one profile exists.
    # An empty registry (no profiles at all) has zero active by definition —
    # that is a valid "not yet configured" state, not a failure.
    if profiles and active_count == 0:
        failures.append("no active profile: exactly one profile must be marked active")
    elif active_count > 1:
        failures.append(f"more than one active profile ({active_count}); exactly one must be active")

    return failures, warnings


def validate_profile_record(metadata: object) -> tuple[list[str], list[str]]:
    """Validate a profile/<id>.md record's front-matter metadata."""
    failures = _require_fields(metadata, PROFILE_REQUIRED_FIELDS, "profile record")
    warnings: list[str] = []
    if not isinstance(metadata, dict):
        return failures, warnings

    profile_id = metadata.get("id")
    if profile_id is not None and not is_normalized_identifier(profile_id):
        failures.append(f"profile id must be a normalized identifier: {profile_id!r}")

    for field in ("role", "team"):
        value = metadata.get(field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            failures.append(f"{field} must be a non-empty string")

    responsibilities = metadata.get("responsibilities")
    if responsibilities is not None and not isinstance(responsibilities, list):
        failures.append("responsibilities must be a list")

    reporting_to = metadata.get("reportingTo")
    if reporting_to is not None and not isinstance(reporting_to, str):
        failures.append("reportingTo must be a string or null")

    sensitivity = metadata.get("sensitivity")
    if sensitivity is not None and sensitivity not in SENSITIVITY_VALUES:
        failures.append(f"invalid sensitivity: {sensitivity!r} (allowed: {SENSITIVITY_VALUES})")

    return failures, warnings


def validate_evidence_pointer(pointer: object) -> list[str]:
    """Structural validation of a single {type, ref} evidence pointer.

    Does not check whether `ref` resolves against any other data source —
    Phase 9 does not require that (design.md); see check_evidence_resolution
    for the separate, optional resolution-warning behavior.
    """
    if not isinstance(pointer, dict):
        return ["evidence entry must be an object"]

    failures = [
        f"evidence pointer missing required field: {field}"
        for field in EVIDENCE_POINTER_REQUIRED_FIELDS
        if not pointer.get(field)
    ]

    ptype = pointer.get("type")
    if ptype is not None and ptype not in EVIDENCE_TYPES:
        failures.append(f"invalid evidence type: {ptype!r} (allowed: {EVIDENCE_TYPES})")

    ref = pointer.get("ref")
    if ref is not None and not is_normalized_identifier(ref):
        failures.append(
            f"evidence ref must be a normalized identifier, never free text or a file path: {ref!r}"
        )

    return failures


def validate_expertise_entry(entry: object) -> tuple[list[str], list[str]]:
    """Validate a single expertise entry, including its evidence pointers."""
    failures = _require_fields(entry, EXPERTISE_ENTRY_REQUIRED_FIELDS, "expertise entry")
    warnings: list[str] = []
    if not isinstance(entry, dict):
        return failures, warnings

    entry_id = entry.get("id")
    if entry_id is not None and not is_normalized_identifier(entry_id):
        failures.append(f"expertise entry id must be a normalized identifier: {entry_id!r}")

    name = entry.get("name")
    if name is not None and (not isinstance(name, str) or not name.strip()):
        failures.append("expertise entry name must be a non-empty string")

    level = entry.get("level")
    if level is not None and level not in PROFICIENCY_LEVELS:
        failures.append(f"invalid expertise level: {level!r} (allowed: {PROFICIENCY_LEVELS})")

    evidence = entry.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, list) or not evidence:
            # REQ-003: expertise claims must be evidence-based — at least one
            # evidence pointer is required, not merely recommended.
            failures.append(
                f"expertise entry {entry_id!r} must have at least one evidence pointer"
            )
        else:
            for pointer in evidence:
                failures += [f"expertise entry {entry_id!r}: {msg}" for msg in validate_evidence_pointer(pointer)]

    source = entry.get("source")
    if source is not None and source not in EXPERTISE_SOURCE_VALUES:
        failures.append(f"invalid expertise source: {source!r} (allowed: {EXPERTISE_SOURCE_VALUES})")

    status = entry.get("status")
    if status is not None and status not in EXPERTISE_STATUS_VALUES:
        failures.append(f"invalid expertise status: {status!r} (allowed: {EXPERTISE_STATUS_VALUES})")

    return failures, warnings


def validate_expertise_file(data: object) -> tuple[list[str], list[str]]:
    """Validate a profile/<id>.expertise.json object."""
    failures = _require_fields(data, EXPERTISE_FILE_REQUIRED_FIELDS, "expertise file")
    warnings: list[str] = []
    if failures:
        return failures, warnings

    entries = data.get("entries")
    if not isinstance(entries, list):
        return ["expertise file entries must be a list"], warnings

    seen_ids: set[str] = set()
    for entry in entries:
        entry_failures, entry_warnings = validate_expertise_entry(entry)
        failures += entry_failures
        warnings += entry_warnings
        if isinstance(entry, dict):
            entry_id = entry.get("id")
            if entry_id in seen_ids:
                failures.append(f"duplicate expertise entry id: {entry_id!r}")
            seen_ids.add(entry_id)

    return failures, warnings


def check_evidence_resolution(entries: list, known_refs: set | None) -> list[str]:
    """Return warnings for evidence pointers whose ref doesn't resolve.

    known_refs is the set of ids/slugs known to other Phase 9 data sources
    (work-activity projects, sessions, etc.). Pass None when no resolution
    context is available (e.g. before those generators exist) — in that case
    nothing is checked, since Phase 9 does not require refs to resolve
    (design.md). An unresolved ref is always a warning, never a failure, and
    the entry is never dropped.
    """
    if known_refs is None:
        return []
    warnings: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for pointer in entry.get("evidence", []):
            if not isinstance(pointer, dict):
                continue
            ref = pointer.get("ref")
            if ref and ref not in known_refs:
                warnings.append(
                    f"unresolved evidence ref (kept as authored): {ref!r} "
                    f"in expertise entry {entry.get('id')!r}"
                )
    return warnings
