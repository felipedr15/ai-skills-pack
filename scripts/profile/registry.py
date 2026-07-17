"""profile/registry.json read/write and active-profile resolution."""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import SCHEMA_VERSION

REGISTRY_PATH = "profile/registry.json"


def load_registry(root: Path) -> dict:
    """Load profile/registry.json, defaulting to an empty registry if absent.

    An absent or empty registry is a valid state (no profile authored yet) —
    it is never an error to find no profile/ content in a repository.
    """
    path = root / REGISTRY_PATH
    if not path.is_file():
        return {"schemaVersion": SCHEMA_VERSION, "profiles": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "profiles" not in data or not isinstance(data["profiles"], list):
        raise ValueError("profile/registry.json must contain a profiles array")
    return data


def save_registry(root: Path, data: dict) -> None:
    """Atomic write (temp file + os.replace): a failure partway through
    never leaves profile/registry.json in a partially-written state --
    either the previous content or the new content, never a mix."""
    profiles = sorted(data.get("profiles", []), key=lambda item: item["id"])
    payload = {"schemaVersion": SCHEMA_VERSION, "profiles": profiles}
    path = root / REGISTRY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def active_profile(data: dict) -> dict | None:
    """Return the single active profile entry, or None if none is active.

    An empty profiles list has no active entry by definition — that is a
    valid "not yet configured" state, not an error.
    """
    active = [p for p in data.get("profiles", []) if isinstance(p, dict) and p.get("active") is True]
    if len(active) == 1:
        return active[0]
    return None


def find_profile(data: dict, profile_id: str) -> dict | None:
    for entry in data.get("profiles", []):
        if isinstance(entry, dict) and entry.get("id") == profile_id:
            return entry
    return None
