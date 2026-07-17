"""Shared helper for scoping generator file discovery to repository content.

The knowledge-graph and semantic-discovery generators used to walk the
entire repository root (`root.rglob("*")`) and exclude only a short list
of hardcoded directory names (`.git`, `node_modules`, `.venv`, ...). That
denylist only recognizes specific directory *names*, not "this is actually
part of the repository" -- so any untracked local directory (IDE settings,
scratch folders, temp exports, however named) containing a .md/.json file
was silently indexed.

This module scopes discovery to files git actually tracks, which is the
one signal that reliably distinguishes intentional repository content from
local/untracked clutter regardless of what it is named. When git is
unavailable (no git binary, no .git directory, not a working tree -- e.g.
a released package), it falls back to a deterministic directory/suffix
allowlist instead of an unscoped walk.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# Used only when `git ls-files` cannot run. Mirrors the directories/root
# files the generators are meant to index; kept in sync by hand since
# there is no git to ask in this mode.
FALLBACK_ALLOWED_PREFIXES = (
    ".agent/skills/",
    "agents/",
    "config/",
    "docs/",
    "examples/",
    "generated/",
    "knowledge/",
    "memory/",
    "profile/",
    "prompts/",
    "references/",
    "scripts/",
    "standards/",
    "templates/",
    "tests/",
)

FALLBACK_ROOT_SUFFIXES = {".md", ".json", ".yml", ".yaml"}


def git_tracked_files(root: Path) -> list[str] | None:
    """Return posix-relative paths of files git tracks under root.

    Returns None (rather than raising) if the git binary is missing, the
    call errors, or root is not inside a git working tree, so callers can
    fall back to a safe deterministic allowlist.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.decode("utf-8", errors="replace")
    return [item for item in raw.split("\0") if item]


def fallback_allowed(rel_posix: str) -> bool:
    """Deterministic allowlist used only when git tracking is unavailable."""
    if any(rel_posix.startswith(prefix) for prefix in FALLBACK_ALLOWED_PREFIXES):
        return True
    if "/" not in rel_posix and Path(rel_posix).suffix.lower() in FALLBACK_ROOT_SUFFIXES:
        return True
    return False


def discoverable_files(root: Path) -> list[Path]:
    """Return candidate file paths for indexing, scoped to repository content.

    Prefers git-tracked files. Falls back to a fixed allowlist of
    supported directories/root files when git tracking information is
    unavailable, so arbitrary untracked root directories are never
    indexed either way.
    """
    tracked = git_tracked_files(root)
    if tracked is not None:
        return [root / rel for rel in tracked]
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and fallback_allowed(path.relative_to(root).as_posix())
    ]
