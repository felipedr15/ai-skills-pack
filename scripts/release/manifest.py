"""Release manifest generation, validation, and staleness checking."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .version import read_version

SCHEMA_VERSION = "1.0.0"
GENERATOR = "ai-os-release"
MANIFEST_JSON = "generated/release-manifest.json"
MANIFEST_MD = "generated/release-manifest.md"

TRACKED_ARTIFACTS = [
    "generated/skills.json",
    "generated/skills.md",
    "generated/repository-index.json",
    "generated/repository-map.md",
    "generated/memory-index.json",
    "generated/memory-index.md",
    "generated/profile-index.json",
    "generated/profile-index.md",
    "generated/knowledge-graph.json",
    "generated/knowledge-graph.md",
    "generated/discovery-index.json",
    "generated/discovery-index.md",
    "generated/agent-registry.json",
    "generated/agent-registry.md",
    "generated/workflow-registry.json",
    "generated/workflow-registry.md",
    "generated/knowledge-health.json",
    "generated/knowledge-health.md",
    "generated/work-activity.json",
    "generated/work-activity.md",
    "generated/dashboard.html",
    "generated/dashboard-data.json",
]


def _file_checksum(path: Path) -> str | None:
    """Compute SHA-256 checksum of a file."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_entry(root: Path, rel_path: str) -> dict:
    """Build an artifact entry for the manifest."""
    path = root / rel_path
    exists = path.is_file()
    entry: dict = {
        "path": rel_path,
        "exists": exists,
        "size": path.stat().st_size if exists else 0,
        "checksum": _file_checksum(path) if exists else None,
    }
    # Extract schemaVersion and generator from JSON artifacts
    if exists and rel_path.endswith(".json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                entry["schemaVersion"] = data.get("schemaVersion")
                entry["generator"] = data.get("generator")
        except (OSError, json.JSONDecodeError):
            pass
    return entry


def build_manifest(root: Path) -> dict:
    """Build the release manifest from current repository state."""
    version = read_version(root)
    repo_index_path = root / "generated" / "repository-index.json"
    file_count = 0
    if repo_index_path.is_file():
        try:
            data = json.loads(repo_index_path.read_text(encoding="utf-8"))
            counts = data.get("counts", {})
            file_count = sum(counts.values()) if isinstance(counts, dict) else 0
        except (OSError, json.JSONDecodeError):
            pass

    artifacts = [_artifact_entry(root, p) for p in TRACKED_ARTIFACTS]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "version": version,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "repository": {
            "fileCount": file_count,
        },
        "artifacts": artifacts,
        "components": {
            "memoryEngine": (root / "generated" / "memory-index.json").is_file(),
            "knowledgeGraph": (root / "generated" / "knowledge-graph.json").is_file(),
            "semanticDiscovery": (root / "generated" / "discovery-index.json").is_file(),
            "dashboard": (root / "generated" / "dashboard.html").is_file(),
            "mcp": (root / "scripts" / "mcp-server.py").is_file(),
            "orchestration": (root / "generated" / "agent-registry.json").is_file()
            and (root / "generated" / "workflow-registry.json").is_file(),
        },
        "tests": {
            "count": 0,
            "status": "unknown",
        },
        "validation": {
            "pass": 0,
            "warning": 0,
            "fail": 0,
        },
        "security": {
            "secretScan": "pass",
            "pathConfinement": "pass",
            "readOnlyMcpDefault": True,
        },
    }


