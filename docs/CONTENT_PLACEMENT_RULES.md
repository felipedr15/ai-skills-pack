# Content placement rules

[Structure](REPOSITORY_STRUCTURE.md) · [Start here](../README.md)

| If the content is… | Put it in… | Keep out of… |
| --- | --- | --- |
| Repository setup, architecture, roadmap, workflow, governance, release history | `docs/` and its named subfolder | Root, except entry and required integration files |
| A supporting reference or source used by contributors or tooling | `references/` | `docs/` when it is not repository guidance |
| A human reference handout about using this repository | `docs/reference/` | Root |
| Reusable subject knowledge | `knowledge/` | `memory/` if it has no changing owner/state |
| Current project or session context, decisions, lessons, preferences | `memory/` | `knowledge/` when its status changes over time |
| Binding conventions or quality rules | `standards/` | `specs/` |
| Requirements/design/tasks for a particular feature | `specs/` | `standards/` |
| Machine readable validation shape | `schemas/` | Prose only in `specs/` |
| Reusable blank starting point | `templates/` | `examples/` |
| Filled in sample implementation | `examples/` | `templates/` |
| Generated index, registry, or dashboard | `generated/` | Source folders; regenerate using `generated/README.md` |

Keep registry metadata and its target file aligned: `agents.json` indexes `agents/`, `prompts.json` indexes `prompts/`, and `skills.json` is retained for legacy compatibility while `.agent/skills/**/SKILL.md` front matter drives generated skill artifacts. Do not infer that all three JSON files are generated.

Before moving any file, search for its path in scripts, tests, workflow files, registries, and Markdown links. Update consumers and rerun validation. Do not reorganize `.github/`, `.agent/`, `.kiro/`, or root tool config files without verifying their integrations.
