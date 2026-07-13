# Contributing

Use lowercase, hyphenated folders, stable IDs, predictable filenames, and valid metadata. Before adding a skill, agent, prompt, starter, or specification, inspect existing content to prevent duplication. Skill front matter is authoritative; never hand-edit files under `generated/`. Keep agent and prompt registries aligned with actual relative paths.

Memory records must follow `schemas/memory.schema.json`, live under `memory/`, and be registered in `memory/registry.json`. Source memory records are authoritative; generated memory indexes are derived outputs.

Skills need complete front matter, a folder README, tests or examples when applicable, and a changelog entry. Agents and prompts must name inputs, outputs, skills, restrictions, and handoffs. Starters must preserve the required project-memory contract. Specifications require traceable requirements, design, tasks, and validation.

After source changes, run `python scripts/generate-skill-registry.py`, `python scripts/index-repository.py`, and `python scripts/generate-memory-index.py` when memory data changes. Their `--check` modes fail without writing when derived files are stale. Run `python scripts/validate-memory-security.py` and `python scripts/validate-all.py` before review. Never include secrets or unrelated changes. Pull requests should describe scope, requirement coverage, tests, risks, documentation, changelog impact, and human validation.

Create projects with `python scripts/create-project.py --name "Name" --type TYPE --destination PATH`; use `--list-types` to discover starters.

Memory command examples:

```text
python scripts/memory-add.py --type lesson --title "Example" --scope global --summary "..."
python scripts/memory-list.py --type lesson
python scripts/memory-search.py "keyword"
python scripts/memory-archive.py --id lesson-example-001
python scripts/memory-promote.py --id session-example-001 --target-type lesson --reason "Reusable finding"
```
