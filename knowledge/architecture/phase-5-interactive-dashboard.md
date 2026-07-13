# Phase 5 Interactive Dashboard Architecture

## Purpose

Document the local interactive dashboard introduced in Phase 5 for exploring AI OS repository state.

## Source-of-Truth Policy

Source Markdown and JSON files remain authoritative. The dashboard reads generated artifacts and displays aggregated views. Dashboard outputs (`dashboard.html`, `dashboard-data.json`) are derived and non-authoritative.

## Startup Commands

```text
python scripts/dashboard-build.py            # Generate dashboard artifacts
python scripts/dashboard-serve.py            # Start server (opens browser)
python scripts/dashboard-serve.py --port 9000 --no-browser   # Custom port
```

Default URL: `http://127.0.0.1:8080`

## Development Commands

```text
python scripts/dashboard-build.py            # Rebuild after changes
python scripts/dashboard-validate.py         # Validate structure
python scripts/dashboard-check.py            # Check staleness
python -m unittest tests.test_dashboard -v   # Run dashboard tests
```

## Production Build

The dashboard is a self-contained HTML file with embedded data. Build it with `dashboard-build.py` and open `generated/dashboard.html` directly in a browser (no server required for static view). The server adds live API endpoints for interactive filtering and search.

## Data Sources

| Artifact | Provides |
|----------|----------|
| `generated/repository-index.json` | File categories, counts, sizes |
| `generated/skills.json` | Skill registry with metadata |
| `generated/memory-index.json` | Memory records, types, status |
| `generated/knowledge-graph.json` | Nodes, edges, relationships |
| `generated/discovery-index.json` | Documents, entities, terms |

## Dashboard Pages

1. **Overview** - Summary cards, artifact status table, staleness warnings
2. **Skills** - Search, path filter, category filter, metadata table
3. **Memory** - Type/status/project filters, summaries only, related graph entities
4. **Knowledge Graph** - Node list, edge list, type filters, node detail with inbound/outbound
5. **Graph Viz** - SVG force-directed visualization, type filters, depth control, neighbor highlighting
6. **Discovery** - Search with scoring, type/path filters, match reasons, explain view
7. **Repository** - Category breakdown, file search, size display

## Graph Visualization

- SVG-based force-directed layout (vanilla JavaScript, no library)
- 80-iteration physics simulation with repulsion, attraction, and center gravity
- Node coloring by type (7 distinct colors)
- Maximum 50 nodes per view to prevent performance issues
- BFS neighbor expansion with configurable depth (1-3, max 3)
- Focus on a node to explore its neighborhood
- Click or keyboard-select nodes for detail view
- Neighbor and edge highlighting
- Fallback table when visualization cannot render
- Falls back to top-connected-by-degree when no focus node specified

## Security Model

- All rendered text escaped (HTML entities)
- No raw HTML from repository files rendered
- No secrets displayed
- No full memory contents (summaries only)
- No network calls outside localhost
- No external CDN or remote resources
- No telemetry or analytics
- No authentication (local-only access)
- Source paths validated (no absolute paths, no traversal)
- Secret-like files excluded from all data sources

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Health check |
| `GET /api/data` | Full aggregated dashboard data |
| `GET /api/skills` | Skills with search/filter |
| `GET /api/memory` | Memory records with filters |
| `GET /api/graph/nodes` | Graph nodes with type/search |
| `GET /api/graph/edges` | Graph edges with type/node filter |
| `GET /api/graph/node/{id}` | Node detail with relationships |
| `GET /api/graph/visualize` | Subgraph for visualization |
| `GET /api/discovery/search` | Semantic search |
| `GET /api/discovery/explain/{id}` | Scoring explanation |
| `GET /api/repository` | Repository files with filters |

## Troubleshooting

- **Dashboard not built**: Run `python scripts/dashboard-build.py`
- **Stale dashboard**: Regenerate with `dashboard-build.py` after source changes
- **Port in use**: Use `--port` flag to specify a different port
- **Graph too large**: The visualization automatically limits to 50 nodes
- **Missing artifacts**: Check `validate-all.py` output for which builds need to run
- **Server won't start**: Ensure no other process is using the port

## Future Extension Points

- Additional visualization layouts (hierarchical, radial)
- Real-time file watching for auto-rebuild
- MCP tool integration for AI-assisted exploration
- Skill dependency visualization
- Memory timeline view
- Graph diff between branches
- Export views as PDF/PNG
- WebSocket for live updates during builds

[Back to architecture knowledge](README.md)
