# Phase 3 Knowledge Graph Architecture

## Purpose

Describe the local deterministic Knowledge Graph introduced in Phase 3.

## Source-of-Truth Policy

Source Markdown and JSON files remain authoritative. Generated graph artifacts are derived outputs and never sources of truth.

## Inputs

- Skill definitions under `.agent/skills/**/SKILL.md`
- Memory records under `memory/`
- Project and repository documentation
- Supplemental generated registries where useful for linking

## Outputs

- `generated/knowledge-graph.json`
- `generated/knowledge-graph.md`

## Node Types

- `skill`
- `memory`
- `project`
- `document`
- `platform`
- `tool`
- `concept`

## Edge Types

- `contains`
- `references`
- `related_to`
- `supports`
- `uses`
- `belongs_to`
- `generated_from`

## Determinism and Safety

- IDs are deterministic and path-based where applicable.
- Paths are normalized to forward slashes.
- Staleness checks ignore `generatedAt` only.
- Secret-like files and excluded directories are skipped.
- No network requests are performed.

## Commands

```text
python scripts/generate-knowledge-graph.py
python scripts/validate-knowledge-graph.py
python scripts/generate-knowledge-graph.py --check
```

[Back to architecture knowledge](README.md)
