#!/usr/bin/env python3
"""Build the AI OS dashboard artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dashboard.aggregate import build_dashboard_data
from dashboard.render import write_dashboard
from dashboard.validate import DashboardError, validate_dashboard_data

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    try:
        data = build_dashboard_data(ROOT)
        failures, _warnings = validate_dashboard_data(data)
        if failures:
            raise DashboardError("build produced invalid data:\n" + "\n".join(failures))
        write_dashboard(data, ROOT)
        stats = data.get("repository", {})
        kg = data.get("knowledgeGraph", {})
        print(
            f"PASS dashboard built "
            f"({stats.get('totalFiles', 0)} files, "
            f"{kg.get('totalNodes', 0)} nodes, "
            f"{kg.get('totalEdges', 0)} edges)"
        )
        return 0
    except DashboardError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
