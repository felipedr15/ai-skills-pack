"""Shared utilities for semantic discovery."""
from __future__ import annotations

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
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
}

SECRET_LIKE_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".env",
}

SECRET_LIKE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "secrets.json",
    "private.json",
}

# Technical terms that should be preserved during tokenization
PRESERVED_TERMS = {
    "github",
    "powershell",
    "json",
    "yaml",
    "api",
    "mcp",
    "chatgpt",
    "claude",
    "copilot",
    "vercel",
    "canva",
    "kiro",
    "codex",
    "vscode",
}


def normalize_path(path: str) -> str:
    """Normalize a path to forward slashes."""
    return path.replace("\\", "/")


def safe_source_path(value: str) -> bool:
    """Return True if path is safe (relative, no backslashes, no traversal)."""
    if not value:
        return False
    if value.startswith("/"):
        return False
    if "\\" in value:
        return False
    parts = Path(value).parts
    if any(part == ".." for part in parts):
        return False
    return True


def path_is_excluded(path: Path) -> bool:
    """Return True if path should be excluded from indexing."""
    lowered = {part.lower() for part in path.parts}
    if any(item.lower() in lowered for item in SKIP_DIRS):
        return True
    suffix = path.suffix.lower()
    if suffix in SECRET_LIKE_SUFFIXES:
        return True
    name = path.name.lower()
    if name in SECRET_LIKE_NAMES or name.startswith(".env"):
        return True
    return False


def is_secret_like_path(path: str) -> bool:
    """Return True if the path looks like it might contain secrets."""
    p = Path(path)
    if p.suffix.lower() in SECRET_LIKE_SUFFIXES:
        return True
    if p.name.lower() in SECRET_LIKE_NAMES or p.name.lower().startswith(".env"):
        return True
    return False


def slug(value: str) -> str:
    """Create a URL-safe slug from a string."""
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    text = re.sub(r"-+", "-", text)
    return text or "item"


def stable_doc_id(source_path: str) -> str:
    """Create a stable document ID from a source path."""
    return f"doc:{normalize_path(source_path)}"


def stable_entity_id(node_id: str) -> str:
    """Create a stable entity ID from a graph node ID."""
    return f"entity:{node_id}"
