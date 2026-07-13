"""Discovery index build and staleness checking."""
from __future__ import annotations

import json
from pathlib import Path

from .index import build_discovery_index
from .render import render_json, render_markdown
from .validate import compare_indexes_ignoring_generated_at, load_discovery_index, DiscoveryError


def build(root: Path) -> dict:
    """Build the discovery index and validate it."""
    from .validate import validate_index_object
    index = build_discovery_index(root)
    failures, _warnings = validate_index_object(index)
    if failures:
        raise DiscoveryError("build produced invalid index:\n" + "\n".join(failures))
    return index


def write_index(index: dict, root: Path) -> None:
    """Write discovery index artifacts to generated/."""
    out_json = root / "generated" / "discovery-index.json"
    out_md = root / "generated" / "discovery-index.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(render_json(index), encoding="utf-8", newline="\n")
    out_md.write_text(render_markdown(index), encoding="utf-8", newline="\n")


def check_index(index: dict, root: Path) -> None:
    """Check if generated discovery artifacts are current."""
    out_json = root / "generated" / "discovery-index.json"
    out_md = root / "generated" / "discovery-index.md"

    if not out_json.is_file() or not out_md.is_file():
        raise DiscoveryError("stale generated files: generated/discovery-index.json, generated/discovery-index.md")

    try:
        saved = load_discovery_index(out_json)
    except DiscoveryError as exc:
        raise DiscoveryError(str(exc)) from exc

    if not compare_indexes_ignoring_generated_at(index, saved):
        raise DiscoveryError("stale generated files: generated/discovery-index.json")

    expected_md = render_markdown(index)
    try:
        saved_md = out_md.read_text(encoding="utf-8")
    except OSError as exc:
        raise DiscoveryError(f"unable to read generated files: {exc}") from exc

    # Compare markdown ignoring timestamps
    def normalize_timestamp(content: str) -> str:
        lines = content.splitlines()
        result: list[str] = []
        for line in lines:
            if line.startswith("Generated at: "):
                result.append("Generated at: <ignored>")
            else:
                result.append(line)
        return "\n".join(result)

    if normalize_timestamp(saved_md) != normalize_timestamp(expected_md):
        raise DiscoveryError("stale generated files: generated/discovery-index.md")
