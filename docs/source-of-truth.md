# Source of Truth

This document defines what content is **authoritative** in the repository and what is **derived**. When content exists in both a folder and a registry file, this clarifies which is the source.

## Core Principle

**Authored content in folders is authoritative.** Registry files (`*.json` files) are registration indexes that must be kept in sync with folder content.

## Agents

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Role instructions | `agents/*.md` | **Yes** | Each agent is a markdown file with YAML front matter |
| Agent registry | `agents.json` | No (derived) | Manually maintained index; must match folder contents |
| ID and metadata | Front matter in `agents/*.md` | **Yes** | YAML front matter is the source of IDs, descriptions, and tool restrictions |

**When changing an agent:**
1. Edit the `.md` file under `agents/`
2. Update `agents.json` to match
3. Run `python scripts/generate-agent-registry.py` to regenerate derived indexes

---

## Skills

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Skill content | `.agent/skills/*/SKILL.md` | **Yes** | Each skill is a markdown file with YAML front matter in `.agent/skills/` |
| Skill metadata | YAML front matter in `SKILL.md` | **Yes** | Front matter drives the generated skill registry |
| Root `skills.json` | `skills.json` | No (legacy) | Compatibility registry; use front matter instead |
| Generated skill index | `generated/skills-registry.json` | No (derived) | Regenerated from `SKILL.md` front matter |
| Supporting content | `skills/*/` | No (supplementary) | Optional supporting files; not required for registration |

**When adding or changing a skill:**
1. Create or edit `.agent/skills/SKILL_NAME/SKILL.md` with complete front matter
2. Optionally add supporting content to `skills/SKILL_NAME/`
3. Run `python scripts/generate-skill-registry.py` to rebuild indexes
4. Use `--check` flag to verify before committing

---

## Prompts

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Prompt text | `prompts/*.md` or `prompts/*/prompt.md` | **Yes** | Prompt content lives in markdown files |
| Prompt registry | `prompts.json` | No (manual index) | Manually maintained index; must match folder contents |
| Metadata | File path and filename | **Yes** | ID and category are inferred from folder structure |

**When adding or changing a prompt:**
1. Create or edit prompt markdown under `prompts/`
2. Update `prompts.json` to register the new or changed prompt
3. The registry maps prompt IDs to file paths

---

## Memory

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Memory records | `memory/*.md` files | **Yes** | Each record is authored markdown with metadata |
| Memory schema | `schemas/memory.schema.json` | **Yes** | Defines valid record types and fields |
| Memory registry | `memory/registry.json` | **Yes** | Manually maintained index of all records; must stay aligned |
| Generated memory index | `generated/memory-index.json` | No (derived) | Regenerated from `memory/registry.json` |
| Generated memory graph | `generated/memory-graph.json` | No (derived) | Regenerated to show relationships |

**When adding or changing a memory record:**
1. Create or edit `.md` file under `memory/` (use `python scripts/memory-add.py` for consistency)
2. Update `memory/registry.json` with the record ID and metadata
3. Run `python scripts/generate-memory-index.py` to rebuild indexes
4. Run `python scripts/validate-memory-security.py` to check for secrets

**Memory governance:**
- Source records under `memory/` are **authoritative**
- Outputs under `generated/` are **derived** and should be rebuilt
- `.ai-os/` is **local runtime state** and never committed
- Never hand-edit generated files

---

## Knowledge & References

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Curated knowledge | `knowledge/` (markdown files) | **Yes** | Subject-matter knowledge organized by topic |
| Knowledge graph | `generated/knowledge-graph.json` | No (derived) | Regenerated to show topic relationships |
| Supporting references | `references/` | **Yes** | External resources and reference material; can be linked from knowledge topics |
| Knowledge health index | `generated/knowledge-health.json` | No (derived) | Derived from source knowledge; shows freshness and coverage |

**Content model:**
- `knowledge/` holds **reusable information** organized by subject
- `references/` holds **supporting resources** that knowledge topics cite
- Organize both by topic or domain (e.g., `knowledge/agents/`, `knowledge/memory/`)

---

## Standards, Specs, and Schemas

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Standards | `standards/*.md` | **Yes** | Conventions and best practices |
| Specifications | `specs/*.md` | **Yes** | Feature requirements and design docs |
| Schemas | `schemas/*.json` | **Yes** | JSON schema definitions for validation |

