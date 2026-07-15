"""Shared helpers for the orchestration package."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def ensure_scripts_path() -> None:
    """Put scripts/ on sys.path so sibling packages (ai_os_service, etc.) import cleanly."""
    scripts_dir = str(Path(__file__).resolve().parents[1])
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def now_iso() -> str:
    """Current UTC timestamp in ISO format (matches release/utils.now_iso)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str, max_len: int = 40) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    text = re.sub(r"-+", "-", text)
    text = text[:max_len].strip("-")
    return text or "item"


def next_sequential_id(existing_ids, prefix: str, seed: str) -> str:
    """Generate a deterministic, collision-free id: '<prefix>-<slug>-NNN'.

    No wall-clock or random component in the id itself, so ids are stable
    and reproducible given the same existing-id set and seed text.
    """
    base = f"{prefix}-{slug(seed)}"
    known = set(existing_ids)
    index = 1
    while True:
        candidate = f"{base}-{index:03d}"
        if candidate not in known:
            return candidate
        index += 1


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def runtime_dir(root: Path, *parts: str) -> Path:
    """Path under the git-ignored local runtime directory (.ai-os/...)."""
    path = root / ".ai-os"
    for part in parts:
        path = path / part
    return path


def atomic_write_json(path: Path, data: object) -> None:
    """Write JSON atomically (temp file + os.replace) to avoid partial writes."""
    ensure_dir(path.parent)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def load_json(path: Path, default=None):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def bounded_list(items: list, max_items: int):
    """Truncate a list to max_items. Returns (items, truncated: bool)."""
    if len(items) <= max_items:
        return list(items), False
    return list(items[:max_items]), True


def sanitize_text(text: str, max_chars: int) -> str:
    """Strip control characters and cap length for free-text local storage."""
    if text is None:
        return ""
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ch >= " ")
    cleaned = cleaned.strip()
    return cleaned[:max_chars]


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def content_hash(text: str, length: int = 8) -> str:
    """Deterministic short hash of text content (no randomness, no clock)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]
