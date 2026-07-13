# AI OS Architecture

## System Purpose
AI OS is a portable repository framework for reliable AI-assisted development.

## Architectural Principles
Platform-neutral core, explicit human gates, source-controlled memory, actual-path registries, least privilege, reusable artifacts, and validation without hidden mutation.

## Logical Layers
1. Core AI skills in `.agent/skills/`.
2. AI OS core: instructions, roles, prompts, standards, validation, and security.
3. Specifications, project memory, and structured memory engine records.
4. Project starters.
5. Knowledge and platform references.

## Directory Map
```text
request
  -> prompts + agent role + selected skills
  -> requirements -> design -> tasks -> HANDOFF
  -> implementation -> validation -> review
  -> human approval -> commit/deployment

.agent/skills ----> skills.json
agents/ ----------> agents.json
prompts/ ---------> prompts.json
templates/ -------> project artifacts
scripts/ ---------> validation/bootstrap
memory/ ----------> source memory records + registry
references/ ------> tool-specific guidance
```

## Phase 1 Automation

`SKILL.md` front matter is authoritative. `generate-skill-registry.py` validates it and derives `generated/skills.json` and `generated/skills.md`. `index-repository.py` derives a security-conscious repository index and map from allowed source categories. Generated files are never sources of truth.

`validate-all.py` is the unified read-only validation entry point. It checks existing repository rules, generated-file freshness, JSON, metadata, links, identifiers, dependencies, secret patterns, required templates, and unit tests. `create-project.py` copies a selected starter, safely replaces project placeholders, emits `project.yaml`, and optionally initializes Git without installing dependencies or committing.

Phase 2 implements local structured memory records, deterministic memory indexing, memory lifecycle commands, archive and promotion flows, and memory-specific security validation. Advanced orchestration, publishing, deployment, and release automation remain proposed.

## Memory Engine Architecture

The Memory Engine is repository-local and uses Markdown plus JSON.

- Source records: `memory/**/*.md`
- Source registry: `memory/registry.json`
- Schema: `schemas/memory.schema.json`
- Generated views: `generated/memory-index.json` and `generated/memory-index.md`
- Commands: add, list, search, archive, promote
- Security scan: `scripts/validate-memory-security.py`

Memory promotion preserves traceability with related IDs. Archived records remain retained under `memory/archive/`; records are not deleted by memory tooling.

Generated memory indexes are deterministic outputs and not source-of-truth data.

## Models
Skills are versioned Markdown instructions with metadata and stable IDs. Agents define bounded responsibilities and handoffs. Prompts are reusable entry points. Specifications express intent and traceability. Project memory separates durable decisions from temporary session context.

## Validation and Security
Standard-library Python and PowerShell check structure, metadata, links, formatting, memory metadata consistency, archive placement rules, and secret-pattern checks (including memory records). These checks reduce risk but do not replace human security review.

## Tool Integration and Data Flow
Tools consume only the files made available through their configuration. Requests flow into selected prompts, roles, skills, specifications, implementation evidence, and human decisions. No universal automatic ingestion is assumed.

## Extension Points
Add skills, agents, prompts, starters, standards, references, validators, and optional integrations through governance and source metadata updates, then regenerate derived artifacts.

## Non-Goals
AI OS is not an operating system, autonomous deployment service, credential store, universal agent runtime, or substitute for product-specific controls.
