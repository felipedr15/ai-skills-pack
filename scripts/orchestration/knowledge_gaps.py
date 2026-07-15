"""Knowledge gap detection and health scoring (Phase 8, Part 9).

Reuses the existing knowledge graph / discovery / registry artifacts —
this module never re-parses source files itself. Scores are explainable
integer heuristics (0-100), not precise measurements; every score is
accompanied by the raw counts it was computed from. Only aggregate counts
(never content) are read from local runtime state (`.ai-os/sessions`,
`.ai-os/feedback`), consistent with generated/ artifacts never embedding
local session data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import GENERATOR, SCHEMA_VERSION
from .freshness import review_due
from .utils import load_json

# This system does not log search queries (no telemetry) so "frequent
# search queries with weak results" / "no-result searches" cannot be
# computed from history; this is a documented, deliberate limitation.
NO_QUERY_LOG_NOTE = "search queries are not logged (no telemetry); this signal is unavailable by design"


def _score(hits: int, total: int) -> int:
    """Deterministic 0-100 score: 100 when nothing is wrong, degrading with hit ratio."""
    if total <= 0:
        return 100
    ratio = min(1.0, hits / total)
    return round((1.0 - ratio) * 100)


def _graph_integrity(root: Path) -> dict:
    graph = load_json(root / "generated" / "knowledge-graph.json", {}) or {}
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    unresolved = graph.get("unresolvedReferences", [])

    connected = set()
    for edge in edges:
        connected.add(edge.get("from"))
        connected.add(edge.get("to"))
    isolated = [n["id"] for n in nodes if n["id"] not in connected]

    total = max(1, len(nodes))
    score = _score(len(unresolved) + len(isolated), total * 2)
    return {
        "score": score,
        "unresolvedReferences": unresolved,
        "isolatedNodes": isolated,
    }


def _project_documentation(root: Path) -> dict:
    graph = load_json(root / "generated" / "knowledge-graph.json", {}) or {}
    projects = [n for n in graph.get("nodes", []) if n.get("type") == "project"]
    gaps = []
    evaluated = 0
    for project in projects:
        source = root / project.get("sourcePath", "")
        if not source.is_dir():
            continue  # not a directory-shaped project; nothing to check
        evaluated += 1
        if not (source / "README.md").is_file():
            gaps.append({"category": "project-without-overview", "severity": "warning",
                         "description": f"{project['id']} has no README.md overview"})
        if not (source / "ARCHITECTURE.md").is_file():
            gaps.append({"category": "project-without-architecture", "severity": "warning",
                         "description": f"{project['id']} has no ARCHITECTURE.md"})
        if not (source / "TESTING.md").is_file():
            gaps.append({"category": "project-without-validation-checklist", "severity": "warning",
                         "description": f"{project['id']} has no TESTING.md validation checklist"})
    score = _score(len(gaps), max(1, evaluated) * 3)
    return {"score": score, "gaps": gaps, "evaluated": evaluated}


def _skill_documentation(root: Path) -> dict:
    skills = load_json(root / "generated" / "skills.json", {}) or {}
    entries = skills.get("skills", [])
    gaps = []
    for skill in entries:
        path = root / skill.get("path", "")
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if "validation" not in text:
            gaps.append({"category": "skill-without-validation-section", "severity": "info",
                         "description": f"{skill.get('id')} has no validation section"})
    score = _score(len(gaps), max(1, len(entries)))
    return {"score": score, "gaps": gaps}


def _memory_linkage(root: Path) -> dict:
    memory_index = load_json(root / "generated" / "memory-index.json", {}) or {}
    records = memory_index.get("records", [])
    gaps = []
    project_scoped = [r for r in records if r.get("scope") == "project"]
    for record in project_scoped:
        if not record.get("project"):
            gaps.append({"category": "memory-without-project-link", "severity": "warning",
                         "description": f"{record.get('id')} is project-scoped but has no project link"})
    score = _score(len(gaps), max(1, len(project_scoped)))
    return {"score": score, "gaps": gaps}


def _workflow_governance(root: Path) -> dict:
    registry = load_json(root / "generated" / "workflow-registry.json", {}) or {}
    workflows = registry.get("workflows", [])
    gaps = []
    for workflow in workflows:
        if not workflow.get("approvalGates"):
            gaps.append({"category": "workflow-without-approval-gate", "severity": "critical",
                         "description": f"{workflow.get('id')} has no approval gate"})
    score = _score(len(gaps), max(1, len(workflows)))
    return {"score": score, "gaps": gaps}


def _freshness_health(root: Path) -> dict:
    due = review_due(root, days=30)
    gaps = []
    for item in due:
        severity = "critical" if item.get("overdue") else "warning" if item.get("dueSoon") else "info"
        gaps.append({"category": "review-due", "severity": severity,
                     "description": f"{item['path']}: {'; '.join(item['issues']) or 'review due'}"})
    score = _score(len(due), max(1, len(due) + 10))
    return {"score": score, "gaps": gaps, "reviewDueItems": due}


def _session_health(root: Path) -> dict:
    from .session import list_sessions
    sessions = list_sessions(root)
    if not sessions:
        return {"score": 100, "gaps": [], "unknownIntentCount": 0, "failureCount": 0, "totalSessions": 0}
    unknown = sum(1 for s in sessions if s.get("intent") == "unknown")
    failed = sum(1 for s in sessions if s.get("status") == "failed" or s.get("failures"))
    gaps = []
    if unknown:
        gaps.append({"category": "unknown-task-intents", "severity": "info",
                     "description": f"{unknown} session(s) had an unclassifiable task intent"})
    if failed:
        gaps.append({"category": "repeated-session-failures", "severity": "warning",
                     "description": f"{failed} session(s) recorded at least one failure"})
    score = _score(unknown + failed, len(sessions) * 2)
    return {"score": score, "gaps": gaps, "unknownIntentCount": unknown, "failureCount": failed,
            "totalSessions": len(sessions)}


def _feedback_signal(root: Path) -> dict:
    from .feedback import list_feedback
    entries = list_feedback(root)
    if not entries:
        return {"score": 100, "gaps": [], "correctionCount": 0}
    correction_types = {"incorrect", "wrong-project", "wrong-procedure", "outdated"}
    by_target: dict = {}
    for item in entries:
        if item.get("type") in correction_types:
            by_target[item.get("targetId")] = by_target.get(item.get("targetId"), 0) + 1
    repeated = {target: count for target, count in by_target.items() if count > 1}
    gaps = []
    for target, count in sorted(repeated.items()):
        gaps.append({"category": "repeated-user-corrections", "severity": "warning",
                     "description": f"{target} received {count} correction(s)"})
    score = _score(sum(repeated.values()), max(1, len(entries)))
    return {"score": score, "gaps": gaps, "correctionCount": sum(repeated.values())}


def build_knowledge_health(root: Path, *, include_live: bool = True) -> dict:
    """Build the knowledge-health report.

    `include_live=False` produces the deterministic, repo-only report used
    for the committed `generated/knowledge-health.json` artifact (safe to
    `--check` for staleness across machines). `include_live=True` (the
    default, used by the `knowledge-health`/`knowledge-gaps` CLI commands
    and the dashboard's live endpoint) additionally overlays session/
    feedback signal categories computed from local `.ai-os/` runtime state
    at request time — this view is never written into the committed
    artifact, since local runtime state differs machine to machine.
    """
    categories = {
        "graphIntegrity": _graph_integrity(root),
        "projectDocumentation": _project_documentation(root),
        "skillDocumentation": _skill_documentation(root),
        "memoryLinkage": _memory_linkage(root),
        "workflowGovernance": _workflow_governance(root),
        "freshness": _freshness_health(root),
    }
    if include_live:
        categories["sessionHealth"] = _session_health(root)
        categories["feedbackSignal"] = _feedback_signal(root)

    category_scores = {name: data["score"] for name, data in categories.items()}
    overall_score = round(sum(category_scores.values()) / len(category_scores))

    gaps = []
    for data in categories.values():
        gaps.extend(data.get("gaps", []))
    gaps = gaps[:100]

    recommendations = []
    worst = sorted(category_scores.items(), key=lambda kv: kv[1])[:3]
    for name, score in worst:
        if score < 90:
            recommendations.append(f"Improve {name} (score {score}/100) — see related gaps for specifics.")
    if not recommendations:
        recommendations.append("No significant gaps detected in the current snapshot.")

    diagnostics = {
        "searchQueryLogging": NO_QUERY_LOG_NOTE,
        "scoreRange": "0-100, higher is healthier; heuristic, not a precise measurement",
        "includesLiveSignals": include_live,
    }
    if include_live:
        diagnostics["sessionsEvaluated"] = categories["sessionHealth"]["totalSessions"]
        diagnostics["feedbackEvaluated"] = categories["feedbackSignal"]["correctionCount"]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "overallScore": overall_score,
        "categoryScores": category_scores,
        "gaps": gaps,
        "staleItems": [],
        "unresolvedReferences": categories["graphIntegrity"]["unresolvedReferences"],
        "isolatedNodes": categories["graphIntegrity"]["isolatedNodes"],
        "reviewDueItems": categories["freshness"]["reviewDueItems"],
        "conflicts": [],
        "recommendations": recommendations,
        "diagnostics": diagnostics,
    }


def validate_knowledge_health(report: object) -> tuple:
    failures: list = []
    warnings: list = []
    if not isinstance(report, dict):
        return ["knowledge health report root must be an object"], warnings
    if report.get("schemaVersion") != SCHEMA_VERSION:
        failures.append(f"unsupported schemaVersion: {report.get('schemaVersion')}")
    score = report.get("overallScore")
    if not isinstance(score, int) or not (0 <= score <= 100):
        failures.append(f"overallScore must be an integer 0-100, got {score!r}")
    for name, value in report.get("categoryScores", {}).items():
        if not isinstance(value, int) or not (0 <= value <= 100):
            failures.append(f"categoryScores.{name} must be an integer 0-100, got {value!r}")
    return failures, warnings


def compare_reports_ignoring_generated_at(current: dict, saved: dict) -> bool:
    import json
    left = json.loads(json.dumps(current))
    right = json.loads(json.dumps(saved))
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    return left == right
