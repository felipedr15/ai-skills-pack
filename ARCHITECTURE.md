# AI OS Architecture

## System Purpose
AI OS is a portable repository framework for reliable AI-assisted development.

## Architectural Principles
Platform-neutral core, explicit human gates, source-controlled memory, actual-path registries, least privilege, reusable artifacts, and validation without hidden mutation.

## Logical Layers
1. Core AI skills in `.agent/skills/`.
2. AI OS core: instructions, roles, prompts, standards, validation, and security.
3. Specifications and project memory.
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
references/ ------> tool-specific guidance
```

## Models
Skills are versioned Markdown instructions with metadata and stable IDs. Agents define bounded responsibilities and handoffs. Prompts are reusable entry points. Specifications express intent and traceability. Project memory separates durable decisions from temporary session context.

## Validation and Security
Standard-library Python and PowerShell check structure, metadata, links, formatting, and obvious secret patterns. These checks reduce risk but do not replace human security review.

## Tool Integration and Data Flow
Tools consume only the files made available through their configuration. Requests flow into selected prompts, roles, skills, specifications, implementation evidence, and human decisions. No universal automatic ingestion is assumed.

## Extension Points
Add skills, agents, prompts, starters, standards, references, validators, and optional integrations through governance and registry updates.

## Non-Goals
AI OS is not an operating system, autonomous deployment service, credential store, universal agent runtime, or substitute for product-specific controls.
