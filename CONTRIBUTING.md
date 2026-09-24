# Contributing

Welcome! This guide explains how to contribute to `ai-skills-pack`. Start with [CONTENT_PLACEMENT_RULES.md](docs/CONTENT_PLACEMENT_RULES.md) to understand where content belongs, then follow the checklist below for your contribution type.

## Quick Reference

**Before you start:**
1. Read [CONTENT_PLACEMENT_RULES.md](docs/CONTENT_PLACEMENT_RULES.md) to understand where content belongs
2. Inspect existing similar content to prevent duplication
3. Follow the [source-of-truth](docs/source-of-truth.md) rules for your content type

**When you're ready to submit:**
1. Run validation scripts (see [Validation Checklist](#validation-checklist) below)
2. Write a clear PR description with scope, risks, and changes
3. Include human validation where applicable
4. Never commit secrets or unrelated changes

---

## Contribution Types

### Adding a Skill

Skills live in `.agent/skills/` with front matter, a README, and optionally examples.

**Checklist:**
- [ ] Create `.agent/skills/CATEGORY/SKILL_NAME/SKILL.md` with complete YAML front matter
- [ ] Add folder `skills/SKILL_NAME/` for supporting content (optional)
- [ ] Include folder README documenting the skill
- [ ] Add tests or examples when applicable
- [ ] Add changelog entry
- [ ] Run `python scripts/generate-skill-registry.py`

**Authority:** Skill front matter in `SKILL.md` is authoritative; generated registry is derived.

---

### Adding an Agent

Agents live in `agents/` with front matter defining role, inputs, outputs, skills, and handoffs.

**Checklist:**
- [ ] Create `agents/AGENT_NAME.md` with YAML front matter
- [ ] Define inputs, outputs, tool restrictions, and handoffs
- [ ] Update `agents.json` to register the new agent
- [ ] Run `python scripts/generate-agent-registry.py`

**Authority:** Agent `*.md` files and manually maintained `agents.json` are authoritative.

---

### Adding a Prompt

Prompts live in `prompts/` organized by category.

**Checklist:**
- [ ] Create `prompts/CATEGORY/PROMPT_NAME.md` or `prompts/CATEGORY/PROMPT_NAME/prompt.md`
- [ ] Update `prompts.json` to register the prompt
- [ ] Document the prompt's purpose and usage

**Authority:** Prompt markdown files and manually maintained `prompts.json` are authoritative.

---

### Adding Memory

Memory records live in `memory/` as markdown files with metadata and are registered in `memory/registry.json`.

**Checklist:**
- [ ] Use `python scripts/memory-add.py --type TYPE --title "Title" --scope SCOPE --summary "..."` to create records
- [ ] Ensure records follow `schemas/memory.schema.json`
- [ ] Register in `memory/registry.json`
- [ ] Run `python scripts/validate-memory-security.py` to check for secrets
- [ ] Run `python scripts/generate-memory-index.py`

**Authority:** Source `.md` records and `memory/registry.json` are authoritative; generated indexes are derived.

**Memory Types:** lesson, decision, session, project, workflow, pattern, risk, opportunity

---

### Adding Knowledge or References

Knowledge lives in `knowledge/` by subject; references in `references/`.

**Checklist:**
- [ ] Create `knowledge/SUBJECT/TOPIC.md` for reusable knowledge
- [ ] Create `references/SUBJECT/REFERENCE.md` for supporting material
- [ ] Link from knowledge topics to references where applicable
- [ ] No registry needed; organize by topic folder

**Authority:** Markdown files are authoritative; no generated registry.

---

### Adding a Template or Example

Templates live in `templates/`; examples in `examples/`.

**Checklist:**
- [ ] Create `templates/CATEGORY/NAME/` or `examples/CATEGORY/NAME/`
- [ ] Include a README documenting the content
- [ ] Ensure the template/example is self-contained and runnable
- [ ] For project templates, preserve the [project-memory contract](templates/project-memory/README.md)

**Authority:** Markdown and source files are authoritative; never edit generated output.

---

### Adding a Specification or Standard

Specifications live in `specs/`; standards in `standards/`.

**Checklist:**
- [ ] Create `specs/FEATURE.md` with requirements, design, tasks, and validation
- [ ] Create `standards/DOMAIN.md` for conventions and best practices
- [ ] Link from related agents, skills, or knowledge
- [ ] No registry needed

**Authority:** Markdown files are authoritative.

---

## Registry and Generated File Rules

**Manual registries (keep in sync with folder content):**
- `agents.json` ← `agents/`
- `prompts.json` ← `prompts/`
- `memory/registry.json` ← `memory/`
- `profile/registry.json` ← `profile/`

**Generated files (never hand-edit; regenerate instead):**
- `generated/*.json` and `generated/*.html`
- Run the appropriate generator script after source changes

**Generator Scripts:**
- Agents: `python scripts/generate-agent-registry.py`
- Skills: `python scripts/generate-skill-registry.py`
- Memory: `python scripts/generate-memory-index.py`
- Knowledge: `python scripts/generate-knowledge-graph.py`
- Repository: `python scripts/index-repository.py`
- Profile: `python scripts/generate-profile-index.py`
- Orchestration: `python scripts/generate-agent-registry.py`, `python scripts/generate-workflow-registry.py`

**Check mode** (validate without writing): Add `--check` flag to any generator script.

---

## Validation Checklist

Before submitting a pull request, run these validation steps:

```bash
# Regenerate derived files if you changed source content
python scripts/generate-skill-registry.py
python scripts/generate-agent-registry.py
python scripts/index-repository.py
python scripts/generate-memory-index.py
python scripts/generate-knowledge-graph.py

# Validate everything
python scripts/validate-all.py

# Check for secrets in memory
python scripts/validate-memory-security.py

# Optional: validate in check mode (no writing)
python scripts/validate-all.py --check
```

All checks must pass before submitting for review.

---

## Naming Conventions

- **Folders:** lowercase, hyphenated (e.g., `my-skill`, `agent-name`)
- **Files:** kebab-case or snake_case (consistent within folder)
- **IDs:** Stable, lowercase, hyphenated (e.g., `my-skill-001`)
- **Metadata:** Valid YAML in front matter; no invalid characters

---

## Pull Request Template

When submitting, include:

1. **Scope:** What did you add or change?
2. **Type:** Skill / Agent / Prompt / Memory / Knowledge / Template / Spec / Other
3. **Tests/Examples:** How is this demonstrated or validated?
4. **Risks:** What could break? What dependencies exist?
5. **Documentation:** What docs were updated?
6. **Changelog:** Will this require a release note?
7. **Validation:** Did you run the validation checklist above?

---

## Special Rules

**Never commit:**
- Secrets, credentials, API keys, tokens, or access codes
- Personal data, employee records, or government-protected information
- Unrelated changes or work-in-progress content

**Never hand-edit:**
- Files in `generated/`
- Generated indexes or dashboards
- Agent/prompt/memory registries without updating source

**Always update together:**
- Source files (e.g., `agents/*.md`) and their registries (e.g., `agents.json`)
- Agent definitions and their registry
- Prompt files and `prompts.json`
- Memory records and `memory/registry.json`

**Runtime state (never commit):**
- `.ai-os/` contents (session, approval, feedback, audit data)
- Temporary editor files

---

## Getting Help

- **Where should this go?** → See [CONTENT_PLACEMENT_RULES.md](docs/CONTENT_PLACEMENT_RULES.md)
- **What's authoritative?** → See [docs/source-of-truth.md](docs/source-of-truth.md)
- **How does the repository work?** → See [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- **What's the workflow?** → See [docs/process/WORKFLOW.md](docs/process/WORKFLOW.md)

---

## Memory Command Examples

```bash
python scripts/memory-add.py --type lesson --title "Refresh data before rebuilding" --scope global --summary "..." --tags "power-apps" --sensitivity internal
python scripts/memory-list.py --type lesson
python scripts/memory-search.py "keyword" --max-results 10
python scripts/memory-archive.py --id lesson-example-001
python scripts/memory-promote.py --id session-example-001 --target-type lesson --reason "Reusable finding"
```

---

## Knowledge Graph Command Examples

```bash
python scripts/generate-knowledge-graph.py
python scripts/validate-knowledge-graph.py
python scripts/generate-knowledge-graph.py --check
```

---

## Orchestration (Phase 8)

Agent docs (`agents/*.md`, `agents.json`) and workflow sources (`knowledge/workflows/*.json`) are authoritative.

**After changes, run:**
```bash
python scripts/generate-agent-registry.py
python scripts/generate-workflow-registry.py
python scripts/generate-knowledge-health.py
python scripts/orchestration-validate.py
```

Never hand-edit `generated/agent-registry.json`, `generated/workflow-registry.json`, or `generated/knowledge-health.json`.

---

## Professional Context (Phase 9)

Profile records (`profile/*.md`, `profile/registry.json`) are authoritative.

**Authority rules:**
- `knowledge/professional-context/overview.md` is human-owned; edit directly
- `python scripts/ai-os.py profile sync-knowledge` only scaffolds if absent
- `profile switch` is the only way to change active profile; requires `profile-switch` approval

**Never store:**
- Raw resumes
- Evaluations or performance data
- Personal contact info or government IDs
- Private correspondence

See [SECURITY.md](SECURITY.md) for details.

---

## Questions or Issues?

Check [CONTRIBUTING.md](CONTRIBUTING.md), ask in an issue, or review [docs/](docs/) for deeper guidance.
