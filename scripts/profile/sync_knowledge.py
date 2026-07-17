"""profile sync-knowledge: safe scaffold + explicit --force-refresh snapshots
(Tasks 008-011).

Task 008 (safe default): creates knowledge/professional-context/overview.md
only if it does not already exist. If it already exists, this is a no-op
that leaves it byte-for-byte unchanged and reports that no overwrite
occurred.

Task 009 (--force-refresh): the only mutating path, and even then it never
touches overview.md itself -- it snapshots the current, pre-refresh
curated content into a new timestamped file under snapshots/. Refuses to
run if no overview.md exists yet (nothing to snapshot) and refuses if the
pre-refresh content fails sanitization.

Task 010 (snapshots): filenames are
`professional-context-YYYY-MM-DDTHHMMSSZ.md` (UTC, second precision) --
filesystem-safe on Windows and POSIX (no colons, no spaces), deterministic
for a given timestamp, and collision-resistant: a second invocation
landing on the same second raises rather than silently overwriting or
inventing a disambiguating suffix.

Task 011 (sanitization + non-mutation): every write path -- scaffold and
snapshot alike -- is gated by scripts/profile/sanitize.py before anything
touches disk. This module is reached *only* through the explicit
`ai-os.py profile sync-knowledge` CLI command; it is never imported or
invoked by ai-os.py generate, generate --check, validate-all.py, the
dashboard, MCP, repository indexing, knowledge-graph generation, or
semantic-discovery generation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import registry as profile_registry
from .sanitize import SanitizationError, assert_sanitized

KNOWLEDGE_DIR = "knowledge/professional-context"
OVERVIEW_PATH = f"{KNOWLEDGE_DIR}/overview.md"
SNAPSHOTS_DIR = f"{KNOWLEDGE_DIR}/snapshots"
SNAPSHOT_TIMESTAMP_FORMAT = "%Y-%m-%dT%H%M%SZ"


class SyncKnowledgeError(ValueError):
    pass


def snapshot_filename(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return f"professional-context-{moment.strftime(SNAPSHOT_TIMESTAMP_FORMAT)}.md"


def build_overview_content(root: Path) -> str:
    """Render the professional-context overview from profile/ + generated/
    work-activity.json only. Never fabricates profile facts: if no active
    profile is configured, the overview says so plainly instead of
    inventing content.
    """
    registry = profile_registry.load_registry(root)
    active = profile_registry.active_profile(registry)

    lines = [
        "# Professional Context Overview",
        "",
        "> Scaffolded by `ai-os.py profile sync-knowledge`. This file is curated —",
        "> edit it directly. Re-running sync-knowledge will not overwrite it;",
        "> use `--force-refresh` to snapshot the current content instead.",
        "",
        "## Professional Profile",
        "",
    ]
    if active is None:
        lines += [
            "No active professional profile is configured yet. Author "
            "`profile/<id>.md` and register it in `profile/registry.json` "
            "to populate this section.",
            "",
        ]
    else:
        lines += [
            f"- Active profile id: `{active.get('id', '')}`",
            f"- Source: `{active.get('path', '')}`",
            "",
        ]

    lines += ["## Work Activity Summary", ""]
    work_activity_path = root / "generated" / "work-activity.json"
    if work_activity_path.is_file():
        data = json.loads(work_activity_path.read_text(encoding="utf-8"))
        projects = data.get("projects", [])
        focus_areas = data.get("focusAreas", [])
        summary = data.get("activitySummary", {})
        lines.append(f"- Tracked projects: {len(projects)}")
        if focus_areas:
            top_terms = ", ".join(area["term"] for area in focus_areas[:5])
            lines.append(f"- Top focus areas: {top_terms}")
        lines.append(f"- Total memory records: {summary.get('totalMemoryRecords', 0)}")
        lines.append("")
    else:
        lines += ["Not yet generated. Run `ai-os.py generate` first.", ""]

    return "\n".join(lines)


def sync(root: Path) -> dict:
    """Safe default: scaffold overview.md only if absent."""
    overview_path = root / OVERVIEW_PATH
    if overview_path.is_file():
        return {
            "status": "unchanged",
            "path": OVERVIEW_PATH,
            "message": f"{OVERVIEW_PATH} already exists; no overwrite performed",
        }

    content = build_overview_content(root)
    assert_sanitized(content, context=OVERVIEW_PATH)

    overview_path.parent.mkdir(parents=True, exist_ok=True)
    overview_path.write_text(content, encoding="utf-8", newline="\n")
    return {"status": "created", "path": OVERVIEW_PATH, "message": f"{OVERVIEW_PATH} created"}


def force_refresh(root: Path, now: datetime | None = None) -> dict:
    """Explicit mutating action: snapshot the pre-refresh curated content.

    overview.md itself is never written by this function -- only a new
    snapshot file is created, capturing the content exactly as it was
    before this call.
    """
    overview_path = root / OVERVIEW_PATH
    if not overview_path.is_file():
        raise SyncKnowledgeError(
            f"no curated {OVERVIEW_PATH} exists yet; run sync-knowledge "
            "(without --force-refresh) first"
        )

    pre_refresh_content = overview_path.read_text(encoding="utf-8")
    assert_sanitized(pre_refresh_content, context=f"pre-refresh {OVERVIEW_PATH}")

    filename = snapshot_filename(now)
    snapshot_rel = f"{SNAPSHOTS_DIR}/{filename}"
    snapshot_path = root / snapshot_rel
    if snapshot_path.exists():
        raise SyncKnowledgeError(
            f"snapshot collision: {snapshot_rel} already exists for this "
            "timestamp; wait a second and try again"
        )

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(pre_refresh_content, encoding="utf-8", newline="\n")
    return {
        "status": "snapshotted",
        "path": snapshot_rel,
        "message": f"snapshotted pre-refresh content to {snapshot_rel}",
    }
