# Contributing

Use lowercase, hyphenated folders, stable IDs, predictable filenames, and valid metadata. Before adding a skill, agent, prompt, starter, or specification, inspect existing content to prevent duplication. Skill front matter is authoritative; never hand-edit files under `generated/`. Keep agent and prompt registries aligned with actual relative paths.

Skills need complete front matter, a folder README, tests or examples when applicable, and a changelog entry. Agents and prompts must name inputs, outputs, skills, restrictions, and handoffs. Starters must preserve the required project-memory contract. Specifications require traceable requirements, design, tasks, and validation.

After source changes, run `python scripts/generate-skill-registry.py` and `python scripts/index-repository.py`. Their `--check` modes fail without writing when derived files are stale. Run `python scripts/validate-all.py` before review. Never include secrets or unrelated changes. Pull requests should describe scope, requirement coverage, tests, risks, documentation, changelog impact, and human validation.

Create projects with `python scripts/create-project.py --name "Name" --type TYPE --destination PATH`; use `--list-types` to discover starters. Phase 2 automation remains proposed and must not be described as implemented.
