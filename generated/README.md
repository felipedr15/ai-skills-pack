# Generated Artifacts

Files in this directory are deterministic outputs, never sources of truth.

- `skills.json` and `skills.md` come from `SKILL.md` front matter.
- `repository-index.json` and `repository-map.md` come from repository source paths.
- `memory-index.json` and `memory-index.md` come from source memory records.
- `knowledge-graph.json` and `knowledge-graph.md` come from repository source entities and relationships.

Regenerate them with:

```text
python scripts/generate-skill-registry.py
python scripts/index-repository.py
python scripts/generate-memory-index.py
python scripts/generate-knowledge-graph.py
```

Use `--check` with either command to detect missing or stale output without modifying files.

[Back to AI OS](../README.md)
