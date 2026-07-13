# AI OS

## Overview

AI OS is a repository-based **AI Development Operating System** for coordinating AI tools, reusable skills, specifications, project memory, validation, documentation, and deployment workflows. It is not a traditional computer operating system. It is the evolution of the original AI Skills Pack, whose existing skills remain in their integration-safe locations.

## Supported Tools

AI OS provides guidance for ChatGPT (planning, research, troubleshooting, documentation, review), Claude (architecture and long-context review), GitHub Copilot and VS Code Agent mode (repository implementation), Kiro (specification-oriented work), Codex (repository execution and validation), v0 (web UI ideation), Vercel (hosting and deployment), and Canva (visual communication). Support depends on product, plan, version, integration, configuration, and the instructions supplied; tools do not automatically read every repository file.

## Core Capabilities

Skills, agents, prompts, specifications, project memory, project starters, standards, a knowledge base, validation, security guidance, and deployment guidance.

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

The machine-readable source of truth is [skills.json](skills.json).

## Standard Workflow

Request → Planning → Requirements → Design → Tasks → Execution → Validation → Review → Human approval → Commit → Deployment

See [WORKFLOW.md](WORKFLOW.md) for gates and handoffs.

## Agent Roles

Planner, architect, researcher, builder, reviewer, QA, documentation writer, security reviewer, deployment manager, and project manager roles are registered in [agents.json](agents.json) and documented in [agents/](agents/README.md).

## Specifications

Substantial work moves through approved requirements, design, and task documents. Start with [specification templates](templates/specifications/README.md) or organize a feature under [.kiro/specs/](.kiro/specs/README.md).

## Project Memory

The [project-memory template](templates/project-memory/README.md) provides `README.md`, `AGENTS.md`, `CLAUDE.md`, `REQUIREMENTS.md`, `DESIGN.md`, `TASKS.md`, `decisions.md`, `HANDOFF.md`, temporary `SESSION.md`, `TESTING.md`, `KNOWN_ISSUES.md`, `CHANGELOG.md`, `RELEASE_NOTES.md`, and `RETROSPECTIVE.md` (plus architecture and roadmap context).

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
python scripts/validate-repo.py
python scripts/list-skills.py
powershell -ExecutionPolicy Bypass -File scripts/validate-markdown.ps1
pwsh -File scripts/validate-markdown.ps1
```

## Project Creation

```text
python scripts/create-project.py --name "My Project" --type web-app --destination ../my-project
python scripts/create-project.py --name "Ops Automation" --type automation --destination ../ops-automation
```

The command refuses to overwrite a non-empty destination unless `--force` is explicit.

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
