#!/usr/bin/env python3
"""Build or check the AI OS workflow registry (Phase 8, Part 2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orchestration.workflow import (
    build_workflow_registry,
    compare_registries_ignoring_generated_at,
    validate_workflow_registry,
)
from orchestration.render import render_json, render_workflow_registry_md

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "generated" / "workflow-registry.json"
OUT_MD = ROOT / "generated" / "workflow-registry.md"


class RegistryBuildError(ValueError):
    pass


def _normalize_markdown_timestamp(content: str) -> str:
    lines = content.splitlines()
    return "\n".join(
        "Generated at: <ignored>" if line.startswith("Generated at: ") else line
        for line in lines
    )


def build() -> dict:
    registry = build_workflow_registry(ROOT)
    failures, _warnings = validate_workflow_registry(registry)
    if failures:
        raise RegistryBuildError("\n".join(failures))
    return registry


def write_registry(registry: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(render_json(registry), encoding="utf-8", newline="\n")
    OUT_MD.write_text(render_workflow_registry_md(registry), encoding="utf-8", newline="\n")


def check_registry(registry: dict) -> None:
    if not OUT_JSON.is_file() or not OUT_MD.is_file():
        raise RegistryBuildError("stale generated files: generated/workflow-registry.json, generated/workflow-registry.md")

    saved = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if not compare_registries_ignoring_generated_at(registry, saved):
        raise RegistryBuildError("stale generated files: generated/workflow-registry.json")

    expected_md = render_workflow_registry_md(registry)
    saved_md = OUT_MD.read_text(encoding="utf-8")
    if _normalize_markdown_timestamp(saved_md) != _normalize_markdown_timestamp(expected_md):
        raise RegistryBuildError("stale generated files: generated/workflow-registry.md")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated registry files are stale")
    args = parser.parse_args(argv)

    try:
        registry = build()
        if args.check:
            check_registry(registry)
            print(f"PASS workflow registry is current ({registry['stats']['totalWorkflows']} workflows)")
            return 0
        write_registry(registry)
        print(f"PASS workflow registry generated ({registry['stats']['totalWorkflows']} workflows)")
        return 0
    except RegistryBuildError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
