"""Validation for dashboard artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from . import SCHEMA_VERSION


class DashboardError(ValueError):
    """Raised when dashboard validation fails."""
    pass


def load_dashboard_data(path: Path) -> dict:
    """Load dashboard data JSON."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DashboardError(f"unable to read dashboard data: {path}: {exc}") from exc
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise DashboardError(f"invalid JSON in dashboard data: {exc}") from exc


def validate_dashboard_data(data: object) -> tuple[list[str], list[str]]:
    """Validate dashboard data object. Returns (failures, warnings)."""
    failures: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        failures.append("dashboard data root must be an object")
        return failures, warnings

    if data.get("schemaVersion") != SCHEMA_VERSION:
        failures.append("schemaVersion is missing or unsupported")

    for field in ("generatedAt", "generator"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a nonempty string")

    for section in ("repository", "skills", "memory", "knowledgeGraph", "discovery", "artifacts", "orchestration", "professionalContext"):
        if not isinstance(data.get(section), dict):
            failures.append(f"{section} must be an object")

    # Check artifacts section
    artifacts = data.get("artifacts", {})
    if isinstance(artifacts, dict):
        art_list = artifacts.get("artifacts", [])
        if isinstance(art_list, list):
            missing = [a for a in art_list if isinstance(a, dict) and not a.get("exists")]
            if missing:
                warnings.append(f"{len(missing)} artifact(s) missing or stale")

    return failures, warnings


def validate_dashboard_html(path: Path) -> tuple[list[str], list[str]]:
    """Basic validation of dashboard HTML file."""
    failures: list[str] = []
    warnings: list[str] = []

    if not path.is_file():
        failures.append("dashboard.html is missing")
        return failures, warnings

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        failures.append(f"unable to read dashboard.html: {exc}")
        return failures, warnings

    if "<!DOCTYPE html>" not in content:
        failures.append("dashboard.html missing DOCTYPE")
    if "<title>" not in content:
        failures.append("dashboard.html missing title element")
    if "AI OS Dashboard" not in content:
        failures.append("dashboard.html missing expected title text")
    if "__DASHBOARD_DATA__" in content:
        failures.append("dashboard.html contains unrendered template placeholder")

    return failures, warnings


def _strip_volatile_fields(data: dict) -> dict:
    """Return a copy of dashboard data with non-reproducible fields blanked.

    generatedAt and per-artifact fileTimestamp reflect wall-clock/filesystem
    mtime, which git does not preserve across checkouts, so they must be
    excluded from staleness comparisons or the check can never pass on a
    fresh clone.
    """
    result = dict(data)
    result["generatedAt"] = "<ignored>"
    artifacts = result.get("artifacts")
    if isinstance(artifacts, dict) and isinstance(artifacts.get("artifacts"), list):
        result["artifacts"] = dict(artifacts)
        result["artifacts"]["artifacts"] = [
            {**item, "fileTimestamp": "<ignored>"} if isinstance(item, dict) else item
            for item in artifacts["artifacts"]
        ]
    return result


def compare_data_ignoring_generated_at(current: dict, saved: dict) -> bool:
    """Compare two dashboard data objects ignoring volatile timestamp fields."""
    return _strip_volatile_fields(current) == _strip_volatile_fields(saved)
