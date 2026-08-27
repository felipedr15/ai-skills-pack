"""Unified status model for AI OS."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .config import load_config, validate_config
from .utils import GENERATED_ARTIFACTS, GENERATION_ORDER, run_python_script
from .version import read_version


def get_status(root: Path) -> dict:
    """Get a unified status report backed by existing freshness checks."""
    version = _safe(lambda: read_version(root), "unknown")
    config = load_config(root)
    config_failures, config_warnings = validate_config(config)

    gen = root / "generated"
    artifacts = _artifact_status(gen)
    generation_checks = _generation_checks(root)
    failed_generation = [check for check in generation_checks if check["status"] == "FAIL"]
    unknown_generation = [check for check in generation_checks if check["status"] == "UNKNOWN"]
    dashboard_ready = (gen / "dashboard.html").is_file() and (gen / "dashboard-data.json").is_file()
    mcp_ready = (root / "scripts" / "mcp-server.py").is_file()
    artifacts_present = all(a["exists"] for a in artifacts)
    release_ready = (
        len(config_failures) == 0
        and artifacts_present
        and dashboard_ready
        and mcp_ready
        and not failed_generation
        and not unknown_generation
    )

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
        "generationChecks": generation_checks,
        "summary": {
            "repository": "PASS" if root.is_dir() else "FAIL",
            "configuration": "PASS" if len(config_failures) == 0 else "FAIL",
            "generatedFiles": _rollup_status(generation_checks),
            "dashboard": "PASS" if dashboard_ready else "FAIL",
            "mcp": "PASS" if mcp_ready else "FAIL",
            "currentGeneratedChecks": sum(1 for c in generation_checks if c["status"] == "PASS"),
            "failedGeneratedChecks": len(failed_generation),
            "unknownGeneratedChecks": len(unknown_generation),
        },
        "dashboard": {
            "htmlPresent": (gen / "dashboard.html").is_file(),
            "dataPresent": (gen / "dashboard-data.json").is_file(),
        },
        "mcp": {
            "serverPresent": (root / "scripts" / "mcp-server.py").is_file(),
            "readOnly": config.get("mcp", {}).get("readOnly", True),
        },
        "releaseReady": release_ready,
    }


def _artifact_status(gen: Path) -> list[dict]:
    """Check existence of key generated artifacts."""
    results = []
    for name in GENERATED_ARTIFACTS:
        path = gen / name
        results.append({"path": name, "exists": path.is_file()})
    return results


def _generation_checks(root: Path) -> list[dict]:
    """Run read-only generated-artifact freshness checks."""
    checks: list[dict] = []
    for script, label in GENERATION_ORDER:
        try:
            rc, out, err = run_python_script(script, ["--check"], root, timeout=60)
            checks.append({
                "name": label,
                "script": script,
                "status": "PASS" if rc == 0 else "FAIL",
                "detail": _last_line(out + err),
            })
        except Exception as exc:
            checks.append({
                "name": label,
                "script": script,
                "status": "UNKNOWN",
                "detail": str(exc),
            })
    return checks


def _rollup_status(checks: list[dict]) -> str:
    if not checks:
        return "UNKNOWN"
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "PASS"


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default
