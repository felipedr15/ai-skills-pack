"""Aggregate statistics from all generated JSON artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import GENERATOR, SCHEMA_VERSION


def _load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if missing or invalid."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _file_timestamp(path: Path) -> str | None:
    """Get ISO timestamp of file modification time."""
    if not path.is_file():
        return None
    mtime = path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check_staleness(data: dict | None, path: Path) -> dict:
    """Check if a generated artifact exists and extract its generatedAt."""
    if data is None:
        return {"exists": False, "generatedAt": None, "stale": True, "path": str(path.name)}
    generated_at = data.get("generatedAt")
    return {
        "exists": True,
        "generatedAt": generated_at,
        "stale": False,
        "path": str(path.name),
    }


def aggregate_repository(root: Path) -> dict:
    """Aggregate repository index stats."""
    data = _load_json(root / "generated" / "repository-index.json")
    if data is None:
        return {"available": False, "counts": {}, "totalFiles": 0}
    counts = data.get("counts", {})
    total = sum(counts.values()) if isinstance(counts, dict) else 0
    return {"available": True, "counts": counts, "totalFiles": total}


def aggregate_skills(root: Path) -> dict:
    """Aggregate skill registry stats."""
    data = _load_json(root / "generated" / "skills.json")
    if data is None:
        return {"available": False, "totalSkills": 0, "skills": []}
    skills = data.get("skills", [])
    by_status: dict[str, int] = {}
    for skill in skills:
        status = skill.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
    summary = [
        {"id": s.get("id", ""), "name": s.get("name", ""), "version": s.get("version", ""), "status": s.get("status", "")}
        for s in skills
    ]
    return {"available": True, "totalSkills": len(skills), "byStatus": by_status, "skills": summary}


def aggregate_memory(root: Path) -> dict:
    """Aggregate memory index stats."""
    data = _load_json(root / "generated" / "memory-index.json")
    if data is None:
        return {"available": False, "totalRecords": 0, "records": []}
    records = data.get("records", [])
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for rec in records:
        rtype = rec.get("type", "unknown")
        rstatus = rec.get("status", "unknown")
        by_type[rtype] = by_type.get(rtype, 0) + 1
        by_status[rstatus] = by_status.get(rstatus, 0) + 1
    summary = [
        {"id": r.get("id", ""), "title": r.get("title", ""), "type": r.get("type", ""), "status": r.get("status", "")}
        for r in records
    ]
    return {"available": True, "totalRecords": len(records), "byType": by_type, "byStatus": by_status, "records": summary}


def aggregate_knowledge_graph(root: Path) -> dict:
    """Aggregate knowledge graph stats."""
    data = _load_json(root / "generated" / "knowledge-graph.json")
    if data is None:
        return {"available": False, "totalNodes": 0, "totalEdges": 0}
    stats = data.get("stats", {})
    return {
        "available": True,
        "totalNodes": stats.get("nodes", 0),
        "totalEdges": stats.get("edges", 0),
        "nodesByType": stats.get("nodesByType", {}),
        "edgesByType": stats.get("edgesByType", {}),
        "unresolvedReferences": len(data.get("unresolvedReferences", [])),
    }


def aggregate_discovery(root: Path) -> dict:
    """Aggregate discovery index stats."""
    data = _load_json(root / "generated" / "discovery-index.json")
    if data is None:
        return {"available": False, "documents": 0, "entities": 0, "terms": 0, "relationships": 0}
    stats = data.get("stats", {})
    diagnostics = data.get("diagnostics", {})
    return {
        "available": True,
        "documents": stats.get("documents", 0),
        "entities": stats.get("entities", 0),
        "terms": stats.get("terms", 0),
        "relationships": stats.get("relationships", 0),
        "warnings": len(diagnostics.get("warnings", [])),
        "unindexedFiles": len(diagnostics.get("unindexedFiles", [])),
    }


def aggregate_artifacts(root: Path) -> dict:
    """Check artifact freshness and timestamps."""
    gen = root / "generated"
    artifacts = [
        ("skills.json", gen / "skills.json"),
        ("repository-index.json", gen / "repository-index.json"),
        ("memory-index.json", gen / "memory-index.json"),
        ("knowledge-graph.json", gen / "knowledge-graph.json"),
        ("discovery-index.json", gen / "discovery-index.json"),
    ]
    result = []
    for name, path in artifacts:
        data = _load_json(path)
        info = _check_staleness(data, path)
        info["fileTimestamp"] = _file_timestamp(path)
        result.append(info)
    return {"artifacts": result}


def aggregate_orchestration(root: Path) -> dict:
    """Aggregate Phase 8 registry/health stats.

    Sourced only from committed `generated/*.json` artifacts (agent
    registry, workflow registry, knowledge health) — never from local
    `.ai-os/` runtime state (sessions/approvals/suggestions/feedback/audit
    are served live via /api/orchestration/* instead, so they never end up
    baked into this committed snapshot).
    """
    agents = _load_json(root / "generated" / "agent-registry.json")
    workflows = _load_json(root / "generated" / "workflow-registry.json")
    health = _load_json(root / "generated" / "knowledge-health.json")

    return {
        "available": agents is not None and workflows is not None and health is not None,
        "agentCount": (agents or {}).get("stats", {}).get("totalAgents", 0),
        "workflowCount": (workflows or {}).get("stats", {}).get("totalWorkflows", 0),
        "agentsByRole": (agents or {}).get("stats", {}).get("byRole", {}),
        "knowledgeHealthScore": (health or {}).get("overallScore", 0),
        "knowledgeHealthCategories": (health or {}).get("categoryScores", {}),
    }


def build_dashboard_data(root: Path) -> dict:
    """Build the complete dashboard data payload."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "repository": aggregate_repository(root),
        "skills": aggregate_skills(root),
        "memory": aggregate_memory(root),
        "knowledgeGraph": aggregate_knowledge_graph(root),
        "discovery": aggregate_discovery(root),
        "artifacts": aggregate_artifacts(root),
        "orchestration": aggregate_orchestration(root),
    }
