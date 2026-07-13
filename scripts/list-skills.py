#!/usr/bin/env python3
"""List skills from the generated registry without changing repository files."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "generated/skills.json"


def main():
    if not REGISTRY.is_file():
        print("FAIL generated/skills.json is missing; run scripts/generate-skill-registry.py", file=sys.stderr)
        return 1
    try:
        rows = json.loads(REGISTRY.read_text(encoding="utf-8"))["skills"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL invalid generated skill registry: {exc}", file=sys.stderr)
        return 1
    print(f"{'ID':<28} {'NAME':<28} {'VERSION':<10} {'STATUS':<12} PATH")
    print("-" * 110)
    missing = False
    for skill in rows:
        exists = (ROOT / skill["path"]).is_file()
        missing |= not exists
        suffix = " [MISSING]" if not exists else ""
        print(f"{skill['id']:<28} {skill['name']:<28} {skill['version']:<10} {skill['status']:<12} {skill['path']}{suffix}")
    print(f"\n{len(rows)} skills registered.")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
