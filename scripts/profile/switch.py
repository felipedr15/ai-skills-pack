"""profile switch (Task 013): the only code path allowed to change which
profile/registry.json entry is `active`.

This module is pure validation + mutation and performs no approval check
itself -- the approval gate (Task 014) is enforced by the CLI layer
(`ai-os.py`'s `profile switch` handler), mirroring how `session start`'s
plan-approval gate and `memory-suggestions approve`'s permanent-memory
gate are both orchestrated at the CLI layer rather than inside the
scripts/profile or scripts/orchestration domain modules themselves. This
keeps scripts/profile free of a dependency on scripts/orchestration,
consistent with every other module in this package (Tasks 001-011).

Leaves profile/registry.json byte-for-byte unchanged on any failure:
unknown id, invalid registry, or an empty registry with nothing to
switch. The write itself is atomic (registry.save_registry).
"""
from __future__ import annotations

from pathlib import Path

from . import SCHEMA_VERSION
from . import registry as profile_registry
from . import validate as profile_validate


class SwitchError(ValueError):
    pass


def _apply_active(profiles: list, target_id: str) -> list:
    updated = []
    found = False
    for entry in profiles:
        entry = dict(entry)
        is_target = entry.get("id") == target_id
        entry["active"] = is_target
        found = found or is_target
        updated.append(entry)
    if not found:
        raise SwitchError(f"unknown profile id: {target_id!r}")
    return updated


def switch(root: Path, target_id: str) -> dict:
    """Validate the complete registry, then atomically activate
    `target_id` and deactivate every other profile.

    Idempotent: switching to the already-active profile re-validates and
    re-writes the same content, succeeding without error. Callers must
    gate this on an approved 'profile-switch' approval before calling --
    this function itself performs no approval check and is not, on its
    own, sufficient authorization to mutate the registry.
    """
    data = profile_registry.load_registry(root)
    failures, _warnings = profile_validate.validate_registry_shape(data)
    if failures:
        raise SwitchError("invalid profile registry: " + "; ".join(failures))

    if not data.get("profiles"):
        raise SwitchError("no profiles registered; nothing to switch")

    new_profiles = _apply_active(data["profiles"], target_id)
    new_data = {"schemaVersion": data.get("schemaVersion", SCHEMA_VERSION), "profiles": new_profiles}

    failures, _warnings = profile_validate.validate_registry_shape(new_data)
    if failures:
        raise SwitchError("switch would produce an invalid registry: " + "; ".join(failures))

    profile_registry.save_registry(root, new_data)
    return profile_registry.active_profile(new_data)
