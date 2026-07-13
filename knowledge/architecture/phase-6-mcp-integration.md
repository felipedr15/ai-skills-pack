# Phase 6 MCP Integration Architecture

## Purpose

Document the protocol-neutral service layer and MCP server introduced in Phase 6.

## Source-of-Truth Policy

Source files remain authoritative. The MCP server reads generated artifacts and provides read-only access. No write operations are available by default.

## Architecture

Two layers:

1. **Protocol-neutral service** (`scripts/ai_os_service/`) — reusable business logic with input validation, structured errors, pagination, and security boundaries.
2. **MCP adapter** (`scripts/mcp_server/`) — maps MCP JSON-RPC 2.0 requests to service operations over stdio transport.

## Tools (15)

| Tool | Description |
|------|-------------|
| `ai_os_status` | Repository and artifact status |
| `search_ai_os` | Semantic search |
| `explain_search_result` | Scoring explanation |
| `get_entity` | Knowledge graph node |
| `get_related_entities` | Node neighbors |
| `traverse_knowledge_graph` | BFS traversal |
| `find_knowledge_path` | Shortest path |
| `list_skills` | Skill registry |
| `get_skill` | Skill details |
| `list_memory_summaries` | Memory summaries |
| `get_memory_summary` | Single memory summary |
| `get_repository_file` | Safe file excerpt |
| `get_validation_status` | Validation state |
| `list_generated_artifacts` | Artifact status |
| `get_dashboard_status` | Dashboard status |

## Resources (9)

Stable URIs prefixed with `ai-os://` providing architecture, repository map, skills, memory, knowledge graph, discovery, dashboard, and validation summaries.

## Security Boundaries

- Repository-root confinement
- Path traversal rejection
- Secret-file blocking (.env, .pem, .key, .pfx, .p12)
- Blocked directories (.git, .venv, node_modules, etc.)
- Memory redaction (summaries only, never full content)
- Bounded file excerpts (max 2000 chars)
- Traversal depth cap (max 5)
- Result count limits (max 100)
- No subprocess execution from client values
- No Git operations
- No network calls
- No telemetry
- Read-only by default

## Startup

```text
python scripts/mcp-server.py
```

## Smoke Test

```text
python scripts/mcp-smoke-test.py
```

## Client Configuration

See `examples/mcp/README.md` for Kiro, Claude Desktop, and VS Code setup.

## Future Extension Points

- Official MCP SDK integration when stable
- Optional controlled write operations (disabled by default)
- SSE transport for HTTP-based clients
- Tool discovery from skill metadata
- Dynamic resource generation from graph queries

[Back to architecture knowledge](README.md)
