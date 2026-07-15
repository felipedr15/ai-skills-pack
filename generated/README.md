# Generated Artifacts

Files in this directory are deterministic outputs, never sources of truth.

- `skills.json` and `skills.md` come from `SKILL.md` front matter.
- `repository-index.json` and `repository-map.md` come from repository source paths.
- `memory-index.json` and `memory-index.md` come from source memory records.
- `knowledge-graph.json` and `knowledge-graph.md` come from repository source entities and relationships.
- `discovery-index.json` and `discovery-index.md` come from the knowledge graph and source file metadata.
- `agent-registry.json` and `agent-registry.md` come from `agents/*.md` and `agents.json` (Phase 8).
- `workflow-registry.json` and `workflow-registry.md` come from `knowledge/workflows/*.json` (Phase 8).
- `knowledge-health.json` and `knowledge-health.md` come from the knowledge graph, discovery index, skill/memory/workflow registries, and freshness metadata — a deterministic, repo-only snapshot. It never embeds local session or feedback content; the live view (with session/feedback signal overlaid) is only available via `ai-os.py knowledge-health` / `knowledge-gaps` and the dashboard, never committed (Phase 8).
- `dashboard.html` and `dashboard-data.json` come from all generated JSON artifacts.

Regenerate them with:

```text
python scripts/generate-skill-registry.py
python scripts/index-repository.py
python scripts/generate-memory-index.py
python scripts/generate-knowledge-graph.py
python scripts/discovery-build.py
python scripts/generate-agent-registry.py
python scripts/generate-workflow-registry.py
python scripts/generate-knowledge-health.py
python scripts/dashboard-build.py
```

Use `--check` with the registry, index, and graph commands or run `discovery-check.py` / `orchestration-validate.py` to detect missing or stale output without modifying files.

[Back to AI OS](../README.md)
