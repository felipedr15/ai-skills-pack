# Changelog

## Unreleased

### Added
- AI OS core architecture, agent and prompt registries, specification and memory templates, project starters, standards, knowledge hub, platform references, validation scripts, and GitHub validation workflow.
- Phase 1 deterministic skill-registry generation, repository indexing, unified continuous validation, JSON schemas, and unit tests.
- One-command project bootstrap with starter discovery, `project.yaml`, overwrite protection, and optional Git initialization.
- Phase 2 Memory Engine with structured memory folders, memory schema, source registry, deterministic generated memory indexes, memory add/list/search/archive/promote scripts, security scanning, and dedicated memory tests.
- Phase 3 Knowledge Graph with deterministic local graph generation, standalone build/validate/check commands, generated knowledge graph artifacts, and dedicated Knowledge Graph tests.
- Phase 4 Semantic Discovery with local query engine, deterministic search ranking, graph traversal (BFS, shortest path, neighbors), term-based inverted index, type/path/relationship filtering, explain and stats commands, standalone build/validate/check scripts, generated discovery artifacts, and 63 dedicated tests.
- Phase 5 Interactive Dashboard with local HTTP server, overview/skills/memory/graph/discovery/repository views, SVG knowledge-graph visualization with force-directed layout, dark/light mode, responsive layout, keyboard accessibility, live API endpoints, dashboard build/validate/check scripts, and 80 dedicated tests.
- Phase 6 MCP Integration with protocol-neutral service layer, MCP-compatible stdio server, 15 tools, 9 resources, repository-root confinement, path traversal rejection, secret-file blocking, memory redaction, bounded excerpts, traversal depth limits, read-only default, smoke test utility, client configuration examples, and 73 dedicated tests.
- Phase 7 Release Hardening with unified CLI, one-command bootstrap, environment doctor, configuration system, build orchestration in dependency order, release packaging (zip/tar with checksums), backup/restore, safe clean, migration framework, cross-platform wrappers, semantic versioning, release-check command, and 44 dedicated tests.
- Phase 8 Continuous Learning and Agent Orchestration with a generated agent registry and workflow registry, deterministic task classification, knowledge-retrieval planning, local session tracking with an explicit status-transition graph, an approval engine with no auto-approve path, memory-suggestion generation gated on explicit approval, knowledge-gap and freshness detection, local feedback capture, a hash-chained audit trail, 14 new read-only MCP tools and 8 new resources, 8 new dashboard pages, and 158 dedicated tests.

### Changed
- Evolved the AI Skills Pack README into the AI OS entry point while preserving its reusable-skill purpose.
- Normalized existing skill metadata without moving or deleting skills.
- Updated continuous integration to check generated artifacts and run unified validation plus unit tests with read-only permissions.
- Updated validation and workflow documentation to include memory structure checks, generated memory index freshness checks, and memory security scanning.
- Extended unified and CI validation to include knowledge graph freshness and structure checks.
- Extended unified and CI validation to include discovery index freshness and structure checks.
- Extended unified and CI validation to include dashboard freshness and structure checks.
- Extended unified and CI validation to include MCP smoke test.
- Extended unified and CI validation to include bootstrap and release-check commands.

### Fixed
- Added useful content to the previously empty analytical skill.

### Deprecated
None.

### Removed
None.

### Security
- Added security policy, secret-aware validation, and ignore patterns.
- Added memory-specific security controls and masked secret-pattern reporting for memory source records.
