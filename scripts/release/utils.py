"""Shared utilities for the release package."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .version import get_repo_root


def now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_python_script(script: str, args: list[str] | None = None, root: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """Run a Python script safely. Returns (returncode, stdout, stderr)."""
    if root is None:
        root = get_repo_root()
    cmd = [sys.executable, str(root / script)] + (args or [])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(root), timeout=timeout,
            env={**os.environ, "AI_OS_SKIP_TESTS": os.environ.get("AI_OS_SKIP_TESTS", "0")},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"
    except OSError as exc:
        return 1, "", str(exc)


def print_result(label: str, passed: bool, detail: str = ""):
    """Print a PASS/FAIL result line."""
    status = "PASS" if passed else "FAIL"
    line = f"{status} {label}"
    if detail:
        line += f" ({detail})"
    print(line)


def print_warning(label: str, detail: str = ""):
    """Print a WARNING line."""
    line = f"WARNING {label}"
    if detail:
        line += f" ({detail})"
    print(line)


def ensure_directory(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def load_json_safe(path: Path) -> dict | None:
    """Load JSON safely, returning None on failure."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


GENERATED_ARTIFACTS = [
    "skills.json", "skills.md",
    "repository-index.json", "repository-map.md",
    "memory-index.json", "memory-index.md",
    "profile-index.json", "profile-index.md",
    "knowledge-graph.json", "knowledge-graph.md",
    "discovery-index.json", "discovery-index.md",
    "agent-registry.json", "agent-registry.md",
    "workflow-registry.json", "workflow-registry.md",
    "knowledge-health.json", "knowledge-health.md",
    "work-activity.json", "work-activity.md",
    "dashboard.html", "dashboard-data.json",
    "release-manifest.json", "release-manifest.md",
]

GENERATION_ORDER = [
    ("scripts/generate-skill-registry.py", "skill registry"),
    ("scripts/generate-memory-index.py", "memory index"),
    ("scripts/generate-profile-index.py", "profile index"),
    ("scripts/index-repository.py", "repository index"),
    ("scripts/generate-knowledge-graph.py", "knowledge graph"),
    ("scripts/discovery-build.py", "discovery index"),
    ("scripts/generate-agent-registry.py", "agent registry"),
    ("scripts/generate-workflow-registry.py", "workflow registry"),
    ("scripts/generate-knowledge-health.py", "knowledge health"),
    ("scripts/generate-work-activity.py", "work activity"),
    ("scripts/dashboard-build.py", "dashboard"),
]
