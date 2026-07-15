"""Text extraction from source files for discovery indexing."""
from __future__ import annotations

import json
import re
from pathlib import Path

from repo_files import discoverable_files

from .utils import normalize_path, path_is_excluded


def discover_source_files(root: Path) -> list[Path]:
    """Discover indexable source files from the repository."""
    files: list[Path] = []
    for path in discoverable_files(root):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if path_is_excluded(rel):
            continue
        # Skip generated directory (derived artifacts)
        rel_posix = rel.as_posix()
        if rel_posix.startswith("generated/"):
            continue
        # Only index Markdown and JSON
        if path.suffix.lower() not in {".md", ".json"}:
            continue
        files.append(path)
    files.sort(key=lambda item: normalize_path(str(item.relative_to(root))))
    return files


def parse_front_matter(text: str) -> dict[str, object]:
    """Parse YAML-like front matter from Markdown text."""
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


def extract_title(text: str) -> str | None:
    """Extract the first H1 title from Markdown text."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return None


def extract_headings(text: str) -> list[str]:
    """Extract all headings from Markdown text."""
    headings = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            headings.append(match.group(2).strip())
    return headings


def extract_markdown_metadata(path: Path) -> dict:
    """Extract searchable metadata from a Markdown file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}

    front = parse_front_matter(text)
    body = text
    if text.replace("\r\n", "\n").startswith("---\n") and "\n---\n" in text.replace("\r\n", "\n"):
        body = text.replace("\r\n", "\n").split("\n---\n", 1)[1]

    title = extract_title(body) or str(front.get("title", "") or "")
    headings = extract_headings(body)

    # Build a concise snippet (first meaningful paragraph, max 200 chars)
    snippet = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith(">") and not stripped.startswith("---"):
            snippet = stripped[:200]
            break

    return {
        "title": title,
        "headings": headings,
        "frontMatter": front,
        "snippet": snippet,
    }


def extract_json_metadata(path: Path) -> dict:
    """Extract searchable metadata from a JSON file."""
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {"title": path.stem, "snippet": ""}

    # Extract useful fields from common JSON structures
    title = ""
    snippet = ""
    headings: list[str] = []

    if "name" in data:
        title = str(data["name"])
    elif "title" in data:
        title = str(data["title"])
    else:
        title = path.stem

    if "description" in data:
        snippet = str(data["description"])[:200]
    elif "summary" in data:
        snippet = str(data["summary"])[:200]

    # Extract keys as pseudo-headings for searchability
    if isinstance(data, dict):
        headings = [str(key) for key in list(data.keys())[:20]]

    return {
        "title": title,
        "headings": headings,
        "frontMatter": {},
        "snippet": snippet,
    }


def extract_file_metadata(path: Path, root: Path) -> dict:
    """Extract metadata from a source file based on its type."""
    rel = normalize_path(str(path.relative_to(root)))

    if path.suffix.lower() == ".md":
        meta = extract_markdown_metadata(path)
    elif path.suffix.lower() == ".json":
        meta = extract_json_metadata(path)
    else:
        meta = {"title": path.stem, "headings": [], "frontMatter": {}, "snippet": ""}

    meta["sourcePath"] = rel
    meta["extension"] = path.suffix.lower()

    # Infer document category
    if rel.startswith(".agent/skills/"):
        meta["category"] = "skill"
    elif rel.startswith("memory/"):
        meta["category"] = "memory"
    elif rel.startswith("templates/project-starters/"):
        meta["category"] = "project"
    elif rel.startswith("knowledge/"):
        meta["category"] = "knowledge"
    elif rel.startswith("scripts/"):
        meta["category"] = "script"
    elif rel.startswith("agents/"):
        meta["category"] = "agent"
    elif rel.startswith("prompts/"):
        meta["category"] = "prompt"
    elif rel.startswith("standards/"):
        meta["category"] = "standard"
    elif rel.startswith("references/"):
        meta["category"] = "reference"
    else:
        meta["category"] = "document"

    return meta