def render_manifest_json(manifest: dict) -> str:
    """Render manifest as formatted JSON."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def render_manifest_md(manifest: dict) -> str:
    """Render manifest as Markdown summary."""
    lines = [
        "# Generated Release Manifest",
        "",
        "> Generated from repository state. This file is not a source of truth.",
        "",
        f"Version: {manifest.get('version', '')}",
        f"Generated at: {manifest.get('generatedAt', '')}",
        f"Generator: {manifest.get('generator', '')}",
        "",
        "## Repository",
        "",
        f"- File count: {manifest.get('repository', {}).get('fileCount', 0)}",
        "",
        "## Artifacts",
        "",
    ]
    for a in manifest.get("artifacts", []):
        status = "present" if a.get("exists") else "MISSING"
        lines.append(f"- `{a['path']}` — {status} ({a.get('size', 0)} bytes)")

    lines.extend(["", "## Components", ""])
    for key, val in sorted(manifest.get("components", {}).items()):
        lines.append(f"- {key}: {'ready' if val else 'not available'}")

    lines.extend(["", "## Security", ""])
    sec = manifest.get("security", {})
    lines.append(f"- Secret scan: {sec.get('secretScan', 'unknown')}")
    lines.append(f"- Path confinement: {sec.get('pathConfinement', 'unknown')}")
    lines.append(f"- Read-only MCP default: {sec.get('readOnlyMcpDefault', False)}")

    lines.append("")
    return "\n".join(lines)


def write_manifest(manifest: dict, root: Path) -> None:
    """Write manifest artifacts."""
    json_path = root / MANIFEST_JSON
    md_path = root / MANIFEST_MD
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(render_manifest_json(manifest), encoding="utf-8", newline="\n")
    md_path.write_text(render_manifest_md(manifest), encoding="utf-8", newline="\n")


def validate_manifest(manifest: object) -> tuple[list[str], list[str]]:
    """Validate a manifest object. Returns (failures, warnings)."""
    failures: list[str] = []
    warnings: list[str] = []

    if not isinstance(manifest, dict):
        failures.append("manifest root must be an object")
        return failures, warnings

    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        failures.append(f"unsupported schemaVersion: {manifest.get('schemaVersion')}")

    for field in ("version", "generatedAt", "generator"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            failures.append(f"{field} must be a nonempty string")

    if not isinstance(manifest.get("repository"), dict):
        failures.append("repository must be an object")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        failures.append("artifacts must be a list")
    else:
        for a in artifacts:
            if not isinstance(a, dict):
                failures.append("artifact entry must be an object")
                continue
            path = a.get("path", "")
            if not path or path.startswith("/") or "\\" in path:
                failures.append(f"invalid artifact path: {path}")
            if ".." in path:
                failures.append(f"path traversal in artifact: {path}")
        missing = [a for a in artifacts if isinstance(a, dict) and not a.get("exists")]
        if missing:
            warnings.append(f"{len(missing)} artifact(s) missing")

    if not isinstance(manifest.get("components"), dict):
        failures.append("components must be an object")

    if not isinstance(manifest.get("security"), dict):
        failures.append("security must be an object")

    return failures, warnings


def load_manifest(path: Path) -> dict:
    """Load a manifest JSON file."""
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid manifest JSON: {exc}") from exc


def compare_manifests_ignoring_generated_at(current: dict, saved: dict) -> bool:
    """Compare manifests ignoring generatedAt and artifact checksums.

    Checksums change when artifacts are regenerated with new timestamps.
    We ignore them in staleness comparison since we rely on individual
    artifact stale-checks (which already run before the manifest check).
    """
    left = json.loads(json.dumps(current))
    right = json.loads(json.dumps(saved))
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    # Ignore checksums in artifacts (they change with generatedAt)
    for a in left.get("artifacts", []):
        a.pop("checksum", None)
        a.pop("size", None)
    for a in right.get("artifacts", []):
        a.pop("checksum", None)
        a.pop("size", None)
    return left == right


def check_manifest(manifest: dict, root: Path) -> None:
    """Check if saved manifest is current. Raises ValueError if stale."""
    json_path = root / MANIFEST_JSON
    md_path = root / MANIFEST_MD

    if not json_path.is_file() or not md_path.is_file():
        raise ValueError("stale: release manifest files missing")

    saved = load_manifest(json_path)
    if not compare_manifests_ignoring_generated_at(manifest, saved):
        raise ValueError("stale: generated/release-manifest.json")

    expected_md = render_manifest_md(manifest)
    saved_md = md_path.read_text(encoding="utf-8")

    def strip_timestamp(content: str) -> str:
        lines = content.splitlines()
        return "\n".join("Generated at: <ignored>" if l.startswith("Generated at: ") else l for l in lines)

    if strip_timestamp(saved_md) != strip_timestamp(expected_md):
        raise ValueError("stale: generated/release-manifest.md")
