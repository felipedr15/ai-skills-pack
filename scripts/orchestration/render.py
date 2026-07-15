"""JSON + Markdown renderers for orchestration generated artifacts."""
from __future__ import annotations

import json


def render_json(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def render_agent_registry_md(registry: dict) -> str:
    lines = [
        "# Generated Agent Registry",
        "",
        "> Generated from `agents/*.md` and `agents.json`. This file is not a source of truth —",
        "> edit the agent markdown docs instead and regenerate.",
        "",
        f"Generated at: {registry.get('generatedAt', '')}",
        f"Generator: {registry.get('generator', '')}",
        f"Total agents: {registry.get('stats', {}).get('totalAgents', 0)}",
        "",
        "## Agents by Role",
        "",
    ]
    for role, count in sorted(registry.get("stats", {}).get("byRole", {}).items()):
        lines.append(f"- {role}: {count}")
    lines.extend(["", "## Agents", ""])
    for agent in registry.get("agents", []):
        lines.append(f"### {agent['name']} (`{agent['id']}`)")
        lines.append("")
        lines.append(f"- Role: {agent.get('role', '')}")
        lines.append(f"- Description: {agent.get('description', '')}")
        lines.append(f"- Source: `{agent.get('sourcePath', '')}`")
        lines.append(f"- Required skills: {', '.join(agent.get('requiredSkills', [])) or 'none'}")
        lines.append(f"- Allowed actions: {', '.join(agent.get('allowedActions', [])) or 'none'}")
        lines.append(f"- Forbidden actions: {', '.join(agent.get('forbiddenActions', [])) or 'none'}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_workflow_registry_md(registry: dict) -> str:
    lines = [
        "# Generated Workflow Registry",
        "",
        "> Generated from `knowledge/workflows/*.json`. This file is not a source of truth —",
        "> edit the workflow JSON sources instead and regenerate.",
        "",
        f"Generated at: {registry.get('generatedAt', '')}",
        f"Generator: {registry.get('generator', '')}",
        f"Total workflows: {registry.get('stats', {}).get('totalWorkflows', 0)}",
        "",
        "## Workflows",
        "",
    ]
    for workflow in registry.get("workflows", []):
        lines.append(f"### {workflow['name']} (`{workflow['id']}`)")
        lines.append("")
        lines.append(f"- Description: {workflow.get('description', '')}")
        lines.append(f"- Trigger intent: {workflow.get('triggerIntent', '')}")
        lines.append(f"- Source: `{workflow.get('sourcePath', '')}`")
        lines.append(f"- Approval gates: {', '.join(workflow.get('approvalGates', [])) or 'none'}")
        lines.append(f"- Validation gates: {', '.join(workflow.get('validationGates', [])) or 'none'}")
        lines.append("- Steps:")
        for step in workflow.get("steps", []):
            approval = " (requires approval)" if step.get("requiresApproval") else ""
            lines.append(f"  - `{step['id']}` — {step['agent']}: {step['action']}{approval}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_knowledge_health_md(report: dict) -> str:
    lines = [
        "# Generated Knowledge Health Report",
        "",
        "> Generated from repository state. Not a source of truth — a diagnostic snapshot.",
        "> Scores are explainable heuristics, not precise measurements.",
        "",
        f"Generated at: {report.get('generatedAt', '')}",
        f"Generator: {report.get('generator', '')}",
        f"Overall health score: {report.get('overallScore', 0)} / 100",
        "",
        "## Category Scores",
        "",
    ]
    for category, score in sorted(report.get("categoryScores", {}).items()):
        lines.append(f"- {category}: {score} / 100")
    lines.extend(["", "## Gaps", ""])
    for gap in report.get("gaps", []):
        lines.append(f"- [{gap.get('severity', 'info')}] {gap.get('category', '')}: {gap.get('description', '')}")
    lines.extend(["", "## Recommendations", ""])
    for rec in report.get("recommendations", []):
        lines.append(f"- {rec}")
    lines.append("")
    return "\n".join(lines) + "\n"
