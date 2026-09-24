# ai-skills-pack

A structured AI operations repository for reusable agents, skills, prompts, knowledge, memory, standards, templates, schemas, examples, and automation.

## Overview

`ai-skills-pack` is a structured repository for organizing reusable AI working assets across tools, workflows, and environments.

It separates agent definitions, reusable skills, prompt libraries, stable knowledge, working memory, references, standards, specifications, templates, schemas, examples, generated outputs, and automation scripts so they can be maintained consistently and reused safely.

This repository is designed to support repeatable AI-assisted work with clearer structure, better maintainability, and easier contributor onboarding.

## What This Repository Includes

This repository includes:

- agent definitions
- reusable skills
- prompt libraries
- stable knowledge and references
- memory and context structures
- standards and specifications
- templates and schemas
- examples and generated artifacts
- configuration and profile assets
- setup and bootstrap scripts
- repository workflow, contribution, and security guidance

## Who This Is For

This repository is intended for:

- maintainers managing reusable AI assets
- contributors adding skills, prompts, standards, or reference material
- teams building structured AI-assisted workflows
- users who want an AI-OS-style repository with clear content boundaries

## Quick Start

1. Read this README for the repository layout and content model.
2. Review `CONTRIBUTING.md` before making changes.
3. Check `docs/` for supporting documentation.
4. Use `bootstrap.sh` or `bootstrap.ps1` if environment setup is needed.
5. Review `AGENTS.md` and `CLAUDE.md` if you are using tool-specific agent workflows.

## Repository Structure

| Path | Purpose |
|---|---|
| `agents/` | Agent definitions and role-based assistant configurations |
| `skills/` | Reusable capability or task packs |
| `prompts/` | Prompt assets and reusable prompt patterns |
| `knowledge/` | Stable reusable knowledge |
| `memory/` | Persistent or evolving working context |
| `references/` | Supporting source material and background references |
| `standards/` | Rules, conventions, and operating standards |
| `specs/` | Design, behavior, or implementation specifications |
| `schemas/` | Data structures, contracts, and validation definitions |
| `templates/` | Reusable starter files and patterns |
| `examples/` | Sample implementations and usage examples |
| `examples/mcp/` | Example MCP-related content |
| `generated/` | Generated or derived artifacts |
| `config/` | Configuration assets and repository/tool settings |
| `profile/` | Profile, persona, or identity-related assets |
| `docs/` | Supporting documentation |
| `scripts/` | Maintenance, setup, and automation scripts |
| `tests/` | Validation and test assets |
| `.github/` | GitHub workflows and repository configuration |
| `.agent/` | Agent-tool-specific guidance and related assets |
| `.kiro/` | Tool/editor-specific configuration |
| `AGENTS.md` | Agent-specific operating guidance |
| `CLAUDE.md` | Tool-specific guidance for Claude-oriented workflows |
| `README.md` | Repository entry point and navigation |
| `CONTRIBUTING.md` | Contribution guidance |
| `SECURITY.md` | Security reporting and handling guidance |
| `CHANGELOG.md` | Change history |
| `VERSION` | Current repository version |
| `agents.json` | Agent manifest or index |
| `skills.json` | Skills manifest or index |
| `prompts.json` | Prompts manifest or index |
| `bootstrap.sh` | Bootstrap script for Unix-like environments |
| `bootstrap.ps1` | Bootstrap script for PowerShell environments |

## Content Boundaries

To keep the repository consistent, use these boundaries when placing content:

- `knowledge/` stores stable, reusable knowledge
- `memory/` stores persistent or evolving context
- `references/` stores supporting source material or background information
- `standards/` stores rules, conventions, and operating expectations
- `specs/` stores design intent, requirements, or implementation details
- `schemas/` stores machine-readable structures and validation rules
- `templates/` stores reusable starting points
- `examples/` stores demonstrations or sample usage
- `generated/` stores derived output rather than primary authored content

When content could fit in multiple places, prefer the directory that best matches its long-term purpose rather than where it was first used.

## Tooling and Manifest Files

This repository includes top-level manifest or index files:

- `agents.json`
- `skills.json`
- `prompts.json`

These files should remain aligned with the corresponding content directories:

- `agents/`
- `skills/`
- `prompts/`

If your workflow generates these files from directory contents, or generates directory contents from these files, document that behavior clearly in `docs/` and follow it consistently.

## Tool-Specific Directories

Some repository areas are tool-dependent and should be changed carefully:

- `.github/` contains GitHub configuration and workflow behavior
- `.agent/` contains agent-tool-specific guidance and related structure
- `.kiro/` contains tool/editor-specific configuration
- `AGENTS.md` and `CLAUDE.md` provide tool-specific operating guidance

Changes in these locations may affect product behavior, validation, editor integrations, or automation workflows.

## Supporting Repository Areas

Additional supporting areas include:

- `config/` for configuration assets and structured settings
- `profile/` for profile or persona-related content
- `generated/` for generated or derived outputs
- `docs/` for supporting documentation
- `scripts/` for setup, maintenance, and operational automation
- `tests/` for verification and repository validation

## Setup

Bootstrap scripts are provided for environment setup:

- `bootstrap.sh`
- `bootstrap.ps1`

Use the script that matches your environment, and review script contents before running them.

## Documentation

Use the documentation in `docs/` for deeper reference material and supporting repository guidance.

Also review:

- `README.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `AGENTS.md`
- `CLAUDE.md`

## Contributing

Before contributing:

1. Read `CONTRIBUTING.md`
2. Place content in the correct directory
3. Keep manifests and content folders aligned
4. Update documentation when repository structure or behavior changes
5. Avoid committing secrets, credentials, tokens, or sensitive data

Prefer small, well-scoped changes that improve structure, clarity, or reuse.

## Security

If you identify a security issue, follow the process documented in `SECURITY.md`.

Do not commit:

- passwords
- API keys
- access tokens
- private keys
- internal secrets
- sensitive personal or customer data

## Releases and Versioning

Repository versioning and change tracking are maintained through:

- `VERSION`
- `CHANGELOG.md`

## Maintainer Notes

Maintainers should ensure that:

- repository boundaries remain clear
- generated content is not confused with source content
- manifest files remain aligned with directory contents
- tool-specific configuration is updated carefully
- documentation stays synchronized with repository changes

## Status

This repository is actively structured around reusable AI operational assets, workflow support, and maintainable content organization.

As the repository evolves, update this README when:

- new top-level directories are added
- source-of-truth rules change
- tool-specific behavior changes
- bootstrap or validation workflows change
