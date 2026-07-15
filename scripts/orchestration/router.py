"""Deterministic local task intent classification (Phase 8, Part 3).

No external model, no randomness, no network access. Every signal is a
plain-text/regex match against the task description, so results are fully
explainable via `matchedSignals`.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import INTENT_WORKFLOW, INTENTS
from .utils import content_hash
from .workflow import build_workflow_registry

# Confidence saturates at this many distinct matched signals (deliberately
# small — this is a keyword heuristic, not a precise probability).
CONFIDENCE_SATURATION = 3

# intent -> [(human-readable signal name, compiled pattern), ...]
_SIGNALS = {
    "bug-fix": [
        ("mentions fixing", re.compile(r"\bfix(e[sd]|ing)?\b", re.I)),
        ("mentions a bug", re.compile(r"\bbugs?\b", re.I)),
        ("mentions broken behavior", re.compile(r"\bbroken\b", re.I)),
        ("mentions something not working", re.compile(r"\b(is|are|does(n'?t)?|do(es)? not)\s+not\s+\w+", re.I)),
        ("mentions an error", re.compile(r"\berrors?\b", re.I)),
        ("mentions an issue", re.compile(r"\bissues?\b", re.I)),
        ("mentions a defect", re.compile(r"\bdefects?\b", re.I)),
        ("mentions failure", re.compile(r"\bfail(s|ed|ing|ure)?\b", re.I)),
    ],
    "troubleshooting": [
        ("asks to troubleshoot", re.compile(r"\btroubleshoot(ing)?\b", re.I)),
        ("asks to diagnose", re.compile(r"\bdiagnos(e|is|ing)\b", re.I)),
        ("asks to investigate", re.compile(r"\binvestigat(e|ion|ing)\b", re.I)),
        ("asks why something happens", re.compile(r"\bwhy\s+(is|does|do|are)\b", re.I)),
        ("mentions debugging", re.compile(r"\bdebug(ging)?\b", re.I)),
        ("mentions root cause", re.compile(r"\broot\s+cause\b", re.I)),
    ],
    "documentation": [
        ("mentions documentation", re.compile(r"\bdocument(ation)?\b", re.I)),
        ("mentions a README", re.compile(r"\breadme\b", re.I)),
        ("asks to write docs", re.compile(r"\bwrite\s+(the\s+)?docs?\b", re.I)),
        ("mentions a docstring", re.compile(r"\bdocstring\b", re.I)),
        ("asks to update docs", re.compile(r"\bupdate\s+(the\s+)?docs?\b", re.I)),
    ],
    "release": [
        ("mentions a release", re.compile(r"\breleas(e|ing)\b", re.I)),
        ("mentions publishing", re.compile(r"\bpublish(ing)?\b", re.I)),
        ("mentions packaging", re.compile(r"\bpackag(e|ing)\b", re.I)),
        ("mentions a version bump", re.compile(r"\bversion\s+bump\b", re.I)),
        ("mentions a changelog", re.compile(r"\bchangelog\b", re.I)),
        ("mentions shipping", re.compile(r"\bship(ping)?\b", re.I)),
    ],
    "validation": [
        ("asks to validate", re.compile(r"\bvalidat(e|ion|ing)\b", re.I)),
        ("asks to test", re.compile(r"\btest(s|ing)?\b", re.I)),
        ("asks to verify", re.compile(r"\bverif(y|ication|ying)\b", re.I)),
        ("asks to check", re.compile(r"\bcheck\s+that\b", re.I)),
        ("mentions QA", re.compile(r"\bqa\b", re.I)),
    ],
    "research": [
        ("asks to research", re.compile(r"\bresearch\b", re.I)),
        ("asks to explore", re.compile(r"\bexplore\b", re.I)),
        ("asks to compare options", re.compile(r"\bcompare\b", re.I)),
        ("asks to evaluate options", re.compile(r"\bevaluat(e|ing)\s+options?\b", re.I)),
        ("asks to look into something", re.compile(r"\blook\s+into\b", re.I)),
    ],
    "project-planning": [
        ("mentions onboarding", re.compile(r"\bonboard(ing)?\b", re.I)),
        ("mentions a new project", re.compile(r"\bnew\s+project\b", re.I)),
        ("mentions scaffolding", re.compile(r"\bscaffold(ing)?\b", re.I)),
        ("mentions setting up a project", re.compile(r"\bset\s?up\s+(a\s+)?project\b", re.I)),
        ("mentions kicking off work", re.compile(r"\bkick(ing)?\s?off\b", re.I)),
    ],
    "incident-response": [
        ("mentions an incident", re.compile(r"\bincident\b", re.I)),
        ("mentions an outage", re.compile(r"\boutage\b", re.I)),
        ("mentions a system being down", re.compile(r"\b(is|are)\s+down\b", re.I)),
        ("mentions a production issue", re.compile(r"\bproduction\s+issue\b", re.I)),
        ("mentions urgency", re.compile(r"\burgent(ly)?\b", re.I)),
        ("mentions a critical failure", re.compile(r"\bcritical\b", re.I)),
        ("mentions a severity level", re.compile(r"\bsev[\s-]?1\b", re.I)),
    ],
    "knowledge-maintenance": [
        ("mentions stale content", re.compile(r"\bstale\b", re.I)),
        ("mentions outdated content", re.compile(r"\boutdated\b", re.I)),
        ("mentions a knowledge gap", re.compile(r"\bknowledge\s+gap\b", re.I)),
        ("asks to refresh docs", re.compile(r"\brefresh\s+(the\s+)?docs?\b", re.I)),
        ("mentions a gap", re.compile(r"\bgap\s+in\b", re.I)),
    ],
    "procedure-creation": [
        ("mentions a procedure", re.compile(r"\bprocedures?\b", re.I)),
        ("mentions a runbook", re.compile(r"\brunbooks?\b", re.I)),
        ("mentions a playbook", re.compile(r"\bplaybooks?\b", re.I)),
        ("asks to write a guide", re.compile(r"\bwrite\s+a\s+guide\b", re.I)),
        ("mentions a how-to", re.compile(r"\bhow[\s-]to\b", re.I)),
    ],
    "feature-development": [
        ("mentions adding something", re.compile(r"\badd(ing)?\b", re.I)),
        ("mentions implementing something", re.compile(r"\bimplement(ing)?\b", re.I)),
        ("mentions a new feature", re.compile(r"\bnew\s+feature\b", re.I)),
        ("mentions building something", re.compile(r"\bbuild(ing)?\b", re.I)),
        ("mentions creating something", re.compile(r"\bcreat(e|ing)\s+a\b", re.I)),
        ("mentions introducing something", re.compile(r"\bintroduc(e|ing)\b", re.I)),
    ],
}

# Fixed evaluation order used for deterministic tie-breaking: earlier wins.
_INTENT_PRIORITY = [i for i in INTENTS if i != "unknown"]


def _match_signals(task: str, intent: str) -> list:
    return [name for name, pattern in _SIGNALS.get(intent, []) if pattern.search(task)]


def _score(task: str) -> dict:
    """Return {intent: (matched_count, [signal names])} for every known intent."""
    return {intent: (len(_match_signals(task, intent)), _match_signals(task, intent)) for intent in _INTENT_PRIORITY}


def _confidence(matched_count: int) -> float:
    return round(min(1.0, matched_count / CONFIDENCE_SATURATION), 2)


def _workflow_agents(root: Path, workflow_id: str) -> list:
    if not workflow_id:
        return []
    registry = build_workflow_registry(root)
    for workflow in registry.get("workflows", []):
        if workflow["id"] == workflow_id:
            seen = []
            for step in workflow.get("steps", []):
                if step["agent"] not in seen:
                    seen.append(step["agent"])
            return [f"agent:{a}" for a in seen]
    return []


def _workflow_has_approval_gate(root: Path, workflow_id: str) -> bool:
    if not workflow_id:
        return True  # conservative default: require approval when uncertain
    registry = build_workflow_registry(root)
    for workflow in registry.get("workflows", []):
        if workflow["id"] == workflow_id:
            return bool(workflow.get("approvalGates"))
    return True


def classify_task(root: Path, task: str, *, project: str | None = None,
                   source_path: str | None = None,
                   requested_workflow: str | None = None) -> dict:
    """Classify a task description into a supported intent.

    Deterministic: same inputs always produce the same output. `root` is
    only used to inspect the workflow registry for approval-gate and
    suggested-agent information — no filesystem writes occur here.
    """
    task = (task or "").strip()
    warnings: list = []

    if not task:
        return {
            "taskId": f"task-{content_hash('')}",
            "intent": "unknown",
            "confidence": 0.0,
            "matchedSignals": [],
            "suggestedWorkflow": None,
            "suggestedAgents": [],
            "knowledgeQueries": [],
            "approvalRequired": True,
            "warnings": ["empty task description"],
        }

    scores = _score(task)
    best_intent = "unknown"
    best_count = 0
    best_signals: list = []
    for intent in _INTENT_PRIORITY:  # fixed order => stable tie-break (first max wins)
        count, signals = scores[intent]
        if count > best_count:
            best_intent, best_count, best_signals = intent, count, signals

    if best_count == 0:
        best_intent = "unknown"
        warnings.append("no matching signals found for any known intent; defaulting to unknown")

    confidence = _confidence(best_count) if best_intent != "unknown" else 0.0
    if 0 < confidence < 0.5:
        warnings.append(f"low confidence classification ({confidence})")

    if requested_workflow:
        suggested_workflow = requested_workflow
        warnings.append(f"workflow overridden by caller: {requested_workflow}")
    else:
        suggested_workflow = INTENT_WORKFLOW.get(best_intent)

    suggested_agents = _workflow_agents(root, suggested_workflow) if suggested_workflow else []
    approval_required = _workflow_has_approval_gate(root, suggested_workflow) if suggested_workflow else True

    knowledge_queries = [task]
    if project and project not in knowledge_queries:
        knowledge_queries.append(project)
    if source_path and source_path not in knowledge_queries:
        knowledge_queries.append(source_path)

    return {
        "taskId": f"task-{content_hash(task)}",
        "intent": best_intent,
        "confidence": confidence,
        "matchedSignals": best_signals,
        "suggestedWorkflow": suggested_workflow,
        "suggestedAgents": suggested_agents,
        "knowledgeQueries": knowledge_queries,
        "approvalRequired": approval_required,
        "warnings": warnings,
    }
