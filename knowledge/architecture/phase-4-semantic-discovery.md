# Phase 4 Semantic Discovery Architecture

## Purpose

Describe the local deterministic Semantic Discovery and Query Engine introduced in Phase 4.

## Source-of-Truth Policy

Source Markdown and JSON files remain authoritative. The discovery index is a derived compact artifact that references source paths and graph node IDs. It does not duplicate source content and must never become a source of truth.

## Inputs

- Knowledge graph (`generated/knowledge-graph.json`)
- Source Markdown and JSON files across the repository
- Memory records under `memory/`
- Skill definitions under `.agent/skills/**/SKILL.md`
- Knowledge articles under `knowledge/`

## Outputs

- `generated/discovery-index.json`
- `generated/discovery-index.md`

## Query Modes

- **search** — keyword/phrase search with scoring and filtering
- **related** — direct graph neighbors of a node
- **traverse** — breadth-first traversal from a node with depth control
- **path** — shortest relationship path between two nodes
- **explain** — why a node matches a given query
- **stats** — discovery index statistics

## Ranking Model

Deterministic scoring with factors:

- Exact name match (100)
- Phrase in name (60)
- Title phrase match (50)
- Heading phrase match (30)
- Node type match (25)
- Name token match (20)
- Snippet phrase match (20)
- Title token match (15)
- Direct graph relationship (15)
- Metadata match (12)
- Heading token match (10)
- Source path token match (8)
- Snippet token match (5)

Stable tie-breaking: score descending, type, normalized name, ID.

## Tokenization

Standard library only. Supports:

- Lowercase normalization
- Punctuation removal
- Hyphenated-term splitting
- snake_case splitting
- camelCase splitting
- Technical term preservation (GitHub, PowerShell, MCP, etc.)

## Graph Traversal

- BFS with cycle protection
- Configurable depth (default 2, max 5)
- Relationship-type filtering
- Inbound and outbound edge exploration
- Shortest-path via BFS

## Security

- Secret-like files excluded from indexing
- No full source content stored
- Snippets limited to 200 characters
- Reuses existing repository ignore rules and secret detection

## Commands

```text
python scripts/discover.py search "query"
python scripts/discover.py related <node-id>
python scripts/discover.py traverse <node-id> --depth 2
python scripts/discover.py path <source-id> <target-id>
python scripts/discover.py explain <node-id> "query"
python scripts/discover.py stats

python scripts/discovery-build.py
python scripts/discovery-validate.py
python scripts/discovery-check.py
```

## Adding New Searchable Fields

1. Add extraction logic in `scripts/semantic_discovery/extract.py`
2. Include the field in document or entity construction in `index.py`
3. Add tokenization in `_build_term_index` in `index.py`
4. Optionally add scoring weight in `rank.py`
5. Rebuild: `python scripts/discovery-build.py`

## Future Integration

Dashboard or MCP layers can consume `generated/discovery-index.json` as a read-only data source. The CLI commands can be wrapped in MCP tools for interactive AI-assisted discovery without network dependencies.

[Back to architecture knowledge](README.md)
