"""Security permissions and path confinement for the AI OS service layer."""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from .errors import Forbidden, PathRejected

BLOCKED_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".tox", "coverage", "dist", "build",
}

BLOCKED_SUFFIXES = {".pem", ".key", ".pfx", ".p12"}

BLOCKED_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "secrets.json", "private.json", "credentials.json",
}

ALLOWED_TEXT_EXTENSIONS = {
    ".md", ".json", ".yml", ".yaml", ".txt", ".py", ".ps1",
    ".sh", ".bat", ".cmd", ".toml", ".cfg", ".ini", ".html",
}

SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|password|client[_-]?secret|"
    r"private[_-]?key|connection[_-]?string)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{16,}"
)


def normalize_path(path: str) -> str:
    """Normalize path to forward slashes."""
    return path.replace("\\", "/")


def _is_under_skills(parts: tuple) -> bool:
    return len(parts) >= 2 and parts[0] == ".agent" and parts[1] == "skills"


def validate_path(path: str, root: Path) -> Path:
    """Validate and resolve a repository-relative path.

    Raises PathRejected if the path is unsafe.
    Returns the resolved absolute path.
    """
    if not path or not path.strip():
        raise PathRejected("empty path")

    normalized = normalize_path(path.strip())

    # Reject absolute paths
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        raise PathRejected("absolute paths are not allowed", {"path": normalized})

    # Reject traversal
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        raise PathRejected("path traversal is not allowed", {"path": normalized})

    # Reject blocked directories. `.agent/skills/` is explicitly-tracked
    # source content whose taxonomy uses category directory names (e.g.
    # "build") that can collide with BLOCKED_DIRS' generic build-artifact
    # directory names -- skill content must never be blocked on that basis.
    if not _is_under_skills(parts):
        for part in parts:
            if part.lower() in BLOCKED_DIRS:
                raise PathRejected(f"access to '{part}' is blocked", {"path": normalized})

    # Reject blocked file names
    filename = PurePosixPath(normalized).name.lower()
    if filename in BLOCKED_NAMES or filename.startswith(".env"):
        raise PathRejected(f"access to '{filename}' is blocked", {"path": normalized})

    # Reject blocked suffixes
    suffix = PurePosixPath(normalized).suffix.lower()
    if suffix in BLOCKED_SUFFIXES:
        raise PathRejected(f"access to '{suffix}' files is blocked", {"path": normalized})

    # Resolve and confirm within root
    resolved = (root / normalized).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise PathRejected("path escapes repository root", {"path": normalized})

    return resolved


def is_text_file(path: str) -> bool:
    """Check if a file has an allowed text extension."""
    suffix = PurePosixPath(path).suffix.lower()
    return suffix in ALLOWED_TEXT_EXTENSIONS


def is_secret_like(path: str) -> bool:
    """Check if a path looks like it might contain secrets."""
    normalized = normalize_path(path)
    parts = PurePosixPath(normalized).parts
    filename = PurePosixPath(normalized).name.lower()
    suffix = PurePosixPath(normalized).suffix.lower()

    if filename in BLOCKED_NAMES or filename.startswith(".env"):
        return True
    if suffix in BLOCKED_SUFFIXES:
        return True
    if not _is_under_skills(parts):
        for part in parts:
            if part.lower() in BLOCKED_DIRS:
                return True
    return False


def redact_sensitive_content(text: str) -> str:
    """Redact potential secrets from text content."""
    return SECRET_PATTERN.sub("[REDACTED]", text)
