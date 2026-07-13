#!/usr/bin/env python3
"""Check if dashboard artifacts are current (staleness check)."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dashboard.aggregate import build_dashboard_data
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


def main(argv=None) -> int:
    # Build current data
    try:
        current = build_dashboard_data(ROOT)
        failures, _warnings = validate_dashboard_data(current)
        if failures:
            raise DashboardError("build produced invalid data:\n" + "\n".join(failures))
    except DashboardError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    # Check data JSON staleness
    if not DATA_PATH.is_file():
        print("FAIL stale generated files: generated/dashboard-data.json", file=sys.stderr)
        return 1
    try:
        saved = load_dashboard_data(DATA_PATH)
    except DashboardError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    if not compare_data_ignoring_generated_at(current, saved):
        print("FAIL stale generated files: generated/dashboard-data.json", file=sys.stderr)
        return 1

    # Check HTML exists and is valid
    html_failures, _html_warnings = validate_dashboard_html(HTML_PATH)
    if html_failures:
        print(f"FAIL stale generated files: generated/dashboard.html", file=sys.stderr)
        return 1

    print("PASS dashboard is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
