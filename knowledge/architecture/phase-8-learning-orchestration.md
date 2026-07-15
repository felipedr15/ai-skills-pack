# Phase 8 Continuous Learning and Agent Orchestration Architecture

## Purpose

Add a planning, tracking, and suggestion layer on top of Phases 1-7: classify a task, select a
workflow and agent roles, retrieve relevant knowledge, track a local work session through the
plan, and produce memory/knowledge-gap/feedback suggestions that a human must explicitly approve.
This layer never executes work itself — it plans and tracks; a human (or a future, separately
scoped execution engine) does the work.

## Package

`scripts/orchestration/`: `models.py`, `registry.py`, `workflow.py`, `router.py`, `planner.py`,
`session.py`, `approvals.py`, `memory_suggestions.py`, `feedback.py`, `knowledge_gaps.py`,
`freshness.py`, `audit.py`, `render.py`, `validate.py`, `utils.py`. Mirrors the structure of
`scripts/knowledge_graph/` and `scripts/semantic_discovery/`.

## Reuse, Not Duplication

- Knowledge retrieval → `ai_os_service.service.AiOsService.search`, itself built on
  `semantic_discovery.query/rank/traverse`. No second search engine exists.
- Path confinement and secret redaction → `ai_os_service.permissions`.
- Memory file creation (on suggestion approval only) → `scripts/memory-add.py`'s `create_record`,
  imported the same way `validate-all.py` imports `index-repository.py`.
- Markdown front matter → `knowledge_graph.utils.parse_front_matter`.

## Agent Registry

`generated/agent-registry.json` / `.md`, built from `agents/*.md` + `agents.json`. Ten agents
exist in this repository; there is no separate `support` agent, so the registry is built only from
what exists. Role mapping (an explicit adaptation of the spec's illustrative role list to this
repository's actual agent docs):

| Agent doc | Role |
|---|---|
| planner | planning |
| architect | architecture |
| builder | building |
| reviewer | review |
| qa | quality-assurance |
| documentation-writer | documentation |
| security-reviewer | security |
| deployment-manager | release |
| project-manager | project-management |
| researcher | research |

Every agent's `forbiddenActions` always includes `git_commit, git_push, git_merge, git_tag,
arbitrary_shell_execution, secret_access, network_access, automatic_approval` — a universal set
derived from `AGENTS.md` / `SECURITY.md`, not something any single agent doc opts out of.

## Workflow Registry

`generated/workflow-registry.json` / `.md`, compiled from hand-authored sources in
`knowledge/workflows/*.json` (one per required workflow type). Every workflow has at least one
approval gate; step actions are checked against the acting agent's `allowedActions`; step
dependencies are checked for cycles.

## Task Classification

`orchestration.router.classify_task` — deterministic keyword/regex signal tables per intent (12
intents including `unknown`), fixed intent priority order for tie-breaking, confidence = matched
signal count saturating at 3 (rounded to 2dp). No external model, no randomness.

## Planning

`orchestration.planner.create_plan` composes classification + workflow registry + agent registry +
knowledge retrieval (via the existing search engine) into a single structured plan. Performs no
execution.

## Storage Split (the key architectural decision)

| Data | Location | Rationale |
|---|---|---|
| Agent registry, workflow registry, knowledge-health report | `generated/*.json` + `.md` | Deterministic, derived from committed docs, safe to commit, `--check`-able like every other generated artifact. |
| Sessions, approvals, memory suggestions, feedback, audit log | `.ai-os/{sessions,approvals,memory-suggestions,feedback,audit}/` | Local runtime state — the Phase 7 precedent (`.ai-os/` is git-ignored). Never embedded in committed `generated/` artifacts. |

`generated/knowledge-health.json` is built with `include_live=False` (deterministic, repo-only
categories) so it stays stable across machines; the CLI's `knowledge-health` / `knowledge-gaps`
commands and the dashboard's live endpoint call `include_live=True`, which additionally overlays
session/feedback signal categories computed at request time from local `.ai-os/` state — never
written back into the committed artifact.

## Session Lifecycle

Statuses: `planned, approved, active, blocked, validation, completed, failed, cancelled, archived`.
Transitions are validated against an explicit table (`orchestration.SESSION_TRANSITIONS`); there is
no way to skip from `planned` to `completed` directly. The CLI's `session complete` requires the
session already be in `validation` status (reached via `session validate`), matching the manual
acceptance scenario's "record a validation result, then complete" flow.

## Approval Engine

`.ai-os/approvals/approvals.json`. Every approval starts `pending`; only an explicit
`ai-os.py approval approve <id>` moves it to `approved`. `orchestration.approvals.is_approved` is
the only gate memory-suggestion promotion checks — there is no auto-approve path anywhere in the
codebase.

## Memory Suggestions

Generated automatically when a session with at least one passed validation is completed
(`session complete`), which also auto-requests a `permanent-memory` approval. Approving a
suggestion is the only code path in Phase 8 that writes into `memory/`, and it is blocked until
that specific approval is granted.

## Knowledge Gaps and Freshness

`orchestration.knowledge_gaps.build_knowledge_health` scores 6-8 categories (graph integrity,
project/skill documentation coverage, memory linkage, workflow governance, freshness, and — live
view only — session health and feedback signal) on a 0-100 heuristic scale, with raw counts and
recommendations. `orchestration.freshness` only tracks documents that opt in by declaring
`owner` / `lastReviewed` / `reviewIntervalDays` / `nextReview` front matter — most Phase 1-7 docs
predate this convention, so an empty `review-due` result is expected, not a bug.

## Audit Trail

`.ai-os/audit/audit-<n>.log`, JSONL, hash-chained (`hash = sha256(prevHash + canonical_json(event))`),
rotated past `AUDIT_MAX_ENTRIES_PER_FILE` entries. `orchestration.audit.validate_chain` recomputes
and compares hashes to detect tampering.

## Security Boundaries

No Git operations, no arbitrary shell execution, no network access, no telemetry, no automatic
approvals, no automatic writes to `memory/` outside the single approved-suggestion path, secrets
redacted via the existing `ai_os_service.permissions` patterns before any local storage write.

## Non-Goals

Phase 8 does not execute workflow steps, does not call an LLM, does not retrain or fine-tune
anything, and does not expose approval-mutating operations via MCP.

[Back to AI OS](../../README.md)
