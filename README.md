# AI OS

## Overview

AI OS is a repository-based **AI Development Operating System** for coordinating AI tools, reusable skills, specifications, project memory, validation, documentation, and deployment workflows. It is not a traditional computer operating system. It is the evolution of the original AI Skills Pack, whose existing skills remain in their integration-safe locations.

## Supported Tools

AI OS provides guidance for ChatGPT (planning, research, troubleshooting, documentation, review), Claude (architecture and long-context review), GitHub Copilot and VS Code Agent mode (repository implementation), Kiro (specification-oriented work), Codex (repository execution and validation), v0 (web UI ideation), Vercel (hosting and deployment), and Canva (visual communication). Support depends on product, plan, version, integration, configuration, and the instructions supplied; tools do not automatically read every repository file.

## Core Capabilities

Skills, agents, prompts, specifications, project memory, structured repository memory, project starters, standards, a knowledge base, validation, security guidance, and deployment guidance.

## Available Skills

| Name | ID | Path | Version | Status | Purpose |
|---|---|---|---|---|---|
| Creator | `creator` | [.agent/skills/build/creator/SKILL.md](.agent/skills/build/creator/SKILL.md) | 1.0.0 | stable | Reusable guidance for creator work. |
| Frontend | `frontend` | [.agent/skills/build/frontend/SKILL.md](.agent/skills/build/frontend/SKILL.md) | 1.0.0 | stable | Reusable guidance for frontend work. |
| Performance Optimization | `performance-optimization` | [.agent/skills/build/performance-optimization/SKILL.md](.agent/skills/build/performance-optimization/SKILL.md) | 1.0.0 | stable | Reusable guidance for performance optimization work. |
| Vercel Agent | `vercel-agent` | [.agent/skills/build/vercel-agent/SKILL.md](.agent/skills/build/vercel-agent/SKILL.md) | 1.0.0 | stable | Reusable guidance for vercel agent work. |
| Vercel React | `vercel-react` | [.agent/skills/build/vercel-react/SKILL.md](.agent/skills/build/vercel-react/SKILL.md) | 1.0.0 | stable | Reusable guidance for vercel react work. |
| web-design-guidelines | `web-design-guidelines` | [.agent/skills/build/web-design-guidelines/SKILL.md](.agent/skills/build/web-design-guidelines/SKILL.md) | 1.0.0 | stable | Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices". |
| Browser | `browser` | [.agent/skills/design/browser/SKILL.md](.agent/skills/design/browser/SKILL.md) | 1.0.0 | stable | Reusable guidance for browser work. |
| Ui Ux Pro Max | `ui-ux-pro-max` | [.agent/skills/design/ui-ux-pro-max/SKILL.md](.agent/skills/design/ui-ux-pro-max/SKILL.md) | 1.0.0 | stable | Reusable guidance for ui ux pro max work. |
| Analytical | `analytical` | [.agent/skills/personal/analytical/SKILL.md](.agent/skills/personal/analytical/SKILL.md) | 1.0.0 | stable | Reusable guidance for analytical work. |
| Clear Concise Writing | `clear-concise-writing` | [.agent/skills/personal/clear-concise-writing/SKILL.md](.agent/skills/personal/clear-concise-writing/SKILL.md) | 1.0.0 | stable | Reusable guidance for clear concise writing work. |
| Problem Solving | `problem-solving` | [.agent/skills/personal/problem-solving/SKILL.md](.agent/skills/personal/problem-solving/SKILL.md) | 1.0.0 | stable | Reusable guidance for problem solving work. |
| Simplify | `simplify` | [.agent/skills/personal/simplify/SKILL.md](.agent/skills/personal/simplify/SKILL.md) | 1.0.0 | stable | Reusable guidance for simplify work. |
| Writing | `writing` | [.agent/skills/personal/writing/SKILL.md](.agent/skills/personal/writing/SKILL.md) | 1.0.0 | stable | Reusable guidance for writing work. |
| Superpower | `superpower` | [.agent/skills/system/superpower/SKILL.md](.agent/skills/system/superpower/SKILL.md) | 1.0.0 | stable | Reusable guidance for superpower work. |
| Testing | `testing` | [.agent/skills/system/testing/SKILL.md](.agent/skills/system/testing/SKILL.md) | 1.0.0 | stable | Reusable guidance for testing work. |
| using-superpowers | `using-superpowers` | [.agent/skills/system/using-superpowers/SKILL.md](.agent/skills/system/using-superpowers/SKILL.md) | 1.0.0 | stable | Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions |

