# AI OS Architecture

## System Purpose
AI OS is a portable repository framework for reliable AI-assisted development.

## Architectural Principles
Platform-neutral core, explicit human gates, source-controlled memory, actual-path registries, least privilege, reusable artifacts, and validation without hidden mutation.

## Logical Layers
1. Core AI skills in `.agent/skills/`.
2. AI OS core: instructions, roles, prompts, standards, validation, and security.
3. Specifications, project memory, structured memory engine records, and knowledge graph relationships.
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
generated/ -------> deterministic derived artifacts
references/ ------> tool-specific guidance
```

## Phase 1 Automation

`SKILL.md` front matter is authoritative. `generate-skill-registry.py` validates it and derives `generated/skills.json` and `generated/skills.md`. `index-repository.py` derives a security-conscious repository index and map from allowed source categories. Generated files are never sources of truth.

`validate-all.py` is the unified read-only validation entry point. It checks existing repository rules, generated-file freshness, JSON, metadata, links, identifiers, dependencies, secret patterns, required templates, and unit tests. `create-project.py` copies a selected starter, safely replaces project placeholders, emits `project.yaml`, and optionally initializes Git without installing dependencies or committing.

Phase 2 implements local structured memory records, deterministic memory indexing, memory lifecycle commands, archive and promotion flows, and memory-specific security validation. Phase 3 implements a deterministic local knowledge graph generated from repository sources. Phase 4 implements a local semantic discovery and graph-query engine that combines the knowledge graph, source files, and memory metadata into a searchable index with deterministic ranking, graph traversal, and CLI querying. Phase 5 implements a local interactive dashboard for exploring repository state with read-only views, graph visualization, and live API endpoints. Phase 6 implements a protocol-neutral service layer and MCP-compatible server exposing repository knowledge, search, and graph traversal over stdio transport. Phase 7 implements release hardening with unified CLI, one-command bootstrap, environment doctor, configuration, build orchestration, packaging, backup/restore, and cross-platform support. Advanced orchestration, publishing, deployment, and release automation remain proposed.

## Knowledge Graph Architecture

The Knowledge Graph is repository-local and generated from authoritative Markdown and JSON sources.

- Builder: `scripts/generate-knowledge-graph.py`
- Validator: `scripts/validate-knowledge-graph.py`
- Internal modules: `scripts/knowledge_graph/`
- JSON output: `generated/knowledge-graph.json`
- Markdown summary: `generated/knowledge-graph.md`

Source files remain authoritative. Generated graph artifacts are derived views.

Graph model includes nodes and edges with deterministic IDs and normalized relative paths. Relationship discovery is conservative and uses explicit links, wiki links, metadata, and curated text cues.

Staleness checks compare regenerated graph data to checked-in output while ignoring `generatedAt`.

## Semantic Discovery Architecture

The Semantic Discovery engine is repository-local and combines the knowledge graph with source file metadata into a queryable search index.

- Query CLI: `scripts/discover.py`
- Builder: `scripts/discovery-build.py`
- Validator: `scripts/discovery-validate.py`
- Staleness check: `scripts/discovery-check.py`
- Internal modules: `scripts/semantic_discovery/`
- JSON output: `generated/discovery-index.json`
- Markdown summary: `generated/discovery-index.md`

Query modes: search, related, traverse, path, explain, stats. Ranking is deterministic with stable tie-breaking (score descending, type, name, ID). Graph traversal uses BFS with cycle protection and configurable depth (max 5).

Source files remain authoritative. The discovery index is a derived compact artifact that references source paths and graph node IDs without duplicating source content. Staleness checks ignore `generatedAt` only.

## Dashboard Architecture

The Interactive Dashboard is a local-first, offline-capable web application for exploring repository state.

- Build: `scripts/dashboard-build.py`
- Serve: `scripts/dashboard-serve.py`
- Validate: `scripts/dashboard-validate.py`
- Staleness check: `scripts/dashboard-check.py`
- Internal modules: `scripts/dashboard/`
- HTML output: `generated/dashboard.html`
- Data output: `generated/dashboard-data.json`

The dashboard reads generated JSON artifacts and presents interactive views: Overview, Skills, Memory, Knowledge Graph (list + visualization), Discovery, and Repository. It uses a Python standard-library HTTP server on localhost with no external dependencies, no network calls beyond localhost, and no telemetry.

Graph visualization uses a vanilla SVG force-directed layout limited to 50 nodes with BFS neighbor expansion (depth 1-3). All rendered text is escaped. No secrets or full memory contents are displayed. The dashboard is read-only and non-authoritative.

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

## Continuous Learning and Agent Orchestration Architecture (Phase 8)

A planning/tracking layer, not an execution engine. `scripts/orchestration/` classifies a task
deterministically, selects a workflow (`knowledge/workflows/*.json` → `generated/workflow-registry.json`)
and agent roles (`agents/*.md` → `generated/agent-registry.json`), retrieves knowledge by reusing
the existing semantic discovery engine, and tracks a local session
(`.ai-os/sessions/`) through an explicit status-transition graph.

Storage is split by nature: deterministic registries and the knowledge-health report live in
`generated/` (committed, `--check`-able); sessions, approvals, memory suggestions, feedback, and
the hash-chained audit trail live in `.ai-os/` (local, git-ignored). Promoting a memory suggestion
into `memory/` is the only write path, and it is blocked until a human explicitly approves it —
see [Phase 8 Architecture](knowledge/architecture/phase-8-learning-orchestration.md) for the full
design.

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
