#!/usr/bin/env python3
"""Validate existing dashboard artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dashboard.validate import DashboardError, load_dashboard_data, validate_dashboard_data, validate_dashboard_html

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "generated" / "dashboard-data.json"
HTML_PATH = ROOT / "generated" / "dashboard.html"


def main(argv=None) -> int:
    failures: list[str] = []
    warnings: list[str] = []

    # Validate dashboard-data.json
    if not DATA_PATH.is_file():
        print("FAIL generated/dashboard-data.json is missing; run scripts/dashboard-build.py", file=sys.stderr)
        return 1
    try:
        data = load_dashboard_data(DATA_PATH)
    except DashboardError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    data_failures, data_warnings = validate_dashboard_data(data)
    failures.extend(data_failures)
    warnings.extend(data_warnings)

    # Validate dashboard.html
    html_failures, html_warnings = validate_dashboard_html(HTML_PATH)
    failures.extend(html_failures)
    warnings.extend(html_warnings)

    for item in warnings:
        print(f"WARNING {item}")
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1

    print("PASS dashboard validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
