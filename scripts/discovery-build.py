#!/usr/bin/env python3
"""Build the semantic discovery index artifacts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_discovery.build import build, check_index, write_index
from semantic_discovery.validate import DiscoveryError

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check only, do not write")
    args = parser.parse_args(argv)

    try:
        index = build(ROOT)
        stats = index.get("stats", {})

        if args.check:
            check_index(index, ROOT)
            print(
                f"PASS discovery index is current "
                f"({stats.get('documents', 0)} documents, "
                f"{stats.get('entities', 0)} entities, "
                f"{stats.get('terms', 0)} terms)"
            )
            return 0

        write_index(index, ROOT)
        print(
            f"PASS discovery index generated "
            f"({stats.get('documents', 0)} documents, "
            f"{stats.get('entities', 0)} entities, "
            f"{stats.get('terms', 0)} terms)"
        )
        return 0
    except DiscoveryError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
