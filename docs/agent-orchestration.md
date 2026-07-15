# Agent Orchestration (Phase 8)

## Agent Registry

`generated/agent-registry.json` / `.md`, built from `agents/*.md` and `agents.json` by
`scripts/generate-agent-registry.py`. Each entry has: `id`, `name`, `role`, `description`,
`capabilities`, `inputs`, `outputs`, `allowedActions`, `forbiddenActions`, `requiredSkills`,
`validationRequirements`, `sourcePath`, `metadata`.

Every agent's `forbiddenActions` includes Git mutation, arbitrary shell execution, secret access,
network access, and automatic approval — regardless of role. `allowedActions` is a small,
role-specific list (e.g. `builder` → `modify_files`; `qa` → `run_approved_validation`) that
workflow steps are validated against.

```text
python scripts/ai-os.py workflow list
python scripts/ai-os.py workflow show workflow:bug-fix
```

(Agent listing is via the registry file directly, the dashboard's Agents page, or the
`list_agents` / `get_agent` MCP tools — there is no separate `ai-os.py agent` command since the
registry is small and static.)

## Workflow Registry

`generated/workflow-registry.json` / `.md`, compiled from `knowledge/workflows/*.json`
(see [knowledge/workflows/README.md](../knowledge/workflows/README.md) for the source format) by
`scripts/generate-workflow-registry.py`. Eight required workflow types: feature-development,
bug-fix, documentation-update, release-preparation, incident-response, knowledge-maintenance,
project-onboarding, procedure-creation.

Each workflow declares ordered steps (`id`, `agent`, `action`, `requiresApproval`), approval gates,
validation gates, completion criteria, failure behavior, allowed/forbidden actions, output
artifacts, a memory-suggestion policy, and an audit policy.

## Task Classification

```text
python scripts/ai-os.py classify "<task>" [--project P] [--workflow override]
```

Deterministic keyword/regex matching against 12 supported intents (feature-development, bug-fix,
troubleshooting, documentation, release, validation, research, project-planning,
incident-response, knowledge-maintenance, procedure-creation, unknown). Confidence saturates at 3
matched signals — a heuristic, not a precise probability. `unknown` intent always requires
approval before proceeding.

## Planning

```text
python scripts/ai-os.py plan "<task>" [--project P] [--workflow override] [--json] [--limit N]
    [--explain] [--no-memory] [--no-history]
```

Produces: task summary, selected workflow and agents, a knowledge retrieval plan and its results
(via the existing semantic discovery engine — see
[Phase 4 Semantic Discovery](../knowledge/architecture/phase-4-semantic-discovery.md)), ordered
steps, approval gates, validation requirements, expected output artifacts, and risks/warnings.
`--explain` prints matched signals, full steps, and the top retrieved knowledge items.

## Sessions

```text
python scripts/ai-os.py session start "<task>"
python scripts/ai-os.py session validate <id> --name X --status pass|fail [--detail "..."]
python scripts/ai-os.py session complete <id>
python scripts/ai-os.py session archive <id>
python scripts/ai-os.py session list [--status S]
python scripts/ai-os.py session show <id>
```

Sessions live in `.ai-os/sessions/` (local, git-ignored). Status transitions are validated against
a fixed table — see [Phase 8 Architecture](../knowledge/architecture/phase-8-learning-orchestration.md#session-lifecycle).
`session complete` requires the session already be in `validation` status.

## MCP and Dashboard

Fifteen new read-only MCP tools (`plan_task`, `classify_task`, `list_workflows`, `get_workflow`,
`list_agents`, `get_agent`, `list_sessions`, `get_session`, `list_pending_approvals`,
`list_memory_suggestions`, `get_knowledge_health`, `list_review_due`, `list_feedback`,
`get_audit_summary`) and eight new `ai-os://` resources. No approval-mutating tool is exposed.
The dashboard adds Orchestration Overview, Workflows, Agents, Sessions, Memory Suggestions,
Knowledge Health, Feedback, and Audit pages.

[Back to AI OS](../README.md)
