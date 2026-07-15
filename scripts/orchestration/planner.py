"""Knowledge retrieval planning and full task planning (Phase 8, Parts 4-5).

Retrieval reuses `AiOsService.search` (which itself delegates to
`semantic_discovery`) — this module never re-implements search or graph
traversal. Nothing here executes a workflow; it only produces a plan for a
human to review.
"""
from __future__ import annotations

from pathlib import Path

from . import DEFAULT_RETRIEVAL_LIMIT, MAX_RETRIEVAL_LIMIT
from .registry import build_agent_registry
from .router import classify_task
from .utils import clamp, ensure_scripts_path, load_json
from .workflow import build_workflow_registry


def build_retrieval_plan(root: Path, classification: dict, *, project: str | None = None,
                          limit: int = DEFAULT_RETRIEVAL_LIMIT) -> dict:
    """Describe what will be searched before a workflow begins (Part 4)."""
    limit = clamp(limit, 1, MAX_RETRIEVAL_LIMIT)
    queries = list(classification.get("knowledgeQueries", []))

    # Paths are derived from actual memory records tagged with this project
    # (this repo has no fixed knowledge/projects/<name>/ directory convention).
    paths: list = []
    if project:
        memory_index = load_json(root / "generated" / "memory-index.json", {}) or {}
        for record in memory_index.get("records", []):
            if record.get("project") == project:
                path = record.get("path", "")
                if path and path not in paths:
                    paths.append(path)

    graph_seeds = [f"project:{project}"] if project else []

    return {
        "queries": queries,
        "types": ["project", "memory", "skill", "document"],
        "paths": paths,
        "graphSeeds": graph_seeds,
        "maxResults": limit,
    }


def _run_retrieval(root: Path, retrieval_plan: dict) -> list:
    """Execute the retrieval plan using the existing search engine."""
    ensure_scripts_path()
    from ai_os_service.errors import ServiceError
    from ai_os_service.service import AiOsService

    service = AiOsService(root)
    retrieved: list = []
    seen_ids: set = set()
    for query in retrieval_plan["queries"]:
        if not query or not query.strip():
            continue
        try:
            result = service.search(query=query, limit=retrieval_plan["maxResults"])
        except ServiceError:
            continue
        for item in result.get("results", []):
            if item["id"] in seen_ids:
                continue
            if "memory" not in retrieval_plan["types"] and item.get("type") in {"memory"}:
                continue
            seen_ids.add(item["id"])
            retrieved.append(item)
    retrieved.sort(key=lambda item: -item.get("score", 0))
    return retrieved[: retrieval_plan["maxResults"]]


def create_plan(root: Path, task: str, *, project: str | None = None,
                 workflow_override: str | None = None,
                 limit: int = DEFAULT_RETRIEVAL_LIMIT,
                 no_memory: bool = False, no_history: bool = False) -> dict:
    """Build a structured plan: classify, select workflow/agents, retrieve, assemble.

    Performs no execution. `no_memory` excludes memory-type results from
    retrieval; `no_history` skips retrieval entirely. Neither ever writes
    anything.
    """
    classification = classify_task(root, task, project=project, requested_workflow=workflow_override)
    retrieval_plan = build_retrieval_plan(root, classification, project=project, limit=limit)
    if no_memory:
        retrieval_plan["types"] = [t for t in retrieval_plan["types"] if t != "memory"]

    retrieved_knowledge = [] if no_history else _run_retrieval(root, retrieval_plan)

    workflow_registry = build_workflow_registry(root)
    workflow = next(
        (w for w in workflow_registry["workflows"] if w["id"] == classification["suggestedWorkflow"]), None)

    agent_registry = build_agent_registry(root)
    agents_by_id = {a["id"]: a for a in agent_registry["agents"]}
    selected_agents = [agents_by_id[a] for a in classification["suggestedAgents"] if a in agents_by_id]

    risks = list(classification.get("warnings", []))
    if classification["intent"] == "unknown":
        risks.append("task intent could not be classified; a workflow must be chosen manually")
    if not no_history and not retrieved_knowledge:
        risks.append("no relevant knowledge was retrieved for this task")

    return {
        "taskId": classification["taskId"],
        "taskSummary": task,
        "project": project,
        "intent": classification["intent"],
        "confidence": classification["confidence"],
        "matchedSignals": classification["matchedSignals"],
        "selectedWorkflow": workflow,
        "selectedAgents": selected_agents,
        "retrievalPlan": retrieval_plan,
        "retrievedKnowledge": retrieved_knowledge,
        "steps": workflow.get("steps", []) if workflow else [],
        "approvalGates": workflow.get("approvalGates", []) if workflow else [],
        "validationRequirements": workflow.get("validationGates", []) if workflow else [],
        "expectedOutputArtifacts": workflow.get("outputArtifacts", []) if workflow else [],
        "memorySuggestionPolicy": workflow.get("memorySuggestionPolicy", "") if workflow else "",
        "auditPolicy": workflow.get("auditPolicy", "") if workflow else "",
        "risksAndWarnings": risks,
    }
