#!/usr/bin/env python3
"""Build the AI OS dashboard artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dashboard.aggregate import build_dashboard_data
from dashboard.render import write_dashboard
from dashboard.validate import (
    DashboardError,
    compare_data_ignoring_generated_at,
    load_dashboard_data,
    validate_dashboard_data,
    validate_dashboard_html,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "generated" / "dashboard-data.json"
HTML_PATH = ROOT / "generated" / "dashboard.html"


def _is_current(data: dict) -> bool:
    """Check whether the committed dashboard artifacts already match `data`.

    Ignores only the documented volatile fields (generatedAt and, for
    legacy artifacts, fileTimestamp) via compare_data_ignoring_generated_at.
    """
    if not DATA_PATH.is_file():
        return False
    try:
        saved = load_dashboard_data(DATA_PATH)
    except DashboardError:
        return False
    if not compare_data_ignoring_generated_at(data, saved):
        return False
    html_failures, _html_warnings = validate_dashboard_html(HTML_PATH)
    return not html_failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check only, do not write")
    args = parser.parse_args(argv)

    try:
        data = build_dashboard_data(ROOT)
        failures, _warnings = validate_dashboard_data(data)
        if failures:
            raise DashboardError("build produced invalid data:\n" + "\n".join(failures))
    except DashboardError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    if args.check:
        if _is_current(data):
            print("PASS dashboard is current")
            return 0
        print("FAIL stale generated files: generated/dashboard-data.json or generated/dashboard.html", file=sys.stderr)
        return 1

    stats = data.get("repository", {})
    kg = data.get("knowledgeGraph", {})
    if _is_current(data):
        print(
            f"PASS dashboard unchanged "
            f"({stats.get('totalFiles', 0)} files, "
            f"{kg.get('totalNodes', 0)} nodes, "
            f"{kg.get('totalEdges', 0)} edges)"
        )
        return 0

    write_dashboard(data, ROOT)
    print(
        f"PASS dashboard built "
        f"({stats.get('totalFiles', 0)} files, "
        f"{kg.get('totalNodes', 0)} nodes, "
        f"{kg.get('totalEdges', 0)} edges)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
