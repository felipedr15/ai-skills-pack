"""Workflow registry builder (Phase 8, Part 2).

Compiles hand-authored workflow definitions in `knowledge/workflows/*.json`
into `generated/workflow-registry.json` / `.md`, validating step references
against the agent registry and detecting cyclic step dependencies.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import GENERATOR, SCHEMA_VERSION, WORKFLOW_TYPES
from .registry import build_agent_registry

WORKFLOWS_DIR = "knowledge/workflows"

REQUIRED_WORKFLOW_FIELDS = [
    "id", "name", "description", "triggerIntent", "requiredInputs", "steps",
    "completionCriteria", "failureBehavior", "allowedActions", "forbiddenActions",
    "outputArtifacts", "memorySuggestionPolicy", "auditPolicy",
]

REQUIRED_STEP_FIELDS = ["id", "agent", "action", "requiresApproval"]

VALIDATION_ACTIONS = {"run_approved_validation"}


def _load_workflow_sources(root: Path) -> list:
    directory = root / WORKFLOWS_DIR
    if not directory.is_dir():
        return []
    sources = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_sourcePath"] = f"{WORKFLOWS_DIR}/{path.name}"
        sources.append(data)
    return sources


def _step_graph(steps: list) -> dict:
    """Build an explicit-or-implicit-linear next-step graph, id -> set(next ids)."""
    ids = [s.get("id") for s in steps]
    graph = {sid: set() for sid in ids}
    has_explicit = any("next" in s for s in steps)
    if has_explicit:
        for step in steps:
            graph[step.get("id")] = set(step.get("next", []))
    else:
        for index in range(len(ids) - 1):
            graph[ids[index]].add(ids[index + 1])
    return graph


def _has_cycle(graph: dict) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}

    def visit(node):
        color[node] = GRAY
        for neighbor in graph.get(node, ()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                return True
            if color[neighbor] == WHITE and visit(neighbor):
                return True
        color[node] = BLACK
        return False

    return any(color[node] == WHITE and visit(node) for node in graph)


def build_workflow_registry(root: Path) -> dict:
    """Build the workflow registry from knowledge/workflows/*.json."""
    agent_registry = build_agent_registry(root)
    known_agent_keys = {a["id"].split(":", 1)[1] for a in agent_registry["agents"]}
    known_allowed_actions = {a["id"].split(":", 1)[1]: set(a["allowedActions"]) for a in agent_registry["agents"]}

    entries = []
    for source in _load_workflow_sources(root):
        steps = source.get("steps", [])
        approval_gates = [s["id"] for s in steps if s.get("requiresApproval")]
        validation_gates = [s["id"] for s in steps if s.get("action") in VALIDATION_ACTIONS]
        graph = _step_graph(steps)

        entries.append({
            "id": source.get("id", ""),
            "name": source.get("name", ""),
            "description": source.get("description", ""),
            "triggerIntent": source.get("triggerIntent", ""),
            "requiredInputs": source.get("requiredInputs", []),
            "steps": steps,
            "knowledgeRetrievalStep": next((s["id"] for s in steps if s.get("action") == "search_knowledge"), None),
            "approvalGates": approval_gates,
            "validationGates": validation_gates,
            "completionCriteria": source.get("completionCriteria", []),
            "failureBehavior": source.get("failureBehavior", ""),
            "allowedActions": source.get("allowedActions", []),
            "forbiddenActions": source.get("forbiddenActions", []),
            "outputArtifacts": source.get("outputArtifacts", []),
            "memorySuggestionPolicy": source.get("memorySuggestionPolicy", ""),
            "auditPolicy": source.get("auditPolicy", ""),
            "sourcePath": source.get("_sourcePath", ""),
            "metadata": {
                "hasCycle": _has_cycle(graph),
                "unknownAgentRefs": sorted({s.get("agent") for s in steps} - known_agent_keys),
                "unsafeActionRefs": sorted(
                    f"{s.get('agent')}:{s.get('action')}"
                    for s in steps
                    if s.get("agent") in known_allowed_actions
                    and s.get("action") not in known_allowed_actions[s.get("agent")]
                ),
            },
        })

    entries.sort(key=lambda w: w["id"])

    by_intent: dict = {}
    for entry in entries:
        by_intent[entry["triggerIntent"]] = entry["id"]

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "workflows": entries,
        "stats": {
            "totalWorkflows": len(entries),
            "byIntent": by_intent,
        },
    }


def validate_workflow_registry(registry: object) -> tuple:
    """Structural validation. Returns (failures, warnings)."""
    failures: list = []
    warnings: list = []

    if not isinstance(registry, dict):
        return ["workflow registry root must be an object"], warnings

    if registry.get("schemaVersion") != SCHEMA_VERSION:
        failures.append(f"unsupported schemaVersion: {registry.get('schemaVersion')}")

    workflows = registry.get("workflows")
    if not isinstance(workflows, list):
        failures.append("workflows must be a list")
        return failures, warnings

    seen_ids = set()
    for workflow in workflows:
        wid = workflow.get("id", "")
        missing = [f for f in REQUIRED_WORKFLOW_FIELDS if f not in workflow]
        if missing:
            failures.append(f"{wid}: missing required fields: {missing}")
        if not wid:
            failures.append("workflow missing id")
        elif wid in seen_ids:
            failures.append(f"duplicate workflow id: {wid}")
        else:
            seen_ids.add(wid)

        steps = workflow.get("steps", [])
        for step in steps:
            step_missing = [f for f in REQUIRED_STEP_FIELDS if f not in step]
            if step_missing:
                failures.append(f"{wid}: step {step.get('id')} missing fields: {step_missing}")

        if not workflow.get("approvalGates"):
            failures.append(f"{wid}: workflow has no approval gates")

        metadata = workflow.get("metadata", {})
        if metadata.get("hasCycle"):
            failures.append(f"{wid}: cyclic step dependency detected")
        if metadata.get("unknownAgentRefs"):
            failures.append(f"{wid}: unknown agent references: {metadata['unknownAgentRefs']}")
        if metadata.get("unsafeActionRefs"):
            failures.append(f"{wid}: action not in agent's allowedActions: {metadata['unsafeActionRefs']}")

        if wid and wid.split(":", 1)[-1] not in WORKFLOW_TYPES:
            warnings.append(f"{wid}: workflow type not in the standard list")

    return failures, warnings


def compare_registries_ignoring_generated_at(current: dict, saved: dict) -> bool:
    left = json.loads(json.dumps(current))
    right = json.loads(json.dumps(saved))
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    return left == right
