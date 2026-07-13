#!/usr/bin/env python3
"""Validate existing discovery index artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_discovery.validate import DiscoveryError, load_discovery_index, validate_index_object

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "generated" / "discovery-index.json"


def main(argv=None) -> int:
    if not INDEX_PATH.is_file():
        print("FAIL generated/discovery-index.json is missing; run scripts/discovery-build.py", file=sys.stderr)
        return 1
    try:
        index = load_discovery_index(INDEX_PATH)
    except DiscoveryError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    failures, warnings = validate_index_object(index)
    for item in warnings:
        print(f"WARNING {item}")
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1
    stats = index.get("stats", {})
    print(
        f"PASS discovery index validation "
        f"({stats.get('documents', 0)} documents, "
        f"{stats.get('entities', 0)} entities, "
        f"{stats.get('terms', 0)} terms)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
