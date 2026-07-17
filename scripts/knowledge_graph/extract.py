from __future__ import annotations

import json
import re
from pathlib import Path

from repo_files import discoverable_files

from .utils import markdown_links, normalize_relpath, parse_front_matter, path_is_excluded, slug, wiki_links

PLATFORMS = {
    "chatgpt",
    "claude",
    "copilot",
    "kiro",
    "codex",
    "vercel",
    "canva",
    "github",
    "vscode",
    "power apps",
    "power automate",
    "sharepoint",
}

TOOLS = {
    "git",
    "python",
    "node",
    "mcp",
    "powershell",
    "unittest",
    "pytest",
    "docker",
}

CONCEPTS = {
    "knowledge graph",
    "memory engine",
    "validation",
    "security",
    "workflow",
    "architecture",
    "specification",
    "automation",
}


def classify_document(path: str) -> str:
    if path.startswith(".agent/skills/") and path.endswith("/SKILL.md"):
        return "skill"
    if path.startswith("memory/") and path.endswith(".md") and not path.lower().endswith("readme.md"):
        return "memory"
    if path.startswith("profile/") and path.endswith(".md") and not path.lower().endswith("readme.md"):
        return "profile"
    if path.startswith("templates/project-starters/"):
        return "project"
    return "document"


def discover_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in discoverable_files(root):
        if not path.is_file() or path_is_excluded(path.relative_to(root)):
            continue
        rel = normalize_relpath(path, root)
        if rel.startswith("generated/"):
            if rel not in {
                "generated/skills.json", "generated/repository-index.json", "generated/memory-index.json",
                "generated/profile-index.json", "generated/work-activity.json",
            }:
                continue
        # Snapshots are dated historical checkpoints, never current professional
        # truth (design.md Security) -- excluded from indexing entirely rather
        # than risk a stale snapshot outranking or duplicating the curated
        # knowledge/professional-context/overview.md it was taken from.
        if rel.startswith("knowledge/professional-context/snapshots/"):
            continue
        if path.suffix.lower() not in {".md", ".json"}:
            continue
        files.append(path)
    files.sort(key=lambda item: normalize_relpath(item, root))
    return files


def load_active_profile_ids(root: Path) -> set[str]:
    """Cross-reference profile/registry.json for which profile id(s) are
    currently active, without ingesting any profile front-matter content.
    An absent or empty registry is a valid state -> empty set, never a
    failure (mirrors scripts/profile/registry.py's own not-yet-configured
    handling).
    """
    from profile import registry as profile_registry

    try:
        data = profile_registry.load_registry(root)
    except (OSError, ValueError):
        return set()
    return {
        entry.get("id")
        for entry in data.get("profiles", [])
        if isinstance(entry, dict) and entry.get("active") is True and entry.get("id")
    }


def extract_mentions(text: str, values: set[str]) -> list[str]:
    lowered = text.lower()
    found = [item for item in sorted(values) if item in lowered]
    return found


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_markdown_metadata(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    front = parse_front_matter(text)
    body = text
    if text.startswith("---\n") and "\n---\n" in text:
        body = text.split("\n---\n", 1)[1]
    return front, body


def display_name_from_path(path: str) -> str:
    stem = Path(path).stem
    value = stem.replace("-", " ").replace("_", " ").strip()
    if not value:
        return path
    return value.title()


def resolve_markdown_target(source: Path, target: str, root: Path) -> str | None:
    clean = target.split("#", 1)[0].replace("%20", " ").strip()
    if not clean:
        return None
    candidate = (source.parent / clean).resolve()
    try:
        rel = candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    if not candidate.exists() or ".." in Path(rel).parts:
        return None
    return rel


def canonical_wiki_key(name: str) -> str:
    return slug(name)


def extract_explicit_skill_dependencies(front_matter: dict[str, object]) -> list[str]:
    dependencies = front_matter.get("dependencies", [])
    if isinstance(dependencies, list):
        return [str(item) for item in dependencies]
    if isinstance(dependencies, str) and dependencies.strip():
        return [dependencies.strip()]
    return []


def extract_memory_relationships(front_matter: dict[str, object]) -> tuple[list[str], str | None]:
    related = front_matter.get("related", [])
    if not isinstance(related, list):
        related = []
    project = front_matter.get("project")
    if isinstance(project, str) and project.strip():
        return [str(item) for item in related], project.strip()
    return [str(item) for item in related], None


def looks_like_project_directory(path: str) -> bool:
    return path.startswith("templates/project-starters/") and path.count("/") >= 2


def project_name_from_path(path: str) -> str | None:
    if not looks_like_project_directory(path):
        return None
    return path.split("/")[2]


def extract_header_references(text: str) -> list[str]:
    return re.findall(r"^#+\s+(.+)$", text, flags=re.MULTILINE)
