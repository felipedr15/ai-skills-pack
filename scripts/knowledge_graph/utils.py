from __future__ import annotations

import hashlib
import re
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".vscode",
    ".idea",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
}

SECRET_LIKE_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".env",
}


def normalize_relpath(path: Path, root: Path) -> str:
    value = path.resolve().relative_to(root.resolve()).as_posix()
    return value


def safe_source_path(value: str) -> bool:
    if value.startswith("/"):
        return False
    if "\\" in value:
        return False
    parts = Path(value).parts
    if any(part == ".." for part in parts):
        return False
    return True


def slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    text = re.sub(r"-+", "-", text)
    return text or "item"


def node_id(node_type: str, key: str) -> str:
    return f"{node_type}:{key}"


def edge_id(edge_type: str, source: str, target: str, extra: str = "") -> str:
    raw = f"{edge_type}|{source}|{target}|{extra}".encode("utf-8")
    digest = hashlib.sha1(raw).hexdigest()[:16]
    return f"edge:{digest}"


def path_is_excluded(path: Path) -> bool:
    parts = path.parts
    # `.agent/skills/` is explicitly-tracked source content whose taxonomy
    # uses category directory names (e.g. "build") that can collide with
    # SKIP_DIRS' generic build-artifact-directory names below. Skill content
    # must never be excluded on that basis.
    under_skills = len(parts) >= 2 and parts[0] == ".agent" and parts[1] == "skills"
    if not under_skills:
        lowered = {part.lower() for part in parts}
        if any(item.lower() in lowered for item in SKIP_DIRS):
            return True
    suffix = path.suffix.lower()
    if suffix in SECRET_LIKE_SUFFIXES:
        return True
    name = path.name.lower()
    if name.startswith(".env"):
        return True
    return False


def markdown_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]*\]\((?!https?://|mailto:|#)([^)]+)\)", text)


def wiki_links(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]]+)\]\]", text)


def parse_front_matter(text: str) -> dict[str, object]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n") or "\n---\n" not in normalized:
        return {}
    block = normalized.split("\n---\n", 1)[0].splitlines()[1:]
    data: dict[str, object] = {}
    current = None
    for line in block:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            item = line.strip()
            if current and isinstance(data.get(current), list) and item.startswith("- "):
                data[current].append(item[2:].strip().strip('"').strip("'"))
            continue
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        value = raw.strip()
        if value == "":
            data[key] = []
        elif value in {"null", "~"}:
            data[key] = None
        elif value == "[]":
            data[key] = []
        else:
            data[key] = value.strip('"').strip("'")
        current = key
    return data