These are **all authoritative** and should not be auto-generated. Edit them directly.

---

## Templates and Examples

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Project templates | `templates/` | **Yes** | Starter project structures |
| Example content | `examples/` | **Yes** | Completed samples demonstrating best practices |

Both are **authored content** and should be maintained manually. Use them as models for new contributions.

---

## Configuration & Generated Content

| Aspect | Location | Authoritative? | Notes |
| --- | --- | --- | --- |
| Wrangler config | `wrangler.jsonc` | **Yes** | Tool configuration; edit directly |
| Bootstrap scripts | `bootstrap.sh`, `bootstrap.ps1` | **Yes** | Setup automation; edit directly |
| Generated indexes | `generated/*.json` | No (derived) | Regenerate after source changes; **never hand-edit** |
| Generated dashboards | `generated/*.html` | No (derived) | Regenerate after source changes; **never hand-edit** |

**Workflow:**
1. Make changes to source files (agents, skills, prompts, memory, knowledge)
2. Run the appropriate generation script (see [CONTRIBUTING.md](../CONTRIBUTING.md) for commands)
3. Verify changes with validation scripts
4. Commit both source and generated changes

---

## Manifest Registry Alignment

When a source file is added, moved, or renamed, **update the corresponding registry immediately**:

| Source | Registry | Generator |
| --- | --- | --- |
| `agents/*.md` | `agents.json` | `generate-agent-registry.py` |
| `.agent/skills/*/SKILL.md` | `generated/skills-registry.json` | `generate-skill-registry.py` |
| `prompts/*` | `prompts.json` | (manual for now) |
| `memory/*.md` | `memory/registry.json` | `generate-memory-index.py` |
| `profile/*.md` | `profile/registry.json` | `generate-profile-index.py` |

**Before committing:**
- Verify that folder content and registry are aligned
- Run the relevant generator scripts
- Use `--check` mode to validate without writing
- Run `python scripts/validate-all.py` to catch misalignment

---

## Derived vs. Authored: Reference Table

| File/Folder | Authored | Derived | Maintenance |
| --- | --- | --- | --- |
| `agents/` | ✓ | | Edit directly; update `agents.json` |
| `agents.json` | | ✓ | Keep in sync with `agents/` |
| `.agent/skills/*/SKILL.md` | ✓ | | Edit directly; front matter is authoritative |
| `skills/` | ✓ | | Supporting content (optional) |
| `skills.json` | | ✓ | Legacy; use front matter instead |
| `prompts/` | ✓ | | Edit directly; update `prompts.json` |
| `prompts.json` | ✓ | | Manually maintained registry |
| `memory/` | ✓ | | Edit directly; update `memory/registry.json` |
| `memory/registry.json` | ✓ | | Manually maintained registry |
| `knowledge/` | ✓ | | Edit directly; no registry needed |
| `references/` | ✓ | | Edit directly; cite from knowledge |
| `standards/` | ✓ | | Edit directly; no registry needed |
| `specs/` | ✓ | | Edit directly; no registry needed |
| `schemas/` | ✓ | | Edit directly; JSON schema files |
| `templates/` | ✓ | | Edit directly; starter content |
| `examples/` | ✓ | | Edit directly; sample content |
| `generated/` | | ✓ | Regenerate from source; never hand-edit |
| `profile/` | ✓ | | Edit directly; update `profile/registry.json` |
| `profile/registry.json` | ✓ | | Manually maintained registry |
| `config/`, `.github/` | ✓ | | Configuration; edit directly |
| `scripts/` | ✓ | | Automation; edit directly |

---

## Summary

**Remember:**
1. **Folders + markdown = authoritative** — Edit `.md` files under `agents/`, `.agent/skills/`, `prompts/`, `memory/`, etc.
2. **Registry files must be kept in sync** — When you add/change/remove source, update the corresponding `.json` registry
3. **Generated content should not be hand-edited** — Run generator scripts instead; use `--check` to verify
4. **Validation before commit** — Run validators to catch misalignment and stale generated indexes
5. **Refer to [CONTRIBUTING.md](../CONTRIBUTING.md) for exact commands** — Generator and validator scripts are documented there

When in doubt, run `python scripts/ai-os.py validate` to check for alignment issues.
