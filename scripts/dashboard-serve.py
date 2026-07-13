#!/usr/bin/env python3
"""Start the local AI OS dashboard server."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dashboard import DEFAULT_PORT
from dashboard.server import serve

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Start the AI OS dashboard server.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number (default: {DEFAULT_PORT})")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args(argv)

    html_path = ROOT / "generated" / "dashboard.html"
    if not html_path.is_file():
        print("Dashboard not built. Run: python scripts/dashboard-build.py", file=sys.stderr)
        return 1

    serve(ROOT, port=args.port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
