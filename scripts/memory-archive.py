#!/usr/bin/env python3
"""Archive a memory record by ID."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import (
    find_record,
    load_registry,
    parse_front_matter,
    registry_entry,
    render_front_matter,
    repo_root,
    save_registry,
    today_iso,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Memory ID")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        registry = load_registry(root)
        record = find_record(registry["records"], args.id)
        if not record:
            raise ValueError(f"memory id not found: {args.id}")

        source_path = root / record["path"]
        if not source_path.is_file():
            raise ValueError(f"missing source record: {record['path']}")

        metadata, body = parse_front_matter(source_path)
        archive_rel = f"memory/archive/{source_path.name}"
        archive_path = root / archive_rel
        if archive_path.exists() and archive_path.resolve() != source_path.resolve():
            raise ValueError(f"archive target already exists: {archive_rel}")

        metadata["status"] = "archived"
        metadata["retention"] = "archive"
        metadata["updated"] = today_iso()
        metadata["contentPath"] = archive_rel
        if "Archive date:" not in body:
            body = body.rstrip() + "\n\n## Archive Notes\n\nArchive date: " + today_iso() + "\n"

        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_text(render_front_matter(metadata) + "\n\n" + body.strip() + "\n", encoding="utf-8", newline="\n")
        if archive_path.resolve() != source_path.resolve():
            source_path.unlink()

        record.update(registry_entry(metadata))
        save_registry(root, registry)

        print(f"ARCHIVED {record['id']} -> {archive_rel}")
        print("UPDATED memory/registry.json")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
