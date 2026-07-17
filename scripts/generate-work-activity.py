#!/usr/bin/env python3
"""Generate deterministic work-activity signals from existing local sources.

Aggregates purely from memory/ (via memory/registry.json + front matter) and
generated/knowledge-graph.json's project/memory nodes and belongs_to edges --
no new raw inputs (REQ-002).

Deliberately excludes .ai-os/sessions/ runtime state, for the same reason
scripts/generate-knowledge-health.py's deterministic view excludes local
session/feedback signal: .ai-os/ is git-ignored, machine-local state, so
baking it into a committed, --check-verified generated/ artifact would make
that artifact non-deterministic across machines and CI checkouts (it would
never match between a fresh clone and the machine that generated it). A
live, .ai-os/-inclusive view belongs in a future CLI command (out of scope
for this task group), mirroring how `ai-os.py knowledge-health` provides the
live view alongside this generator's deterministic one.

`windowDays` is recorded as a documented constant, not applied as a
wall-clock-relative filter -- filtering by "now" would make identical inputs
produce different output on different days, which would violate the
determinism this generator (like every other Phase 1-8 generator) must hold.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import load_registry, parse_front_matter, repo_root, slugify  # noqa: E402

SCHEMA_VERSION = "1.0.0"
GENERATOR = "ai-os-work-activity"
WINDOW_DAYS = 90


class WorkActivityError(ValueError):
    pass


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_memory_records(root: Path) -> list[dict]:
    """Best-effort load of memory record front matter, keyed by id.

    Lenient by design: structural validation of memory/ is
    scripts/generate-memory-index.py's job (already wired into
    validate-all.py); this aggregator simply skips anything it cannot parse
    rather than failing the whole summary over one bad record.
    """
    records = []
    registry = load_registry(root)
    for row in registry.get("records", []):
        path_value = row.get("path")
        if not path_value:
            continue
        path = root / path_value
        if not path.is_file():
            continue
        try:
            metadata, _body = parse_front_matter(path)
        except Exception:  # noqa: BLE001
            continue
        records.append(metadata)
    return records


def load_knowledge_graph(root: Path) -> dict:
    path = root / "generated" / "knowledge-graph.json"
    if not path.is_file():
        return {"nodes": [], "edges": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _project_membership_from_graph(graph: dict) -> dict[str, dict]:
    """Map project node id -> {"name": str, "memberIds": set[node id]}."""
    projects: dict[str, dict] = {}
    for node in graph.get("nodes", []):
        if node.get("type") == "project":
            projects[node["id"]] = {"name": node.get("name", ""), "memberIds": set()}
    for edge in graph.get("edges", []):
        target = edge.get("to")
        if edge.get("type") == "belongs_to" and target in projects:
            projects[target]["memberIds"].add(edge.get("from"))
    return projects


def build_work_activity(root: Path) -> dict:
    graph = load_knowledge_graph(root)
    memory_records = load_memory_records(root)
    by_node_id = {f"memory:{r['id']}": r for r in memory_records if r.get("id")}

    project_membership = _project_membership_from_graph(graph)
    projects = []
    for info in project_membership.values():
        member_ids = sorted(info["memberIds"])
        member_records = [by_node_id[mid] for mid in member_ids if mid in by_node_id]
        session_count = sum(1 for r in member_records if r.get("type") == "session")
        last_active_values = [r.get("updated") for r in member_records if r.get("updated")]
        last_active = max(last_active_values) if last_active_values else None
        projects.append(
            {
                "project": info["name"],
                "sessionCount": session_count,
                "lastActiveAt": last_active,
                "relatedEntities": member_ids,
            }
        )
    projects.sort(key=lambda p: p["project"])

    tag_sources: dict[str, list[str]] = defaultdict(list)
    for record in memory_records:
        record_id = record.get("id")
        if not record_id:
            continue
        for tag in record.get("tags") or []:
            if isinstance(tag, str) and tag:
                tag_sources[tag].append(f"memory:{record_id}")
    focus_areas = [
        {"term": term, "weight": len(sources), "sources": sorted(sources)}
        for term, sources in tag_sources.items()
    ]
    focus_areas.sort(key=lambda item: (-item["weight"], item["term"]))

    activity_summary = {
        "totalSessions": sum(1 for r in memory_records if r.get("type") == "session"),
        "totalMemoryRecords": len(memory_records),
    }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _now_iso(),
        "generator": GENERATOR,
        "windowDays": WINDOW_DAYS,
        "projects": projects,
        "focusAreas": focus_areas,
        "activitySummary": activity_summary,
    }


def collect_known_refs(work_activity: dict) -> set[str]:
    """Build the set of normalized identifiers expertise evidence refs may
    resolve against, derived purely from a built work-activity object:
    project slugs, focus-area term slugs, and referenced memory record ids.

    Used as `known_refs` for scripts/profile/validate.py's
    check_evidence_resolution() -- an unresolved ref is always a warning,
    never a failure, and this set only ever grows what can be recognized,
    never what is accepted as valid evidence shape.
    """
    refs: set[str] = set()
    for project in work_activity.get("projects", []):
        slug = slugify(str(project.get("project", "")))
        if slug and slug != "memory":
            refs.add(slug)
        for entity_id in project.get("relatedEntities", []):
            if isinstance(entity_id, str) and entity_id.startswith("memory:"):
                refs.add(entity_id[len("memory:") :])
    for area in work_activity.get("focusAreas", []):
        slug = slugify(str(area.get("term", "")))
        if slug and slug != "memory":
            refs.add(slug)
    return refs


def compare_ignoring_generated_at(current: dict, saved: dict) -> bool:
    left = dict(current)
    right = dict(saved)
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    return left == right


def render_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def render_markdown(data: dict) -> str:
    lines = [
        "# Generated Work Activity",
        "",
        "> Generated from memory/ and generated/knowledge-graph.json. Do not edit this file directly.",
        "",
        f"Generated at: {data['generatedAt']}",
        f"Window (documented, not filtered): {data['windowDays']} days",
        "",
        "## Projects",
        "",
    ]
    if data["projects"]:
        lines.extend(["| Project | Sessions | Last Active | Related Entities |", "|---|---|---|---|"])
        for project in data["projects"]:
            lines.append(
                "| {project} | {sessions} | {last} | {count} |".format(
                    project=project["project"],
                    sessions=project["sessionCount"],
                    last=project["lastActiveAt"] or "-",
                    count=len(project["relatedEntities"]),
                )
            )
    else:
        lines.append("None.")

    lines.extend(["", "## Focus Areas", ""])
    if data["focusAreas"]:
        lines.extend(["| Term | Weight |", "|---|---|"])
        for area in data["focusAreas"]:
            lines.append(f"| {area['term']} | {area['weight']} |")
    else:
        lines.append("None.")

    summary = data["activitySummary"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Total sessions: {summary['totalSessions']}",
            f"- Total memory records: {summary['totalMemoryRecords']}",
            "",
        ]
    )
    return "\n".join(lines)


def _normalize_markdown_timestamp(content: str) -> str:
    lines = content.splitlines()
    return "\n".join(
        "Generated at: <ignored>" if line.startswith("Generated at: ") else line for line in lines
    )


def write_report(data: dict, root: Path) -> None:
    json_path = root / "generated" / "work-activity.json"
    md_path = root / "generated" / "work-activity.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(render_json(data), encoding="utf-8", newline="\n")
    md_path.write_text(render_markdown(data), encoding="utf-8", newline="\n")


def check_report(data: dict, root: Path) -> None:
    json_path = root / "generated" / "work-activity.json"
    md_path = root / "generated" / "work-activity.md"
    if not json_path.is_file() or not md_path.is_file():
        raise WorkActivityError("stale generated files: generated/work-activity.json, generated/work-activity.md")

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    if not compare_ignoring_generated_at(data, saved):
        raise WorkActivityError("stale generated files: generated/work-activity.json")

    expected_md = render_markdown(data)
    saved_md = md_path.read_text(encoding="utf-8")
    if _normalize_markdown_timestamp(saved_md) != _normalize_markdown_timestamp(expected_md):
        raise WorkActivityError("stale generated files: generated/work-activity.md")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated work-activity files are stale")
    args = parser.parse_args(argv)

    root = repo_root()
    data = build_work_activity(root)

    try:
        if args.check:
            check_report(data, root)
            print(f"PASS work activity is current ({len(data['projects'])} projects)")
            return 0
        write_report(data, root)
        print(f"PASS work activity generated ({len(data['projects'])} projects)")
        return 0
    except WorkActivityError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
