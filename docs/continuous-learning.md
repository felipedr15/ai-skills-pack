# Continuous Learning (Phase 8)

How AI OS turns a task description into a tracked, human-approved unit of work — and how it
learns from what happened afterward.

## The Loop

1. **Classify** — `ai-os.py classify "<task>"` deterministically assigns an intent (bug-fix,
   feature-development, documentation, release, incident-response, ...) with an explainable
   confidence score and matched signals. No external model, no randomness.
2. **Plan** — `ai-os.py plan "<task>" --explain` selects a workflow, the agent roles it involves,
   and retrieves relevant knowledge via the existing semantic discovery engine. Nothing is
   executed.
3. **Track** — `ai-os.py session start "<task>"` records a local session snapshot of the plan,
   requests a plan approval if the workflow requires one, and moves through
   `session validate` → `session complete` → `session archive`.
4. **Learn** — completing a session with at least one passed validation generates a pending
   memory suggestion and requests a permanent-memory approval. Nothing becomes a real memory file
   until that approval is explicitly granted.
5. **Detect gaps** — `ai-os.py knowledge-health` / `knowledge-gaps` score the current state of the
   knowledge base and surface concrete, explainable gaps. `ai-os.py review-due` lists documents
   whose freshness metadata says they need another look.
6. **Feedback** — `ai-os.py feedback add` records a correction or observation locally; repeated
   corrections against the same target become a knowledge-gap signal.

## What This Is Not

Phase 8 is a planning and tracking layer, not an autonomous agent. It never modifies source files,
never runs Git commands, never executes arbitrary code, and never calls out to a network service.
Every consequential action — approving a plan, promoting a memory suggestion, resolving feedback —
requires an explicit human command.

## See Also

- [Agent Orchestration](agent-orchestration.md) — agent registry, workflow registry, planning.
- [Memory Approval](memory-approval.md) — sessions, approvals, memory suggestions.
- [Knowledge Health](knowledge-health.md) — gap detection and freshness.
- [Feedback and Audit](feedback-and-audit.md) — feedback capture and the audit trail.
- [Phase 8 Architecture](../knowledge/architecture/phase-8-learning-orchestration.md)

[Back to AI OS](../README.md)
