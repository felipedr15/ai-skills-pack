#!/usr/bin/env python3
"""List memory records from memory/registry.json with filters."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import load_registry, repo_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type")
    parser.add_argument("--scope")
    parser.add_argument("--project")
    parser.add_argument("--status")
    parser.add_argument("--tag")
    parser.add_argument("--sensitivity")
    return parser


def include(row, args) -> bool:
    if args.type and row.get("type") != args.type:
        return False
    if args.scope and row.get("scope") != args.scope:
        return False
    if args.project and (row.get("project") or "") != args.project:
        return False
    if args.status and row.get("status") != args.status:
        return False
    if args.tag and args.tag not in row.get("tags", []):
        return False
    if args.sensitivity and row.get("sensitivity") != args.sensitivity:
        return False
    return True


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = sorted(load_registry(repo_root())["records"], key=lambda item: item["id"])
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    matches = [row for row in rows if include(row, args)]
    print(f"{'ID':<42} {'Title':<48} {'Type':<11} {'Project':<12} {'Status':<11} Path")
    print("-" * 150)
    for row in matches:
        project = row.get("project") or "-"
        print(f"{row['id']:<42} {row['title'][:47]:<48} {row['type']:<11} {project[:11]:<12} {row['status']:<11} {row['path']}")
    print(f"\n{len(matches)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
