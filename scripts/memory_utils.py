#!/usr/bin/env python3
"""Shared utilities for AI OS memory scripts."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from profile.schema import RESERVED_PROFILE_KEYS  # noqa: E402 (see boundary note below)

# memory/ is reserved for approval-gated *learned* memory (lessons, decisions,
# session artifacts). profile/ is reserved for canonical, explicitly-authored
# professional identity data (role, team, reporting relationships). A memory
# record must never carry these profile-only fields (Phase 9 REQ-001/REQ-005)
# — imported from scripts/profile/schema.py so the reserved-key list is
# defined exactly once, shared between both validators.

ALLOWED_TYPES = {"convention", "preference", "principle", "project", "session", "decision", "lesson"}
ALLOWED_SCOPES = {"global", "project", "session"}
ALLOWED_STATUS = {"active", "proposed", "archived", "superseded"}
ALLOWED_SENSITIVITY = {"public", "internal", "restricted"}
ALLOWED_RETENTION = {"permanent", "project", "temporary", "archive"}

REQUIRED_FIELDS = [
    "id",
    "title",
    "type",
    "scope",
    "project",
    "status",
    "created",
    "updated",
    "source",
    "summary",
    "tags",
    "related",
    "sensitivity",
    "retention",
    "contentPath",
]

TYPE_FOLDER = {
    "convention": "memory/permanent/conventions",
    "preference": "memory/permanent/preferences",
    "principle": "memory/permanent/principles",
    "project": "memory/projects",
    "session": "memory/sessions",
    "decision": "memory/decisions",
    "lesson": "memory/lessons",
}

SECRET_LIKE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|password|client[_-]?secret|connection\s*string|private\s*key)"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def today_iso() -> str:
    return date.today().isoformat()


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    value = re.sub(r"-+", "-", value)
    return value or "memory"


def generate_id(root: Path, record_type: str, title: str) -> str:
    base = f"{record_type}-{slugify(title)}"
    records = load_registry(root)["records"]
    known = {row["id"] for row in records}
    index = 1
    while True:
        candidate = f"{base}-{index:03d}"
        if candidate not in known:
            return candidate
        index += 1


def content_folder_for(record_type: str) -> str:
    if record_type not in TYPE_FOLDER:
        raise ValueError(f"unsupported memory type: {record_type}")
    return TYPE_FOLDER[record_type]


def infer_retention(record_type: str, scope: str) -> str:
    if scope == "session":
        return "temporary"
    if scope == "project" or record_type in {"project", "decision"}:
        return "project"
    return "permanent"


def ensure_safe_content_path(value: str) -> str:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError("contentPath must be a relative repository path")
    normalized = candidate.as_posix()
    if not normalized.startswith("memory/"):
        raise ValueError("contentPath must live under memory/")
    if ".." in candidate.parts:
        raise ValueError("contentPath cannot contain '..'")
    return normalized


def parse_scalar(raw: str):
    value = raw.strip()
    if value in {"null", "~"}:
        return None
    if value in {"[]", ""}:
        return [] if value == "[]" else ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def parse_front_matter(path: Path) -> Tuple[Dict[str, object], str]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text:
        raise ValueError(f"{path}: missing YAML front matter")
    block, body = text.split("\n---\n", 1)
    lines = block.splitlines()[1:]
    data: Dict[str, object] = {}
    current = None
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            item = line.strip()
            if current and isinstance(data.get(current), list) and item.startswith("- "):
                data[current].append(parse_scalar(item[2:]))
            continue
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        value = raw.strip()
        if value == "":
            data[key] = []
        else:
            data[key] = parse_scalar(value)
        current = key
    return data, body


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if re.fullmatch(r"[A-Za-z0-9._/-]+", text):
        return text
    escaped = text.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def render_front_matter(metadata: Dict[str, object]) -> str:
    lines = ["---"]
    for key in REQUIRED_FIELDS:
        value = metadata.get(key)
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_yaml_scalar(item)}")
            if not value:
                lines[-1] = f"{key}: []"
            continue
        lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def default_body(record_type: str, title: str, summary: str) -> str:
    lines = [f"# {title}", "", "## Summary", "", summary, "", "## Context", "", "", "## Details", "", "", "## Why It Matters", "", "", "## Related Projects", "", "", "## Related Decisions", "", "", "## Evidence or Source", "", "", "## Review Date", "", ""]
    if record_type == "session":
        lines.insert(2, "Session memory is temporary and should be promoted or archived when work is complete.")
        lines.insert(3, "")
        lines.extend(["## Current Goal", "", "", "## Findings", "", "", "## Files Examined", "", "", "## Work in Progress", "", "", "## Blockers", "", "", "## Next Action", "", ""])
    if record_type == "decision":
        lines = [
            f"# {title}",
            "",
            "## Summary",
            "",
            summary,
            "",
            "## Context",
            "",
            "",
            "## Decision",
            "",
            "",
            "## Reason",
            "",
            "",
            "## Alternatives Considered",
            "",
            "",
            "## Consequences",
            "",
            "",
            "## Why It Matters",
            "",
            "",
            "## Related Projects",
            "",
            "",
            "## Related Decisions",
            "",
            "",
            "## Evidence or Source",
            "",
            "",
            "## Review Date",
            "",
            "",
        ]
    if record_type == "lesson":
        lines = [
            f"# {title}",
            "",
            "## Summary",
            "",
            summary,
            "",
            "## Situation",
            "",
            "",
            "## Observation",
            "",
            "",
            "## Root Cause",
            "",
            "",
            "## Resolution",
            "",
            "",
            "## Reusable Lesson",
            "",
            "",
            "## Preventive Action",
            "",
            "",
            "## Why It Matters",
            "",
            "",
            "## Related Projects",
            "",
            "",
            "## Related Decisions",
            "",
            "",
            "## Evidence or Source",
            "",
            "",
            "## Review Date",
            "",
            "",
        ]
    return "\n".join(lines)


def load_registry(root: Path) -> Dict[str, object]:
    path = root / "memory" / "registry.json"
    if not path.is_file():
        return {"schemaVersion": "1.0.0", "records": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "records" not in data or not isinstance(data["records"], list):
        raise ValueError("memory/registry.json must contain a records array")
    return data


def save_registry(root: Path, data: Dict[str, object]) -> None:
    records = sorted(data.get("records", []), key=lambda item: item["id"])
    payload = {"schemaVersion": "1.0.0", "records": records}
    path = root / "memory" / "registry.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def registry_entry(metadata: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": metadata["id"],
        "title": metadata["title"],
        "type": metadata["type"],
        "scope": metadata["scope"],
        "project": metadata["project"],
        "status": metadata["status"],
        "path": metadata["contentPath"],
        "tags": list(metadata.get("tags", [])),
        "sensitivity": metadata["sensitivity"],
        "retention": metadata["retention"],
    }


def validate_metadata(metadata: Dict[str, object]) -> List[str]:
    errors: List[str] = []
    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
    if metadata.get("type") not in ALLOWED_TYPES:
        errors.append(f"invalid type: {metadata.get('type')}")
    if metadata.get("scope") not in ALLOWED_SCOPES:
        errors.append(f"invalid scope: {metadata.get('scope')}")
    if metadata.get("status") not in ALLOWED_STATUS:
        errors.append(f"invalid status: {metadata.get('status')}")
    if metadata.get("sensitivity") not in ALLOWED_SENSITIVITY:
        errors.append(f"invalid sensitivity: {metadata.get('sensitivity')}")
    if metadata.get("retention") not in ALLOWED_RETENTION:
        errors.append(f"invalid retention: {metadata.get('retention')}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(metadata.get("id", ""))):
        errors.append("id must be lowercase and hyphenated")
    for field in ("created", "updated"):
        value = str(metadata.get(field, ""))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            errors.append(f"{field} must be ISO date format YYYY-MM-DD")
    for field in ("tags", "related"):
        if not isinstance(metadata.get(field), list):
            errors.append(f"{field} must be a list")
    try:
        ensure_safe_content_path(str(metadata.get("contentPath", "")))
    except ValueError as exc:
        errors.append(str(exc))
    reserved_present = sorted(key for key in RESERVED_PROFILE_KEYS if key in metadata)
    if reserved_present:
        errors.append(
            "memory records must not store canonical profile data; move "
            f"reserved profile-only field(s) to profile/ instead: {', '.join(reserved_present)}"
        )
    return errors


def find_record(records: Iterable[Dict[str, object]], record_id: str):
    for row in records:
        if row.get("id") == record_id:
            return row
    return None


def likely_secret(text: str) -> bool:
    return bool(SECRET_LIKE.search(text))


def masked(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) <= 6:
        return "***"
    return trimmed[:3] + "***" + trimmed[-2:]
