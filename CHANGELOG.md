# Changelog

## Unreleased

### Added
- AI OS core architecture, agent and prompt registries, specification and memory templates, project starters, standards, knowledge hub, platform references, validation scripts, and GitHub validation workflow.
- Phase 1 deterministic skill-registry generation, repository indexing, unified continuous validation, JSON schemas, and unit tests.
- One-command project bootstrap with starter discovery, `project.yaml`, overwrite protection, and optional Git initialization.
- Phase 2 Memory Engine with structured memory folders, memory schema, source registry, deterministic generated memory indexes, memory add/list/search/archive/promote scripts, security scanning, and dedicated memory tests.
- Phase 3 Knowledge Graph with deterministic local graph generation, standalone build/validate/check commands, generated knowledge graph artifacts, and dedicated Knowledge Graph tests.

### Changed
- Evolved the AI Skills Pack README into the AI OS entry point while preserving its reusable-skill purpose.
- Normalized existing skill metadata without moving or deleting skills.
- Updated continuous integration to check generated artifacts and run unified validation plus unit tests with read-only permissions.
- Updated validation and workflow documentation to include memory structure checks, generated memory index freshness checks, and memory security scanning.
- Extended unified and CI validation to include knowledge graph freshness and structure checks.

### Fixed
- Added useful content to the previously empty analytical skill.

### Deprecated
None.

### Removed
None.

### Security
- Added security policy, secret-aware validation, and ignore patterns.
- Added memory-specific security controls and masked secret-pattern reporting for memory source records.
