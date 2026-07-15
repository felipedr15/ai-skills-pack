# Workflows

Hand-authored workflow definitions consumed by `scripts/orchestration/workflow.py` to build
`generated/workflow-registry.json` / `.md`. These JSON files are source of truth; the generated
registry is derived data.

## Format

Each file defines one workflow:

```json
{
  "id": "workflow:bug-fix",
  "name": "Bug Fix",
  "description": "...",
  "triggerIntent": "bug-fix",
  "requiredInputs": ["..."],
  "steps": [
    {"id": "retrieve-context", "agent": "planner", "action": "search_knowledge", "requiresApproval": false}
  ],
  "completionCriteria": ["..."],
  "failureBehavior": "...",
  "allowedActions": ["..."],
  "forbiddenActions": ["..."],
  "outputArtifacts": ["..."],
  "memorySuggestionPolicy": "...",
  "auditPolicy": "..."
}
```

`agent` must be an id from `agents.json` (e.g. `planner`, `builder`, `qa`); `action` must be one of
the agent's `allowedActions` in `generated/agent-registry.json` — the workflow build fails
otherwise. Steps run in list order unless a step declares an explicit `"next": ["other-step-id"]`
array; cyclic `next` references are rejected.

## Required Workflow Types

`feature-development`, `bug-fix`, `documentation-update`, `release-preparation`,
`incident-response`, `knowledge-maintenance`, `project-onboarding`, `procedure-creation`.

## Regenerate

```text
python scripts/generate-workflow-registry.py
python scripts/generate-workflow-registry.py --check
```

[Back to AI OS](../../README.md)
