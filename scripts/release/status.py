"""Unified status model for AI OS."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import load_config, validate_config
from .version import read_version


def get_status(root: Path) -> dict:
    """Get a lightweight unified status report."""
    version = _safe(lambda: read_version(root), "unknown")
    config = load_config(root)
    config_failures, config_warnings = validate_config(config)

    gen = root / "generated"
    artifacts = _artifact_status(gen)

    return {
        "version": version,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "repository": str(root),
        "configuration": {
            "valid": len(config_failures) == 0,
            "warnings": config_warnings,
            "failures": config_failures,
        },
        "artifacts": artifacts,
        "dashboard": {
            "htmlPresent": (gen / "dashboard.html").is_file(),
            "dataPresent": (gen / "dashboard-data.json").is_file(),
        },
        "mcp": {
            "serverPresent": (root / "scripts" / "mcp-server.py").is_file(),
            "readOnly": config.get("mcp", {}).get("readOnly", True),
        },
        "releaseReady": len(config_failures) == 0 and all(a["exists"] for a in artifacts),
    }


def _artifact_status(gen: Path) -> list[dict]:
    """Check existence of key generated artifacts."""
    names = [
        "skills.json", "repository-index.json", "memory-index.json",
        "knowledge-graph.json", "discovery-index.json",
        "dashboard.html", "dashboard-data.json",
    ]
    results = []
    for name in names:
        path = gen / name
        results.append({"path": name, "exists": path.is_file()})
    return results


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default