Skill `SKILL.md` front matter is the source of truth. Files under [generated/](generated/README.md), including the generated registry and repository index, are deterministic outputs and must never be edited as sources of truth. The legacy [skills.json](skills.json) remains available for compatibility during Phase 1.

## Standard Workflow

Request → Planning → Requirements → Design → Tasks → Execution → Validation → Review → Human approval → Commit → Deployment

See [WORKFLOW.md](WORKFLOW.md) for gates and handoffs.

## Agent Roles

Planner, architect, researcher, builder, reviewer, QA, documentation writer, security reviewer, deployment manager, and project manager roles are registered in [agents.json](agents.json) and documented in [agents/](agents/README.md).

## Specifications

Substantial work moves through approved requirements, design, and task documents. Start with [specification templates](templates/specifications/README.md) or organize a feature under [specs/](specs/README.md).

## Project Memory

The [project-memory template](templates/project-memory/README.md) provides `README.md`, `AGENTS.md`, `CLAUDE.md`, `REQUIREMENTS.md`, `DESIGN.md`, `TASKS.md`, `decisions.md`, `HANDOFF.md`, temporary `SESSION.md`, `TESTING.md`, `KNOWN_ISSUES.md`, `CHANGELOG.md`, `RELEASE_NOTES.md`, and `RETROSPECTIVE.md` (plus architecture and roadmap context).

## Memory Engine (Phase 2)

The [memory engine](memory/README.md) adds structured, local, repository-based records for:

- permanent memory (`memory/permanent/`)
- project memory (`memory/projects/`)
- session memory (`memory/sessions/`)
- decision memory (`memory/decisions/`)
- lessons learned (`memory/lessons/`)
- archive retention (`memory/archive/`)

Source Markdown records and [memory/registry.json](memory/registry.json) are the source of truth.
Generated files [generated/memory-index.json](generated/memory-index.json) and [generated/memory-index.md](generated/memory-index.md) are derived and never authoritative.

AI OS memory is explicit repository content. It is not automatic access to ChatGPT, Claude, Copilot, or Kiro histories. Tools only receive memory when configured or instructed to read it.

The repository does not currently expose a unified AI OS CLI module for memory commands, so Phase 2 uses standalone scripts. Future CLI consolidation remains proposed.

### Memory Commands

```text
python scripts/memory-add.py --type lesson --title "Refresh data before rebuilding collections" --scope global --summary "Refresh the source before rebuilding dependent collections." --tags "power-apps,sharepoint,refresh" --sensitivity internal --retention permanent
python scripts/memory-list.py --type lesson
python scripts/memory-search.py "refresh" --tag refresh --max-results 10
python scripts/memory-archive.py --id lesson-powerapps-refresh-001
python scripts/memory-promote.py --id session-memory-engine-example-001 --target-type lesson --target-scope global --reason "Reusable troubleshooting lesson"
python scripts/generate-memory-index.py
python scripts/generate-memory-index.py --check
python scripts/validate-memory-security.py
```

## Knowledge Graph (Phase 3)

The local Knowledge Graph connects repository entities and relationships across skills, memories, projects, documents, tools, platforms, and concepts.

- Source of truth remains Markdown and JSON source files.
- Generated graph outputs are derived artifacts and never authoritative.
- No external API, cloud service, vector database, or hosted graph database is used.

Supported node types:

- `skill`
- `memory`
- `project`
- `document`
- `platform`
- `tool`
- `concept`

Supported edge types:

- `contains`
- `references`
- `related_to`
- `supports`
- `uses`
- `belongs_to`
- `generated_from`

Output files:

- `generated/knowledge-graph.json`
- `generated/knowledge-graph.md`

Knowledge graph commands:

```text
python scripts/generate-knowledge-graph.py
python scripts/validate-knowledge-graph.py
python scripts/generate-knowledge-graph.py --check
python scripts/knowledge-build.py
python scripts/knowledge-validate.py
python scripts/knowledge-check.py
```

Extend entity and relationship coverage by updating extraction and graph modules in `scripts/knowledge_graph/` and adding tests in `tests/test_knowledge_graph.py`.

## Continuous Learning and Agent Orchestration (Phase 8)

A planning and tracking layer on top of Phases 1-7: classify a task, select a workflow and agent
roles, retrieve relevant knowledge, track a local work session, and produce memory/knowledge-gap/
feedback suggestions that require explicit human approval before anything becomes permanent.
Nothing here executes work, touches Git, or calls a network service.

