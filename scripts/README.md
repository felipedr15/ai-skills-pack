# Scripts

Validation, registry listing, and safe project creation tools use built-in runtimes and perform no Git operations.

Memory Engine scripts:

- `memory-add.py`
- `memory-list.py`
- `memory-search.py`
- `memory-archive.py`
- `memory-promote.py`
- `generate-memory-index.py`
- `validate-memory-security.py`

Knowledge Graph scripts:

- `generate-knowledge-graph.py`
- `validate-knowledge-graph.py`
- `knowledge-build.py`
- `knowledge-validate.py`
- `knowledge-check.py`
- `knowledge_graph/` (internal modules)

Semantic Discovery scripts:

- `discover.py` (interactive query CLI)
- `discovery-build.py`
- `discovery-validate.py`
- `discovery-check.py`
- `semantic_discovery/` (internal modules)

Dashboard scripts:

- `dashboard-build.py`
- `dashboard-serve.py`
- `dashboard-validate.py`
- `dashboard-check.py`
- `dashboard/` (internal modules)

MCP Integration scripts:

- `mcp-server.py` (MCP stdio server)
- `mcp-smoke-test.py` (automated smoke test)
- `ai_os_service/` (protocol-neutral service layer)
- `mcp_server/` (MCP adapter modules)

Release and Bootstrap scripts:

- `ai-os.py` (unified CLI)
- `release/` (release package modules)

Orchestration scripts (Phase 8):

- `generate-agent-registry.py`
- `generate-workflow-registry.py`
- `generate-knowledge-health.py`
- `orchestration-validate.py`
- `orchestration/` (internal modules: registry, workflow, router, planner, session, approvals,
  memory_suggestions, feedback, knowledge_gaps, freshness, audit, render, validate, models, utils)

`ai-os.py` gains Phase 8 command groups that use nested subparsers (e.g. `session start`,
`approval approve <id>`) rather than the flat top-level style of earlier commands, since these
are multi-verb groups — see `python scripts/ai-os.py help`.

[Back to AI OS](../README.md)
