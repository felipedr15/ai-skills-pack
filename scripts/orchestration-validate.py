#!/usr/bin/env python3
"""Validate Phase 8 orchestration artifacts and local runtime state."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orchestration.validate import validate_all

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures, warnings = validate_all(ROOT)
    for item in warnings:
        print(f"WARNING {item}")
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1
    print("PASS orchestration validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
