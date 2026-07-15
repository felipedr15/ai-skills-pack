#!/usr/bin/env python3
"""Build or check the AI OS knowledge-health report (Phase 8, Part 9).

This generates the deterministic, repo-only view (no local `.ai-os/`
session/feedback signal — see orchestration/knowledge_gaps.py for why).
Use `ai-os.py knowledge-health` / `knowledge-gaps` for the live view that
includes those signals.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orchestration.knowledge_gaps import (
    build_knowledge_health,
    compare_reports_ignoring_generated_at,
    validate_knowledge_health,
)
from orchestration.render import render_json, render_knowledge_health_md

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "generated" / "knowledge-health.json"
OUT_MD = ROOT / "generated" / "knowledge-health.md"


class HealthBuildError(ValueError):
    pass


def _normalize_markdown_timestamp(content: str) -> str:
    lines = content.splitlines()
    return "\n".join(
        "Generated at: <ignored>" if line.startswith("Generated at: ") else line
        for line in lines
    )


def build() -> dict:
    report = build_knowledge_health(ROOT, include_live=False)
    failures, _warnings = validate_knowledge_health(report)
    if failures:
        raise HealthBuildError("\n".join(failures))
    return report


def write_report(report: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(render_json(report), encoding="utf-8", newline="\n")
    OUT_MD.write_text(render_knowledge_health_md(report), encoding="utf-8", newline="\n")


def check_report(report: dict) -> None:
    if not OUT_JSON.is_file() or not OUT_MD.is_file():
        raise HealthBuildError("stale generated files: generated/knowledge-health.json, generated/knowledge-health.md")

    saved = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    if not compare_reports_ignoring_generated_at(report, saved):
        raise HealthBuildError("stale generated files: generated/knowledge-health.json")

    expected_md = render_knowledge_health_md(report)
    saved_md = OUT_MD.read_text(encoding="utf-8")
    if _normalize_markdown_timestamp(saved_md) != _normalize_markdown_timestamp(expected_md):
        raise HealthBuildError("stale generated files: generated/knowledge-health.md")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated report files are stale")
    args = parser.parse_args(argv)

    try:
        report = build()
        if args.check:
            check_report(report)
            print(f"PASS knowledge health is current (score {report['overallScore']}/100)")
            return 0
        write_report(report)
        print(f"PASS knowledge health generated (score {report['overallScore']}/100)")
        return 0
    except HealthBuildError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