```text
python scripts/ai-os.py classify "Fix the login bug"
python scripts/ai-os.py plan "Fix the login bug" --explain
python scripts/ai-os.py session start "Fix the login bug"
python scripts/ai-os.py session validate <id> --name unit-tests --status pass
python scripts/ai-os.py session complete <id>
python scripts/ai-os.py approval list --status pending
python scripts/ai-os.py approval approve <id>
python scripts/ai-os.py memory-suggestions list --status pending
python scripts/ai-os.py memory-suggestions approve <id>
python scripts/ai-os.py knowledge-health
python scripts/ai-os.py knowledge-gaps
python scripts/ai-os.py review-due
python scripts/ai-os.py feedback add --type outdated --target-type document --target-id x.md
python scripts/ai-os.py audit validate
```

See [Continuous Learning](docs/continuous-learning.md), [Agent Orchestration](docs/agent-orchestration.md),
[Memory Approval](docs/memory-approval.md), [Knowledge Health](docs/knowledge-health.md),
[Feedback and Audit](docs/feedback-and-audit.md), and
[Phase 8 Architecture](knowledge/architecture/phase-8-learning-orchestration.md).

## Professional Context and Work Intelligence (Phase 9)

A strictly local-first, privacy-first layer for the user's own professional identity and work
patterns — canonical, explicitly-authored profile records in `profile/` (never inferred or
guessed), an evidence-based expertise list, and deterministic work-activity signals aggregated
from data Phases 2 and 8 already capture. `profile/` (canonical structured source),
`knowledge/professional-context/` (curated, human-owned prose, scaffolded once and never
silently overwritten), `memory/` (approval-gated learned records — never professional identity
data), and `generated/` (deterministic derived artifacts) each have a distinct, enforced role.
Profile switching is always an explicit, approval-gated action; nothing here auto-selects or
auto-switches a profile, and MCP/dashboard exposure is read-only and summary-only.

```text
python scripts/ai-os.py profile list
python scripts/ai-os.py profile show
python scripts/ai-os.py profile switch <profile-id>
python scripts/ai-os.py approval approve <id>
python scripts/ai-os.py profile sync-knowledge
python scripts/ai-os.py profile sync-knowledge --force-refresh
```

`profile/registry.json` starts empty — no profile is fabricated by any tool. `profile switch`
requires an explicitly approved `profile-switch` approval before it changes anything; running it
first requests that approval and stops. `profile sync-knowledge` scaffolds
`knowledge/professional-context/overview.md` only if it doesn't already exist; `--force-refresh`
never rewrites `overview.md` — it checkpoints the current curated content into a timestamped file
under `knowledge/professional-context/snapshots/`.

See [Phase 9 Architecture](knowledge/architecture/phase-9-professional-context.md).

## Quick Start

1. Clone or open AI OS.
2. Run repository validation.
3. Select a project starter.
4. Generate a project with `create-project.py`.
5. Complete its README.
6. Create requirements.
7. Create the design.
8. Create implementation tasks.
9. Prepare `HANDOFF.md`.
10. Execute approved work.
11. Run validation.
12. Review the Git diff.
13. Complete human testing.
14. Commit approved changes.
15. Deploy when applicable.

## Validation

```text
python scripts/generate-skill-registry.py --check
python scripts/index-repository.py --check
python scripts/generate-memory-index.py --check
python scripts/generate-knowledge-graph.py --check
python scripts/validate-knowledge-graph.py
python scripts/validate-memory-security.py
python scripts/validate-all.py
python scripts/list-skills.py
```

Regenerate derived files after changing skills, memory records, or indexed content:

```text
python scripts/generate-skill-registry.py
python scripts/index-repository.py
python scripts/generate-memory-index.py
python scripts/generate-knowledge-graph.py
```

The optional `--check` mode performs no writes and exits non-zero when generated files are missing or stale.

See [Command Reference](docs/cli-reference.md) for a complete cheat sheet of CLI, validation, and
release/Git workflow commands with descriptions and usage examples.

## Project Creation

```text
python scripts/create-project.py --list-types
python scripts/create-project.py --name "My Project" --type web-app --destination ../my-project
python scripts/create-project.py --name "Ops Automation" --type automation --destination ../ops-automation
```

The command copies a starter, replaces safe placeholders, creates `project.yaml`, and refuses to overwrite a non-empty destination unless `--force` is explicit. Add `--init-git` to initialize an empty Git repository; the command never installs dependencies or creates commits.

## Automation Status

Phase 1 core automation implements registry generation, repository indexing, unified validation, and project bootstrap. Phase 2 implements the structured local Memory Engine. Phase 3 implements the local repository Knowledge Graph.

## Security

Follow [SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md).

## References

Platform notes and examples are in [references/](references/README.md).
