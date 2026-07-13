"""Shared utilities for the AI OS service layer."""
from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: Path) -> dict | None:
    """Load a generated JSON artifact, returning None if unavailable."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def artifact_status(path: Path) -> dict:
    """Get status metadata for a generated artifact."""
    if not path.is_file():
        return {
            "path": path.name,
            "exists": False,
            "schemaVersion": None,
            "generator": None,
            "generatedAt": None,
            "valid": False,
        }
    data = load_json_artifact(path)
    if data is None:
        return {
            "path": path.name,
            "exists": True,
            "schemaVersion": None,
            "generator": None,
            "generatedAt": None,
            "valid": False,
        }
    return {
        "path": path.name,
        "exists": True,
        "schemaVersion": data.get("schemaVersion"),
        "generator": data.get("generator"),
        "generatedAt": data.get("generatedAt"),
        "valid": True,
    }
