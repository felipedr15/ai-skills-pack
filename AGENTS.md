# Shared Agent Instructions

## Repository Purpose
AI OS coordinates reusable skills, specifications, project memory, roles, prompts, standards, and validation across AI tools.

## Required Reading Order
1. `README.md`
2. `AGENTS.md`
3. `WORKFLOW.md`
4. `ARCHITECTURE.md` when architecture is relevant
5. `skills.json`
6. `agents.json`
7. `prompts.json`
8. Applicable `.agent/skills/**/SKILL.md` files
9. Active specification files
10. `HANDOFF.md` when present
11. `decisions.md` when present
12. `SESSION.md` only for current temporary context

## Skill Selection
Use actual paths from `skills.json`. Communication covers emails, documentation, tickets, summaries, rewriting, and reports. Build covers coding, creation, implementation, refactoring, UI, testing, and optimization. Thinking covers planning, architecture, troubleshooting, root cause, risks, and decisions. Research covers current information, sources, comparisons, verification, and evidence. System covers orchestration, multi-agent workflows, tools, handoffs, and process control.

## Specification-First Rule
For substantial changes: update requirements, design, and tasks; obtain approval; create `HANDOFF.md`; then implement only approved scope. Small corrections may use a lightweight handoff.

## Agent Roles
The planner scopes work; architect designs; researcher gathers evidence; builder implements; reviewer evaluates the diff; QA validates; documentation writer maintains guidance; security reviewer evaluates risk; deployment manager prepares releases; project manager coordinates gates. Full definitions are in `agents/`.

## Scope Control
Inspect before editing. Preserve useful content. Do not modify unrelated files or silently expand scope. Surface conflicts instead of destructively resolving them.

## Validation Requirements
Run relevant tests plus `python scripts/validate-repo.py`, `python scripts/list-skills.py`, and Markdown validation. Fix work-caused failures.

## Reporting Requirements
Report files changed, requirement coverage, tests and results, assumptions, risks, warnings, and recommended follow-up.

## Security Rules
Use placeholders, least privilege, and data minimization. Do not expose secrets or copy confidential information into prompts, logs, or research.

## Git Rules
- Do not commit automatically.
- Do not push automatically.
- Do not deploy automatically.
- Do not modify unrelated files.
- Do not expose secrets.
- Do not silently expand scope.
