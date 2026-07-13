# AI OS MCP Server Configuration

## Overview

The AI OS MCP server exposes repository knowledge, skills, memory summaries, semantic search, and graph traversal through the Model Context Protocol over stdio transport.

The server is read-only by default. No external dependencies are required beyond Python 3.10+.

## Startup Command

```bash
python <REPOSITORY_ROOT>/scripts/mcp-server.py
```

The server reads JSON-RPC 2.0 messages from stdin and writes responses to stdout.

## Client Configuration

### Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "ai-os": {
      "command": "<PYTHON_EXECUTABLE>",
      "args": ["<REPOSITORY_ROOT>/scripts/mcp-server.py"],
      "disabled": false
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-os": {
      "command": "<PYTHON_EXECUTABLE>",
      "args": ["<REPOSITORY_ROOT>/scripts/mcp-server.py"]
    }
  }
}
```

### VS Code MCP Clients

For VS Code extensions that support MCP, configure the server command:

```json
{
  "command": "<PYTHON_EXECUTABLE>",
  "args": ["<REPOSITORY_ROOT>/scripts/mcp-server.py"]
}
```

## Platform Examples

### Windows

```json
{
  "command": "python",
  "args": ["C:/Users/username/repos/ai-skills-pack/scripts/mcp-server.py"]
}
```

### macOS / Linux

```json
{
  "command": "python3",
  "args": ["/home/username/repos/ai-skills-pack/scripts/mcp-server.py"]
}
```

## Registered Tools (15)

| Tool | Description |
|------|-------------|
| `ai_os_status` | Repository status and artifact availability |
| `search_ai_os` | Semantic search across the repository |
| `explain_search_result` | Explain why an entity matches a query |
| `get_entity` | Get a knowledge graph entity |
| `get_related_entities` | Get related entities |
| `traverse_knowledge_graph` | BFS traversal from a node |
| `find_knowledge_path` | Shortest path between two nodes |
| `list_skills` | List registered skills |
| `get_skill` | Get skill details |
| `list_memory_summaries` | List memory summaries (no full content) |
| `get_memory_summary` | Get a memory record summary |
| `get_repository_file` | Safe bounded file excerpt |
| `get_validation_status` | Validation status |
| `list_generated_artifacts` | Generated artifact status |
| `get_dashboard_status` | Dashboard availability |

## Registered Resources (9)

| URI | Description |
|-----|-------------|
| `ai-os://status` | Repository status |
| `ai-os://architecture` | Architecture document |
| `ai-os://repository-map` | Repository file map |
| `ai-os://skills` | Skill registry summary |
| `ai-os://memory-summary` | Memory index summary |
| `ai-os://knowledge-graph` | Knowledge graph summary |
| `ai-os://discovery` | Discovery index summary |
| `ai-os://dashboard` | Dashboard status |
| `ai-os://validation` | Validation status |

## Verification

### Tool List

After connecting, verify tools are registered:

```
Method: tools/list
Expected: 15 tools returned
```

### Resource List

```
Method: resources/list
Expected: 9 resources returned
```

### Sample Search

```json
{"method": "tools/call", "params": {"name": "search_ai_os", "arguments": {"query": "knowledge graph"}}}
```

### Sample Traversal

```json
{"method": "tools/call", "params": {"name": "traverse_knowledge_graph", "arguments": {"entity_id": "concept:validation", "depth": 2}}}
```

### Path Rejection (Expected)

```json
{"method": "tools/call", "params": {"name": "get_repository_file", "arguments": {"source_path": "../outside.txt"}}}
```

Expected response includes `"error": "path_rejected"`.

### Secret File Rejection (Expected)

```json
{"method": "tools/call", "params": {"name": "get_repository_file", "arguments": {"source_path": ".env"}}}
```

Expected response includes `"error": "path_rejected"`.

## Smoke Test

Run the automated smoke test:

```bash
python <REPOSITORY_ROOT>/scripts/mcp-smoke-test.py
```

This verifies all tools, resources, security boundaries, and clean shutdown.

## Troubleshooting

- **Server not starting**: Ensure Python 3.10+ is available and the repository root contains `generated/` artifacts.
- **Tools returning errors**: Run `python scripts/validate-all.py` to check artifact freshness.
- **Missing search results**: Rebuild indexes with `python scripts/discovery-build.py`.
- **Permission errors**: The server is read-only. No write operations are available by default.

## Security

- Read-only by default
- No network calls
- No telemetry
- Repository-root confinement
- Path traversal rejected
- Secret files blocked
- Memory summaries only (never full content)
- Bounded file excerpts (max 2000 chars)
- Traversal depth capped at 5
- No arbitrary shell execution
- No Git operations
