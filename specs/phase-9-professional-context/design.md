# Design — Phase 9: Professional Context and Work Intelligence

## Overview
Phase 9 adds three new pieces of state — a canonical professional profile, derived work-activity signals, and an evidence-based expertise profile — plus the generators, validation, MCP tools, and dashboard surface needed to expose them, all built on top of the Phase 1–8 infrastructure (memory conventions, knowledge graph, approval engine, MCP adapter, dashboard).

## Current State
- `memory/` holds approval-gated learned records (lessons, decisions, projects, sessions) as Markdown files with YAML front matter, validated by `scripts/memory_utils.py` and indexed both directly into the knowledge graph (`classify_document()` in `scripts/knowledge_graph/extract.py`, type `memory`) and via a dedicated `generated/memory-index.json` (`scripts/generate-memory-index.py`).
- `scripts/index-repository.py`'s `CATEGORIES` tuple (`skills, agents, prompts, project-starters, templates, standards, knowledge, references, scripts`) deliberately excludes `memory/` — the general-purpose repository index does not surface memory content; a dedicated indexer does instead.
- `knowledge/` holds hand-authored, versioned documentation (e.g. `knowledge/architecture/phase-N-*.md`) that is a source of truth and is never silently overwritten by generators.
- `generated/` holds fully deterministic, regenerable artifacts (JSON + Markdown twin) with `--check` staleness modes wired into `validate-all.py`; these files declare "not a source of truth" and are safe to overwrite on every run.
- `scripts/orchestration/approvals.py` implements a no-auto-approve approval engine already used by memory suggestions (Phase 8).
- `scripts/mcp_server/adapter.py` already redacts memory content to summaries in MCP responses (confirmed by the existing "memory returns summary only" smoke-test case).
- The knowledge-graph/discovery-index generators use `scripts/repo_files.py` (this session's earlier fix) to scope file discovery to git-tracked files, with a deterministic fallback allowlist.

## Proposed Architecture
Phase 9 introduces one new top-level data directory (`profile/`), two new generators, one new Python package (`scripts/profile/`), and additive extensions to five existing subsystems (knowledge graph, approvals, MCP adapter, dashboard, unified validation). No existing schema, node type, or CLI command changes shape.

```
profile/                          # canonical, authored (REQ-001, REQ-006)
  README.md
  registry.json                   # lists profile records + which is active
  primary.md                      # the one Phase 9 profile record (front matter + prose)
  primary.expertise.json          # expertise entries for the active profile (REQ-003)

knowledge/professional-context/   # hand-owned, scaffolded once (REQ-002, resolves Open Q1)
  overview.md
  snapshots/                      # created only by explicit --force-refresh, never overwrites overview.md
    professional-context-YYYY-MM-DDTHHMMSSZ.md

generated/
  work-activity.json / .md        # deterministic aggregation (REQ-002)
  profile-index.json / .md        # mirrors generated/memory-index.json (REQ-004, resolves Open Q2)

scripts/profile/                  # new package, mirrors scripts/orchestration/ structure
  __init__.py
  schema.py                       # field lists, enums (proficiency levels, approval target types)
  registry.py                     # profile/registry.json read/write, active-profile resolution
  validate.py                     # profile + expertise structural validation
  render.py                       # profile-index.json/.md rendering

scripts/generate-work-activity.py # CLI entrypoint, standalone build/--check like every other generator
scripts/generate-profile-index.py # CLI entrypoint, mirrors scripts/generate-memory-index.py
```

## Components

| Component | Change | Mirrors |
|---|---|---|
| `profile/` data directory | New | `memory/` structure and front-matter convention |
| `scripts/profile/*.py` | New package | `scripts/orchestration/*.py` |
| `scripts/generate-profile-index.py` | New | `scripts/generate-memory-index.py` |
| `scripts/generate-work-activity.py` | New | `scripts/generate-knowledge-health.py` (pure aggregation over existing artifacts) |
| `scripts/knowledge_graph/extract.py` | Extend `classify_document()` to return `"profile"` for `profile/*.md`; extend the `generated/` allowlist in `discover_source_files()` with `generated/profile-index.json` and `generated/work-activity.json` | Existing `"memory"` classification |
| `scripts/orchestration/approvals.py` | Add `profile_write`, `expertise_write`, `profile_switch` to `APPROVAL_TYPES` | Existing approval-type enum |
| `scripts/mcp_server/adapter.py` + `schemas.py` | Add `get_professional_profile`, `list_expertise`, `get_work_activity_summary` (all read-only, summary-only) | Existing memory-summary redaction tools |
| `scripts/dashboard/` | New "Professional Context" page: active profile, expertise list, work-activity highlights | Existing Phase 8 dashboard pages |
| `scripts/validate-all.py` | Wire in profile-index and work-activity staleness checks; add a profile/memory boundary guard | Existing generator wiring pattern |
| `scripts/ai-os.py` | New `profile show`, `profile switch <id>`, `profile sync-knowledge [--force-refresh]` subcommands | Existing `memory` CLI command group |

## Data Flow
1. **Author**: user creates/edits `profile/primary.md` directly (role, team, responsibilities, reporting relationships) or runs `ai-os.py profile show` to see current state; any change is validated by `scripts/profile/validate.py`.
2. **Generate**: `ai-os.py generate` runs `generate-profile-index.py` (indexes `profile/`, mirroring memory indexing) and `generate-work-activity.py` (aggregates `memory/` and `generated/knowledge-graph.json` into `generated/work-activity.json`), then regenerates the knowledge graph (now including `profile`-typed nodes), discovery index, and dashboard, exactly as today. **Reconciled during implementation**: the committed, `--check`-verified `generated/work-activity.*` artifacts use repository-stable sources only. `.ai-os/sessions/*.json` is excluded because it is git-ignored, machine-local runtime state and would make the committed artifact differ across clones and CI environments (the same reason `generate-knowledge-health.py`'s deterministic view already excludes it, per that generator's own docstring). A session-inclusive activity view is deferred to a future local, read-only CLI or runtime command. `windowDays` (see Data Model) is recorded as descriptive metadata only and is not applied as a wall-clock-relative filter during deterministic generation, since filtering by "now" would make identical committed data produce different output on different days.
3. **Propose**: an agent may propose a new expertise entry into `profile/primary.expertise.json` with `status: proposed` and a required `evidence` reference (e.g. a work-activity project or session pointer) — this goes through `scripts/orchestration/approvals.py` (type `expertise_write`) before becoming `status: approved`. No auto-approve path, matching Phase 8.
4. **Switch** (schema-ready, not exercised in Phase 9 beyond the one profile): `ai-os.py profile switch <id>` is the only code path allowed to change which profile record is `active` in `profile/registry.json`; it is always explicit and itself requires approval (type `profile_switch`).
5. **Sync knowledge**: `ai-os.py profile sync-knowledge` scaffolds `knowledge/professional-context/overview.md` from current profile + work-activity state **only if it does not already exist**; re-running without `--force-refresh` is a no-op that reports the file already exists. `--force-refresh` writes a new file under `knowledge/professional-context/snapshots/professional-context-YYYY-MM-DDTHHMMSSZ.md` (UTC timestamp, second precision), never touching `overview.md` or any other curated file. Snapshot content is generated through the same sanitization step as `overview.md` (see Security). Normal `ai-os.py generate` / `generate --check` never invoke snapshot creation and never write under `knowledge/professional-context/` — only the explicit `sync-knowledge --force-refresh` command does.
6. **Query**: MCP tools and the dashboard read `profile/`, `profile/primary.expertise.json`, and `generated/work-activity.json`; MCP responses are summary-only (name/role/proficiency level, no free-text notes or evidence detail), matching the existing memory redaction posture.

## Data Model

**`profile/registry.json`**
```json
{
  "schemaVersion": "1.0.0",
  "profiles": [
    {"id": "primary", "path": "profile/primary.md", "active": true, "createdAt": "..."}
  ]
}
```
Exactly one entry has `active: true` at all times; validation fails if zero or more than one are active.

**`profile/primary.md`** (front matter, mirroring memory record style)
```yaml
---
id: primary
schemaVersion: "1.0.0"
role: <string>
team: <string>
responsibilities: [<string>, ...]
reportingTo: <string|null>
sensitivity: high
createdAt: <date>
updatedAt: <date>
---
# Primary Professional Profile
<optional free-text notes>
```

**`profile/primary.expertise.json`**
```json
{
  "schemaVersion": "1.0.0",
  "profileId": "primary",
  "updatedAt": "...",
  "entries": [
    {
      "id": "expertise-<slug>",
      "name": "<string>",
      "level": "foundational|working|proficient|advanced|lead",
      "evidence": [
        {"type": "project", "ref": "windows-11-autopilot-deployment"},
        {"type": "role", "ref": "senior-it-technical-support-analyst"},
        {"type": "source", "ref": "current-resume-2026"}
      ],
      "source": "user|agent-suggested",
      "status": "proposed|approved",
      "createdAt": "...",
      "updatedAt": "..."
    }
  ]
}
```

**Evidence pointer format** — `{type, ref}`, lightweight and structured, not a resolvable graph edge in Phase 9:

- `type` is one of a fixed enum: `project`, `role`, `source`, `session`, `workActivity`, `memory`. Both `type` and `ref` are required, non-empty, and schema-validated; entries missing either field fail validation.
- `ref` must be a stable, normalized identifier (lowercase, hyphenated, no whitespace or path traversal) — a slug or id, not free text, and never a raw file path into sensitive source material.
- Validation requires at least one `evidence` entry per record (REQ-003 "evidence-based") and rejects `level` values outside the fixed proficiency enum.
- Phase 9 does not require `ref` to resolve against any existing knowledge-graph node, work-activity entry, or session id. An evidence pointer that doesn't currently resolve produces a **validation warning**, not a failure, and is never silently dropped — the entry and its evidence are preserved as authored.
- The knowledge-graph and discovery-index layers may, in a later phase, derive relationships from evidence pointers that do resolve (e.g. linking an expertise entry to a matching `generated/work-activity.json` project) without any change to this schema — evidence pointers are designed to be forward-compatible with that, not to require it now.
- Evidence entries must never contain raw resumes, evaluation files, contact information, or other sensitive source text — `ref` is an identifier that points at such material conceptually (e.g. `"current-resume-2026"`), never the material itself.

**`generated/work-activity.json`**
```json
{
  "schemaVersion": "1.0.0",
  "generatedAt": "...",
  "generator": "ai-os-work-activity",
  "windowDays": 90,
  "projects": [{"project": "...", "sessionCount": 0, "lastActiveAt": "...", "relatedEntities": []}],
  "focusAreas": [{"term": "...", "weight": 0, "sources": []}],
  "activitySummary": {"totalSessions": 0, "totalMemoryRecords": 0}
}
```

**`generated/profile-index.json`** mirrors `generated/memory-index.json`'s shape (id, path, role, team, active) — safe to expose more broadly than the raw profile record since it is itself a generated, redaction-aware artifact.

## Interfaces
- CLI: `ai-os.py profile show|switch <id>|sync-knowledge [--force-refresh]`
- MCP tools (all read-only): `get_professional_profile` (summary), `list_expertise` (summary), `get_work_activity_summary`
- Generators (standalone, `--check` mode): `generate-profile-index.py`, `generate-work-activity.py`

## Security
- `profile/`, `profile/primary.expertise.json`, and `generated/work-activity.json` are treated as high sensitivity; MCP responses are summary-only, matching REQ-004 and the existing memory pattern.
- `scripts/validate-memory-security.py` (or equivalent secret-pattern scan) is extended to also scan `profile/` and `knowledge/professional-context/`, including its `snapshots/` subdirectory.
- A new validation guard rejects any `memory/` record whose front matter contains reserved profile-only keys (`role`, `team`, `reportingTo`) as a structural failure, enforcing the REQ-001/REQ-005 boundary actively rather than by convention alone.
- Evidence entries in `profile/primary.expertise.json` must never contain raw resumes, evaluation files, contact information, or other sensitive source text; validation checks `ref` values look like normalized identifiers (see Data Model) rather than free text or file paths, as a structural proxy for this rule.
- `overview.md` and every file under `knowledge/professional-context/snapshots/` are produced through the same sanitization step before being written: no private contact information, signatures, reviewer names, credentials, or confidential operational data. This is enforced by the same secret-pattern scan used elsewhere, applied specifically to this generated content before it is written to disk, not only after the fact by `validate-all.py`.
- Snapshot filenames (`professional-context-YYYY-MM-DDTHHMMSSZ.md`) are deterministic for a given input and timestamp source, filesystem-safe (no characters requiring escaping on Windows or POSIX), and collision-resistant at second precision; repeated invocations within the same command run must not silently overwrite or duplicate a snapshot silently — a second invocation within the same second is treated as an error rather than a silent overwrite.
- Purge is file deletion (`profile/primary.md`, `profile/primary.expertise.json`, then `ai-os.py generate` to clear derived artifacts); documented in `profile/README.md`. No archive/soft-delete concept is introduced for Phase 9.

## Error Handling
Matches existing generator conventions: structural validation failures print `FAIL <reason>` and return a non-zero exit code; `--check` mode never mutates state; `profile switch` refuses to proceed if the target id doesn't exist in `registry.json` or if more than one profile would end up `active`.

## Logging and Monitoring
No new logging subsystem. Approval and audit events for profile/expertise writes flow through the existing Phase 8 hash-chained audit trail (`scripts/orchestration/audit.py`) — no changes needed there beyond recognizing the new approval types.

## Testing Strategy
- `tests/test_profile.py`: schema/validation unit tests mirroring `tests/test_orchestration_*.py` patterns; registry active-flag invariants (exactly one active profile); evidence-requirement enforcement (at least one entry, `type`/`ref` non-empty and normalized); an unresolved evidence `ref` produces a warning, not a failure, and is preserved; the `memory/` boundary guard (profile-only keys rejected from memory front matter).
- `tests/test_work_activity.py`: determinism (identical fixture → identical output ignoring `generatedAt`); aggregation correctness against a small fixture.
- `tests/test_profile_sync_knowledge.py`: normal `sync-knowledge` never overwrites an existing `overview.md`; `--force-refresh` creates a new file under `snapshots/` and never touches `overview.md`; snapshot filenames are deterministic for a fixed input/timestamp and collision-resistant; two invocations within the same second are handled as an error, not a silent overwrite; snapshot and `overview.md` content is sanitized (no fixture-injected contact info/credentials survive into output).
- Extend `tests/test_dashboard.py` and `scripts/validate-all.py`'s generator-wiring tests: confirm `ai-os.py generate` / `generate --check` never create or modify anything under `knowledge/professional-context/`.
- Extend `tests/test_mcp_integration.py`: new tools are callable, read-only, summary-only, and none can mutate approval/profile state (extends the existing "no approval-mutating tool exposed" smoke-test case).
- Extend `tests/test_dashboard.py`: new page renders, staleness check behaves like other pages.
- Extend `tests/test_repo_files.py`-style coverage: confirm `profile/` (and `knowledge/professional-context/`) participate correctly in git-tracked-file discovery scoping, and that an arbitrary untracked local directory is still never indexed with this new content type present (regression coverage for the fix already merged this session).

## Deployment Strategy
Purely additive — existing repositories get an empty `profile/` (no active profile) until the user authors one; all new `--check` staleness gates default to passing-but-absent until first use, matching how `generated/knowledge-health.json` etc. were introduced in Phase 8. No migration script needed.

## Rollback Strategy
Revert the Phase 9 commits; no prior-phase schema is touched, so rollback is a plain `git revert` with no data-migration concern. If `profile/` records already exist at rollback time, they simply become inert (unused by the reverted code) rather than corrupting anything.

## Alternatives Considered
- **JSON-only profile record** (no Markdown/front matter) — rejected to stay consistent with the existing human-editable memory-record authoring style rather than introducing a second authoring convention.
- **Expertise inline inside the profile record** — rejected; expertise changes at a different cadence (evidence-driven, sometimes agent-proposed) than the largely static role/team fields, and a separate file keeps diffs and approvals scoped to what actually changed.
- **Auto-regenerating `knowledge/professional-context/` on every `generate` run** — rejected; would blur the `knowledge/` source-of-truth boundary and risk silently clobbering human edits, resolving Open Question 1 from requirements.md in favor of scaffold-once + explicit dated snapshots.
- **Adding `profile` to `index-repository.py`'s `CATEGORIES`** — rejected in favor of a dedicated `profile-index.json`, mirroring the existing `memory/` precedent, resolving Open Question 2 from requirements.md and keeping sensitive personal data out of the general-purpose repository index/file browser.

## Risks
- Splitting profile/expertise across multiple files adds structural complexity for a phase that only populates one profile; mitigated by keeping multi-profile mechanics to a single `active` flag rather than building switching UI now.
- Classifying `profile/` as a new knowledge-graph node type means any future generic document-traversal code must remember to treat it as sensitive; mitigated by centralizing redaction in the MCP adapter and covering it with an explicit regression test.

## Open Questions
None remaining for Phase 9. Both prior open questions are resolved and reflected above:
- Evidence-reference format: lightweight `{type, ref}` pointer, not required to resolve to a knowledge-graph edge in Phase 9 (see Data Model).
- `profile sync-knowledge --force-refresh` behavior: dated/timestamped snapshots under `knowledge/professional-context/snapshots/` using the `professional-context-YYYY-MM-DDTHHMMSSZ.md` filename format, never overwriting curated files (see Data Flow, Security).
