#!/usr/bin/env python3
"""Add a memory record and update memory/registry.json."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import (
    ALLOWED_RETENTION,
    ALLOWED_SCOPES,
    ALLOWED_SENSITIVITY,
    ALLOWED_TYPES,
    content_folder_for,
    default_body,
    ensure_safe_content_path,
    generate_id,
    infer_retention,
    load_registry,
    likely_secret,
    registry_entry,
    render_front_matter,
    repo_root,
    save_registry,
    today_iso,
    validate_metadata,
)


def parse_tags(raw: str):
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def create_record(root: Path, args) -> int:
    if args.type not in ALLOWED_TYPES:
        raise ValueError(f"invalid --type: {args.type}")
    if args.scope not in ALLOWED_SCOPES:
        raise ValueError(f"invalid --scope: {args.scope}")
    if args.sensitivity not in ALLOWED_SENSITIVITY:
        raise ValueError(f"invalid --sensitivity: {args.sensitivity}")
    if args.retention and args.retention not in ALLOWED_RETENTION:
        raise ValueError(f"invalid --retention: {args.retention}")

    suspicious = [value for value in [args.title, args.summary, args.source] if value and likely_secret(value)]
    if suspicious:
        raise ValueError("input appears to contain a likely secret; use placeholders instead")

    registry = load_registry(root)
    records = registry["records"]
    record_id = generate_id(root, args.type, args.title)
    folder = content_folder_for(args.type)
    content_path = ensure_safe_content_path(f"{folder}/{record_id}.md")

    now = today_iso()
    metadata = {
        "id": record_id,
        "title": args.title,
        "type": args.type,
        "scope": args.scope,
        "project": args.project,
        "status": "active",
        "created": now,
        "updated": now,
        "source": args.source,
        "summary": args.summary,
        "tags": parse_tags(args.tags),
        "related": [],
        "sensitivity": args.sensitivity,
        "retention": args.retention or infer_retention(args.type, args.scope),
        "contentPath": content_path,
    }
    errors = validate_metadata(metadata)
    if errors:
        raise ValueError("; ".join(errors))

    if any(row["id"] == record_id for row in records):
        raise ValueError(f"duplicate id: {record_id}")

    full_path = root / content_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    body = default_body(args.type, args.title, args.summary)
    full_path.write_text(render_front_matter(metadata) + "\n\n" + body + "\n", encoding="utf-8", newline="\n")

    records.append(registry_entry(metadata))
    save_registry(root, registry)

    print(f"CREATED {content_path}")
    print("UPDATED memory/registry.json")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", required=True, help="Memory type")
    parser.add_argument("--title", required=True, help="Memory title")
    parser.add_argument("--scope", required=True, help="global|project|session")
    parser.add_argument("--project", default=None, help="Project identifier")
    parser.add_argument("--summary", required=True, help="Short summary")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--sensitivity", default="internal", help="public|internal|restricted")
    parser.add_argument("--retention", default=None, help="permanent|project|temporary|archive")
    parser.add_argument("--source", default="memory-add", help="Evidence or source description")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return create_record(repo_root(), args)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
