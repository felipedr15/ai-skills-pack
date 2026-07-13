#!/usr/bin/env python3
"""Promote memory records between scopes/types with traceability."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import (
    content_folder_for,
    default_body,
    ensure_safe_content_path,
    find_record,
    generate_id,
    infer_retention,
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
    parser.add_argument("--id", required=True, help="Source memory ID")
    parser.add_argument("--target-type", help="Target type when changing semantics")
    parser.add_argument("--target-scope", help="Target scope when promoting")
    parser.add_argument("--project", help="Project for promoted record")
    parser.add_argument("--reason", required=True, help="Promotion reason")
    return parser


def is_supported_transition(source_type, source_scope, target_type, target_scope, source_status):
    if source_status == "proposed" and source_type == target_type and source_scope == target_scope:
        return True
    if source_type == "session" and target_type == "project":
        return True
    if source_type == "session" and target_type == "lesson":
        return True
    if source_type == "lesson" and source_scope == "project" and target_type == "lesson" and target_scope == "global":
        return True
    return False


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        registry = load_registry(root)
        source_entry = find_record(registry["records"], args.id)
        if not source_entry:
            raise ValueError(f"memory id not found: {args.id}")

        source_path = root / source_entry["path"]
        if not source_path.is_file():
            raise ValueError(f"missing source record: {source_entry['path']}")

        source_meta, source_body = parse_front_matter(source_path)
        target_type = args.target_type or source_meta["type"]
        target_scope = args.target_scope or source_meta["scope"]

        if not is_supported_transition(source_meta["type"], source_meta["scope"], target_type, target_scope, source_meta["status"]):
            raise ValueError("unsupported promotion transition")

        changed = []

        semantic_change = target_type != source_meta["type"] or target_scope != source_meta["scope"]
        if semantic_change:
            new_id = generate_id(root, target_type, source_meta["title"])
            folder = content_folder_for(target_type)
            new_path_rel = ensure_safe_content_path(f"{folder}/{new_id}.md")
            now = today_iso()

            related = list(source_meta.get("related", []))
            if source_meta["id"] not in related:
                related.append(source_meta["id"])

            promoted = {
                "id": new_id,
                "title": source_meta["title"],
                "type": target_type,
                "scope": target_scope,
                "project": args.project if args.project is not None else source_meta.get("project"),
                "status": "active",
                "created": now,
                "updated": now,
                "source": f"Promotion from {source_meta['id']}: {args.reason}",
                "summary": source_meta["summary"],
                "tags": list(source_meta.get("tags", [])),
                "related": related,
                "sensitivity": source_meta["sensitivity"],
                "retention": infer_retention(target_type, target_scope),
                "contentPath": new_path_rel,
            }

            promoted_path = root / new_path_rel
            promoted_path.parent.mkdir(parents=True, exist_ok=True)
            promoted_body = source_body.strip() + "\n\n## Promotion Notes\n\nReason: " + args.reason + "\n"
            if not source_body.strip():
                promoted_body = default_body(target_type, promoted["title"], promoted["summary"]) + "\n\n## Promotion Notes\n\nReason: " + args.reason + "\n"
            promoted_path.write_text(render_front_matter(promoted) + "\n\n" + promoted_body.strip() + "\n", encoding="utf-8", newline="\n")

            source_related = list(source_meta.get("related", []))
            if new_id not in source_related:
                source_related.append(new_id)
            source_meta["status"] = "superseded"
            source_meta["updated"] = now
            source_meta["related"] = source_related
            source_path.write_text(render_front_matter(source_meta) + "\n\n" + source_body.strip() + "\n", encoding="utf-8", newline="\n")

            source_entry.update(registry_entry(source_meta))
            registry["records"].append(registry_entry(promoted))
            changed.extend([source_meta["contentPath"], promoted["contentPath"]])
        else:
            if source_meta["status"] != "proposed":
                raise ValueError("no semantic change requested and source status is not proposed")
            source_meta["status"] = "active"
            source_meta["updated"] = today_iso()
            if "## Promotion Notes" in source_body:
                updated_body = source_body.strip() + "\nReason: " + args.reason + "\n"
            else:
                updated_body = source_body.strip() + "\n\n## Promotion Notes\n\nReason: " + args.reason + "\n"
            source_path.write_text(render_front_matter(source_meta) + "\n\n" + updated_body.strip() + "\n", encoding="utf-8", newline="\n")
            source_entry.update(registry_entry(source_meta))
            changed.append(source_meta["contentPath"])

        save_registry(root, registry)
        for path in changed:
            print(f"UPDATED {path}")
        print("UPDATED memory/registry.json")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
