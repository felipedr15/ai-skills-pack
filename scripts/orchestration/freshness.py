"""Knowledge freshness / review-due detection (Phase 8, Part 10).

Pure read. Never writes review dates or document metadata. Only documents
that opt in — by declaring at least one of `owner`, `status`,
`lastReviewed`, `reviewIntervalDays`, or `nextReview` in their front matter —
are considered; this repo's Phases 1-7 docs mostly predate this convention,
so an empty result here is expected and correct, not a bug.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

from .utils import ensure_scripts_path

ensure_scripts_path()
from knowledge_graph.utils import parse_front_matter  # noqa: E402

# Deliberately excludes "status" — skills and memory records already use a
# generic "status" front-matter field for unrelated lifecycle concerns
# (e.g. skill stability, memory record state). Requiring one of these more
# specific fields avoids false-positive opt-in on existing documents.
FRESHNESS_OPT_IN_FIELDS = {"owner", "lastReviewed", "reviewIntervalDays", "nextReview"}
STATUSES = {"draft", "approved", "deprecated", "archived", "needs-review"}
SCAN_ROOTS = ["knowledge", "agents", ".agent/skills"]
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _candidate_docs(root: Path) -> list:
    docs = []
    for rel in SCAN_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        docs.extend(sorted(base.rglob("*.md")))
    return docs


def _parse_date(value) -> date | None:
    if not isinstance(value, str) or not DATE_PATTERN.match(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def scan_freshness(root: Path) -> list:
    """Return freshness records for every document that opts into the schema."""
    records = []
    for path in _candidate_docs(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        front = parse_front_matter(text)
        if not (FRESHNESS_OPT_IN_FIELDS & set(front.keys())):
            continue

        rel_path = path.relative_to(root).as_posix()
        issues = []
        owner = front.get("owner")
        status = front.get("status")
        last_reviewed = _parse_date(front.get("lastReviewed"))
        interval_raw = front.get("reviewIntervalDays")
        next_review = _parse_date(front.get("nextReview"))

        if not owner:
            issues.append("missing owner")
        if status is not None and status not in STATUSES:
            issues.append(f"invalid status: {status}")
        if front.get("lastReviewed") and last_reviewed is None:
            issues.append(f"invalid lastReviewed date: {front.get('lastReviewed')!r}")
        if front.get("nextReview") and next_review is None:
            issues.append(f"invalid nextReview date: {front.get('nextReview')!r}")

        interval_days = None
        if interval_raw is not None:
            try:
                interval_days = int(interval_raw)
            except (TypeError, ValueError):
                issues.append(f"invalid reviewIntervalDays: {interval_raw!r}")
        elif last_reviewed is not None and next_review is None:
            issues.append("missing reviewIntervalDays")

        if next_review is None and last_reviewed is not None and interval_days is not None:
            next_review = last_reviewed + timedelta(days=interval_days)

        if status == "deprecated":
            issues.append("deprecated document still referenced")

        records.append({
            "path": rel_path,
            "owner": owner,
            "status": status,
            "lastReviewed": front.get("lastReviewed"),
            "reviewIntervalDays": interval_days,
            "nextReview": next_review.isoformat() if next_review else front.get("nextReview"),
            "issues": issues,
        })
    records.sort(key=lambda r: r["path"])
    return records


def review_due(root: Path, *, days: int = 0) -> list:
    """Documents overdue for review, or due within `days` from today."""
    today = date.today()
    horizon = today + timedelta(days=max(0, days))
    due = []
    for record in scan_freshness(root):
        next_review = _parse_date(record.get("nextReview"))
        overdue = next_review is not None and next_review < today
        due_soon = next_review is not None and today <= next_review <= horizon
        has_metadata_issue = bool(record["issues"])
        if overdue or due_soon or has_metadata_issue:
            entry = dict(record)
            entry["overdue"] = overdue
            entry["dueSoon"] = due_soon and not overdue
            due.append(entry)
    return due
