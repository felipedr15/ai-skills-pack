"""Version management for AI OS."""
from __future__ import annotations

import re
from pathlib import Path

_VERSION_FILE = "VERSION"
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")


def get_repo_root() -> Path:
    """Get the repository root (parent of scripts/)."""
    return Path(__file__).resolve().parents[2]


def read_version(root: Path | None = None) -> str:
    """Read the canonical version from VERSION file."""
    if root is None:
        root = get_repo_root()
    version_path = root / _VERSION_FILE
    if not version_path.is_file():
        raise FileNotFoundError(f"VERSION file not found at {version_path}")
    return version_path.read_text(encoding="utf-8").strip()


def is_valid_semver(version: str) -> bool:
    """Check if a version string is valid semantic versioning."""
    return bool(_SEMVER_RE.match(version))


def parse_version(version: str) -> tuple[int, int, int, str]:
    """Parse a semver string into (major, minor, patch, prerelease)."""
    if not is_valid_semver(version):
        raise ValueError(f"invalid semver: {version}")
    pre = ""
    if "-" in version:
        version, pre = version.split("-", 1)
    parts = version.split(".")
    return int(parts[0]), int(parts[1]), int(parts[2]), pre
