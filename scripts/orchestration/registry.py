"""Agent registry builder (Phase 8, Part 1).

Builds `generated/agent-registry.json` / `.md` from the existing agent
documentation (`agents/*.md` + `agents.json`). Does not invent agents beyond
what already exists in the repository.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import GENERATOR, SCHEMA_VERSION, UNIVERSAL_FORBIDDEN_ACTIONS

# agents.json id -> Phase 8 role category. Adapted to the 10 agents that
# actually exist in this repository (see
# knowledge/architecture/phase-8-learning-orchestration.md for the rationale;
# there is no separate "support" agent doc, so it is intentionally omitted).
ROLE_MAP = {
    "planner": "planning",
    "architect": "architecture",
    "builder": "building",
    "reviewer": "review",
    "qa": "quality-assurance",
    "documentation-writer": "documentation",
    "security-reviewer": "security",
    "deployment-manager": "release",
    "project-manager": "project-management",
    "researcher": "research",
}

# Static, per-agent allowed actions — intentionally conservative and scoped
# to what each role's markdown doc actually describes it doing. These never
# include Git mutation, arbitrary execution, or secret access (see
# UNIVERSAL_FORBIDDEN_ACTIONS).
ALLOWED_ACTIONS = {
    "planner": ["search_knowledge", "create_plan", "classify_task"],
    "architect": ["design_components", "create_plan"],
    "builder": ["modify_files"],
    "reviewer": ["review_diff"],
    "qa": ["run_approved_validation"],
    "documentation-writer": ["create_memory_suggestion", "update_documentation"],
    "security-reviewer": ["assess_security_risk"],
    "deployment-manager": ["prepare_deployment_guidance"],
    "project-manager": ["coordinate_approval_gates"],
    "researcher": ["search_knowledge", "gather_evidence"],
}

SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _parse_sections(text: str) -> dict:
    """Split a Phase-1-7 agent markdown doc into {lowercased header: body}."""
    normalized = text.replace("\r\n", "\n")
    matches = list(SECTION_PATTERN.finditer(normalized))
    sections: dict = {}
    for index, match in enumerate(matches):
        header = match.group(1).strip().lower()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        sections[header] = normalized[start:end].strip()
    return sections


def _split_items(text: str) -> list:
    """Deterministically split a prose sentence into short item phrases."""
    if not text:
        return []
    cleaned = text.strip().rstrip(".")
    if not cleaned:
        return []
    # Bullet list (Completion Checklist style)
    bullet_lines = [line[2:].strip() for line in cleaned.splitlines() if line.strip().startswith("- ")]
    if bullet_lines:
        return bullet_lines
    cleaned = re.sub(r"\band\s+", "", cleaned)
    parts = [p.strip() for p in re.split(r",\s*|;\s*", cleaned) if p.strip()]
    return parts


def _load_agents_json(root: Path) -> list:
    path = root / "agents.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("agents", [])


def _normalize_source_path(value: str) -> str:
    return value.replace("\\", "/")


def build_agent_registry(root: Path) -> dict:
    """Build the agent registry from agents.json + agents/*.md."""
    entries = []
    for record in _load_agents_json(root):
        agent_key = record.get("id", "")
        source_path = _normalize_source_path(record.get("path", ""))
        doc_path = root / source_path
        sections = _parse_sections(doc_path.read_text(encoding="utf-8")) if doc_path.is_file() else {}

        capabilities = _split_items(sections.get("responsibilities", ""))
        inputs = record.get("inputs") or _split_items(sections.get("required inputs", ""))
        outputs = record.get("outputs") or _split_items(sections.get("expected outputs", ""))
        validation_requirements = _split_items(sections.get("completion checklist", ""))
        role = ROLE_MAP.get(agent_key, "unassigned")

        entries.append({
            "id": f"agent:{agent_key}",
            "name": record.get("name", agent_key),
            "role": role,
            "description": record.get("description", ""),
            "capabilities": capabilities,
            "inputs": inputs,
            "outputs": outputs,
            "allowedActions": ALLOWED_ACTIONS.get(agent_key, []),
            "forbiddenActions": list(UNIVERSAL_FORBIDDEN_ACTIONS),
            "requiredSkills": list(record.get("skills", [])),
            "validationRequirements": validation_requirements,
            "sourcePath": source_path,
            "metadata": {
                "handoffTo": record.get("handoffTo"),
                "rolePurpose": sections.get("role purpose", ""),
            },
        })

    entries.sort(key=lambda a: a["id"])

    by_role: dict = {}
    for entry in entries:
        by_role[entry["role"]] = by_role.get(entry["role"], 0) + 1

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "agents": entries,
        "stats": {
            "totalAgents": len(entries),
            "byRole": by_role,
        },
    }


def validate_agent_registry(registry: object) -> tuple:
    """Structural validation. Returns (failures, warnings)."""
    failures: list = []
    warnings: list = []

    if not isinstance(registry, dict):
        return ["agent registry root must be an object"], warnings

    if registry.get("schemaVersion") != SCHEMA_VERSION:
        failures.append(f"unsupported schemaVersion: {registry.get('schemaVersion')}")

    agents = registry.get("agents")
    if not isinstance(agents, list):
        failures.append("agents must be a list")
        return failures, warnings

    seen_ids = set()
    for agent in agents:
        if not isinstance(agent, dict):
            failures.append("agent entry must be an object")
            continue
        agent_id = agent.get("id", "")
        if not agent_id:
            failures.append("agent missing id")
        elif agent_id in seen_ids:
            failures.append(f"duplicate agent id: {agent_id}")
        else:
            seen_ids.add(agent_id)

        if not agent.get("sourcePath"):
            failures.append(f"{agent_id}: missing sourcePath")
        elif agent["sourcePath"].startswith("/") or ".." in agent["sourcePath"] or "\\" in agent["sourcePath"]:
            failures.append(f"{agent_id}: unsafe sourcePath {agent['sourcePath']!r}")

        forbidden = set(agent.get("forbiddenActions", []))
        missing_forbidden = set(UNIVERSAL_FORBIDDEN_ACTIONS) - forbidden
        if missing_forbidden:
            failures.append(f"{agent_id}: missing required forbidden actions: {sorted(missing_forbidden)}")

        allowed = set(agent.get("allowedActions", []))
        unsafe_allowed = allowed & set(UNIVERSAL_FORBIDDEN_ACTIONS)
        if unsafe_allowed:
            failures.append(f"{agent_id}: allowedActions grants forbidden capability: {sorted(unsafe_allowed)}")

        if not agent.get("requiredSkills"):
            warnings.append(f"{agent_id}: no required skills listed")

    if not agents:
        warnings.append("agent registry has no agents with an assigned workflow")

    return failures, warnings


def compare_registries_ignoring_generated_at(current: dict, saved: dict) -> bool:
    left = json.loads(json.dumps(current))
    right = json.loads(json.dumps(saved))
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    return left == right
