# AI OS Roadmap

## Version 1.0 — Foundation
Implemented foundation: core skills, agent roles, shared instructions, prompt library, specification templates, project memory, project starters, security, validation, and documentation.

## Phase 1 — Core Automation (Implemented)

Deterministic skill-registry generation, repository indexing, unified continuous validation, and one-command project bootstrap.

## Phase 2 — Memory Engine (Implemented)

Structured local memory architecture, memory schema and registry, memory CRUD-style command scripts, archive and promotion workflows, deterministic memory index generation, and memory security validation.

## Phase 3 — Knowledge Graph (Implemented)

Deterministic local graph generation from repository source files, graph validation and staleness checks, relationship discovery from explicit references and metadata, and generated graph summaries.

## Phase 4 — Semantic Discovery (Implemented)

Local semantic discovery and graph-query engine combining the knowledge graph, source file metadata, and memory records into a deterministic search index. Supports keyword, phrase, type, path, and relationship filtering with graph traversal, shortest-path finding, and scoring explanations. CLI provides search, related, traverse, path, explain, and stats commands.

## Phase 5 — Interactive Dashboard (Implemented)

Local-first, offline-capable web dashboard for exploring repository state. Provides Overview, Skills, Memory, Knowledge Graph (list + SVG visualization), Discovery (search with explain), and Repository views. Uses Python standard-library HTTP server with no external dependencies. Includes graph visualization with BFS neighbor expansion, type/relationship filters, and performance limits.

## Phase 6 — MCP Integration (Implemented)

Protocol-neutral service layer and MCP-compatible server exposing 15 tools and 9 resources over stdio transport. Provides semantic search, graph traversal, skill/memory lookup, and safe file access with repository-root confinement, path traversal rejection, secret-file blocking, bounded excerpts, and read-only default mode. No external dependencies required.

## Phase 7 — Release Hardening (Implemented)

One-command bootstrap, unified CLI, environment doctor, configuration system, build orchestration, release packaging, backup/restore, safe cleaning, migration framework, and cross-platform wrappers. Semantic versioning with single source of truth. Release check validates all phases before packaging.

## Phase 8 — Continuous Learning and Agent Orchestration (Implemented)

Deterministic task classification, agent and workflow registries, knowledge-retrieval planning
(reusing the Phase 4 discovery engine), local session tracking with an explicit approval
boundary, memory-suggestion generation gated on explicit approval, knowledge-gap and freshness
detection, local feedback capture, and a hash-chained audit trail. 14 new read-only MCP tools, 8
new resources, and 8 new dashboard pages. No execution engine — planning and tracking only.

## Phase 9 — Professional Context and Work Intelligence (Implemented)

A strictly local-first, privacy-first layer capturing the user's own professional role/organizational
context as canonical authored records (`profile/`), deriving work-activity signals purely from
data Phases 2 and 8 already capture (`generated/work-activity.json`), and maintaining an
evidence-based expertise list. Exactly one profile may be active at a time, and switching is
always an explicit, approval-gated action — never automatic. Minimal knowledge-graph and
semantic-discovery integration classifies profile records without exposing role/team/prose through
generic traversal. 3 new read-only MCP tools and 1 new dashboard page, both summary-only. No
professional profile is included with the repository; `profile/registry.json` ships empty.

## Version 1.1 — Workflow Improvements (Proposed)
Improved bootstrap, deeper validation, more examples, and expanded Power Apps, Power Automate, and web deployment guidance.

## Version 1.2 — Integration Improvements (Proposed)
Optional MCP research, synchronization workflows, documentation indexing, and registry generation.

## Version 2.0 — Advanced Automation (Proposed)
Project dashboard, skill dependency visualization, optional knowledge indexing, and release automation. Multi-agent orchestration's planning/tracking foundation is implemented in Phase 8; a controlled, allow-listed execution engine (still requiring human approval at every consequential step) remains proposed.

Dashboard, MCP-driven integrations, and advanced unified CLI orchestration remain proposed.
