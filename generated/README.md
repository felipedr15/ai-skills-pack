# Generated Artifacts

Files in this directory are deterministic outputs, never sources of truth.

- `skills.json` and `skills.md` come from `SKILL.md` front matter.
- `repository-index.json` and `repository-map.md` come from repository source paths.

Regenerate them with:

```text
python scripts/generate-skill-registry.py
python scripts/index-repository.py
```

Use `--check` with either command to detect missing or stale output without modifying files.

[Back to AI OS](../README.md)
