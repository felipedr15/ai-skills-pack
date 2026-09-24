# ai-skills-pack

A structured AI operations repository for reusable agents, skills, prompts, knowledge, memory, standards, templates, schemas, and workflow automation.

[![AI OS CI](https://github.com/felipedr15/ai-skills-pack/actions/workflows/validate.yml/badge.svg)](https://github.com/felipedr15/ai-skills-pack/actions/workflows/validate.yml)

## Overview

`ai-skills-pack` (AI OS) organizes reusable AI working assets and local automation. It coordinates instructions, project context, specifications, and validation across supported tools. Each tool needs its own configuration to read the relevant files; cloning the repository alone does not connect it to every tool.

## What's in This Repository

- Agent roles, skill definitions, and reusable prompts
- Curated knowledge, supporting references, and structured memory
- Standards, project specifications, schemas, templates, and examples
- Bootstrap scripts, tests, generated indexes, and repository documentation

## Who This Is For

Maintainers managing reusable AI assets, contributors adding prompts or skills, and people setting up consistent AI-assisted work across devices and tools.

## Quick Start

1. Clone the repository and read the [structure guide](docs/REPOSITORY_STRUCTURE.md).
2. Review [CONTRIBUTING.md](CONTRIBUTING.md) and the [placement rules](docs/CONTENT_PLACEMENT_RULES.md) before editing.
3. Read the [architecture](docs/architecture/ARCHITECTURE.md) and [workflow](docs/process/WORKFLOW.md) for design and process guidance.
4. Run `./bootstrap.sh` (macOS/Linux) or `./bootstrap.ps1` (PowerShell) if setup automation is needed.
5. Run `python scripts/ai-os.py doctor`, then `python scripts/ai-os.py validate` to inspect the environment and validate the repository.

See [multi-device setup](docs/multi-device-setup.md) and the [CLI reference](docs/cli-reference.md) for details.

## Repository Structure

| Path | Purpose |
| --- | --- |
| `agents/` | Role instructions; `agents.json` registers them |
| `.agent/skills/`, `skills/` | Skill definitions and supporting skill content |
| `prompts/` | Prompt text; `prompts.json` registers it |
| `knowledge/`, `references/` | Stable subject knowledge and supporting references |
| `memory/`, `profile/` | Explicit working context and optional authored profile data |
| `standards/`, `specs/`, `schemas/` | Conventions, feature specifications, and validation structures |
| `templates/`, `examples/` | Reusable starters and completed samples |
| `config/`, `.github/`, `.kiro/` | Configuration and platform integrations |
| `scripts/`, `tests/` | Automation and verification |
| `generated/` | Derived indexes and dashboards; regenerate rather than edit |
| `docs/` | Human documentation, including architecture, workflow, releases, and setup |

See the [full repository structure guide](docs/REPOSITORY_STRUCTURE.md).

## Key Concepts

`knowledge/` holds reusable information; `memory/` holds evolving context. `standards/` defines conventions, `specs/` captures requirements and design, and `schemas/` defines machine-readable validation. `templates/` contains starting points; `examples/` demonstrates use. The [placement rules](docs/CONTENT_PLACEMENT_RULES.md) cover the other boundaries.

## Source of Truth

See [docs/source-of-truth.md](docs/source-of-truth.md) for the complete guide. In brief:

- **Authored content is authoritative** — folder content in `.md` files and registry files (agents, prompts, memory)
- **Registry files must stay in sync** — when adding/changing source, update the corresponding `.json` registry
- **Generated content is derived** — never hand-edit files in `generated/`; run the generation scripts instead
- **Validation ensures alignment** — run generators and validators before committing

Key locations: Agent instructions → `agents/*.md` + `agents.json` | Prompts → `prompts/*.md` + `prompts.json` | Skills → `.agent/skills/*/SKILL.md` + generated index | Memory → `memory/*.md` + `memory/registry.json`

## Setup

The root [bootstrap.sh](bootstrap.sh) and [bootstrap.ps1](bootstrap.ps1) call the repository's Python setup command. Review the script for your platform before running it. Core commands use Python 3.10 or newer; see [setup guidance](docs/multi-device-setup.md).

## Documentation

**Start here:** [docs/README.md](docs/README.md) is the docs index and your entry point.

| Topic | Document |
| --- | --- |
| Authoritative content | [Source of Truth](docs/source-of-truth.md) — what's authoritative vs. derived |
| Architecture and structure | [Architecture](docs/architecture/ARCHITECTURE.md) · [Repository Structure](docs/REPOSITORY_STRUCTURE.md) |
| Workflow and governance | [Workflow](docs/process/WORKFLOW.md) · [Governance](docs/governance/GOVERNANCE.md) |
| Contributions and security | [Contributing](CONTRIBUTING.md) · [Content Placement](docs/CONTENT_PLACEMENT_RULES.md) · [Security](SECURITY.md) |
| Plans and history | [Roadmap](docs/project/ROADMAP.md) · [Changelog](CHANGELOG.md) · [Release notes](docs/releases/) |
| Commands and setup | [CLI reference](docs/cli-reference.md) · [Multi-device setup](docs/multi-device-setup.md) |

## Contributing

Follow [CONTRIBUTING.md](CONTRIBUTING.md), use the [placement rules](docs/CONTENT_PLACEMENT_RULES.md), keep edits scoped, and update documentation and generated artifacts when source paths or behavior change.

## Security

Report security issues using [SECURITY.md](SECURITY.md). Do not commit secrets, credentials, tokens, or sensitive data.

## Releases and Versioning

The current version is in [VERSION](VERSION); [CHANGELOG.md](CHANGELOG.md) tracks changes and [release notes](docs/releases/) document releases.

## Maintainer Notes

Keep registered paths aligned with content, regenerate derived output after source changes, and run the [validation suite](#validation) before proposing changes.

## Operational Details

The sections below describe implemented capabilities and commands in more detail.


## Supported Tools

AI OS provides guidance for ChatGPT (planning, research, troubleshooting, documentation, review), Claude (architecture and long-context review), GitHub Copilot and VS Code Agent mode (repository implementation), Kiro (specification-oriented work), Codex (repository execution and validation), v0 (web UI ideation), Vercel (hosting and deployment), and Canva (visual communication). Support depends on product, plan, version, integration, configuration, and the instructions supplied; tools do not automatically read every repository file.

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

Skill `SKILL.md` front matter is the source of truth. Files under [generated/](generated/README.md), including the generated registry and repository index, are deterministic outputs and must never be edited as sources of truth. The legacy [skills.json](skills.json) remains available for compatibility during Phase 1. Role and prompt files live in `agents/` and `prompts/`; their root JSON registries are maintained alongside them. See [content placement rules](docs/CONTENT_PLACEMENT_RULES.md).

## Standard Workflow

Request → Planning → Requirements → Design → Tasks → Execution → Validation → Review → Human approval → Commit → Deployment

See [WORKFLOW.md](docs/process/WORKFLOW.md) for gates and handoffs.

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

Memory commands remain available as standalone scripts for compatibility. Common release, validation,
orchestration, profile, dashboard, and MCP operations are consolidated under `python scripts/ai-os.py`.

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
python scripts/ai-os.py mcp check
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

For portable setup across Windows devices and future clones, see
[Multi-Device Setup](docs/multi-device-setup.md). For v1.0 release gates, see
[AI OS v1.0 Acceptance Criteria](docs/v1.0-acceptance-criteria.md).

## Project Creation

```text
python scripts/create-project.py --list-types
python scripts/create-project.py --name "My Project" --type web-app --destination ../my-project
python scripts/create-project.py --name "Ops Automation" --type automation --destination ../ops-automation
```

The command copies a starter, replaces safe placeholders, creates `project.yaml`, and refuses to overwrite a non-empty destination unless `--force` is explicit. Add `--init-git` to initialize an empty Git repository; the command never installs dependencies or creates commits.

## Automation Status

Phase 1 core automation implements registry generation, repository indexing, unified validation, and project bootstrap. Phase 2 implements the structured local Memory Engine. Phase 3 implements the local repository Knowledge Graph.
