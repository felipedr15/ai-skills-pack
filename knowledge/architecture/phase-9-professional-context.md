# Phase 9 Professional Context and Work Intelligence Architecture

## Purpose and Boundaries

Phase 9 adds a strictly local-first, privacy-first layer capturing *who the user is
professionally* (role, team, responsibilities, reporting relationships) as canonical, explicitly-
authored records, deriving work-activity signals purely from data Phases 2 and 8 already capture,
and maintaining an evidence-based expertise list — all read-only from an agent's perspective except
where the user explicitly approves a write.

What Phase 9 intentionally does **not** add: no integration with external work tools (calendar,
email, ticketing, HR systems); no automatic inference of role/org data from repository content
(role/org context is authored, never guessed); no execution engine or automated action-taking; no
reuse of the existing `skill` node type for professional expertise (a distinct vocabulary); no
automatic profile switching (the schema supports multiple profiles, but switching which one is
active is always an explicit, approval-gated user action); and no richer role/team/expertise/
evidence-pointer graph or discovery modeling — that is deferred to a later phase (see
[Deferred Work](#9-deferred-work)).

Local-first constraint: every Phase 9 write path is local disk I/O only. Privacy boundary:
professional-context and expertise data defaults to high sensitivity — MCP responses are
summary-only, generic knowledge-graph/discovery traversal never exposes role/team/responsibilities/
prose, and `profile/registry.json` ships empty (no professional profile is included with this
repository).

## 2. Directory and Ownership Model

| Directory | Owns | Mutation path |
|---|---|---|
| `profile/` | Canonical, explicitly-authored professional profile records (`registry.json`, `<id>.md`, `<id>.expertise.json`) — structurally parallel to `memory/`, never stored inside it | `profile switch` (approval-gated, registry `active` flag only); record authoring is manual |
| `knowledge/professional-context/` | Curated, human-owned prose derived from profile + work-activity state | `profile sync-knowledge` (scaffold-once, no-overwrite) and `--force-refresh` (adds a dated snapshot only, never rewrites `overview.md`) |
| `memory/` | Approval-gated *learned* records (lessons, decisions, sessions) | Unchanged from Phase 2/8; a validation guard actively rejects any record whose front matter carries the reserved profile-only keys `role`, `team`, or `reportingTo` |
| `generated/` | Deterministic derived artifacts (`profile-index.json/.md`, `work-activity.json/.md`) | `ai-os.py generate` / `generate --check`; never touches `knowledge/professional-context/` |
| `.ai-os/` | Local runtime state (approvals, sessions) | Git-ignored; `profile-switch` approvals live here like every other Phase 8 approval; deliberately excluded from the committed, deterministic `generated/work-activity.json` |

## 3. Data Flow

1. **Author** (manual, read-only from the system's perspective): the user creates/edits
   `profile/<id>.md` and `profile/<id>.expertise.json` directly; `scripts/profile/validate.py`
   validates structure on demand (via the generators and CLI below), never automatically.
2. **Generate** (deterministic generation): `ai-os.py generate` runs `generate-profile-index.py`
   (indexes `profile/`, mirroring `generate-memory-index.py`) and `generate-work-activity.py`
   (aggregates `memory/` + `generated/knowledge-graph.json` into `generated/work-activity.json`;
   `.ai-os/sessions/` is excluded so the committed artifact is identical across machines;
   `windowDays` is descriptive metadata, never a wall-clock filter), then regenerates the
   knowledge graph (profile-typed nodes), discovery index, and dashboard as it already does for
   every other artifact. This path never invokes `sync-knowledge` and never writes under
   `knowledge/professional-context/`.
3. **Read (CLI, read-only)**: `profile list` / `profile show [id]` read `profile/registry.json`
   and, for `show`, the matching `profile/<id>.md` front matter — never the prose body, never any
   field outside the fixed schema.
4. **Switch (explicit, approval-gated mutation)**: `profile switch <id>` is the only code path
   allowed to change `profile/registry.json`'s `active` flag. It validates the full registry,
   confirms the target id exists, then checks for an approved `profile-switch` approval scoped to
   that id; if none exists it auto-requests one and stops without mutating anything. Only after
   approval does it perform an atomic write.
5. **Sync-knowledge (explicit manual mutation)**: `profile sync-knowledge` scaffolds
   `knowledge/professional-context/overview.md` only if absent; `--force-refresh` snapshots the
   *current* curated content into `knowledge/professional-context/snapshots/professional-context-
   YYYY-MM-DDTHHMMSSZ.md` and never touches `overview.md`. Both paths run write-time sanitization
   before anything reaches disk.
6. **Query (read-only)**: MCP tools and the dashboard read `generated/profile-index.json`,
   `profile/<id>.expertise.json` (summary fields only), and `generated/work-activity.json`.

## 4. Schema and Evidence Model

- **Registry** (`profile/registry.json`): `{schemaVersion, profiles: [{id, path, active,
  createdAt}]}`. Exactly one entry has `active: true` once any profile exists; an empty
  `profiles` list is a valid, expected "not yet configured" state, not an error.
- **Profile record** (`profile/<id>.md`): YAML front matter (`id, schemaVersion, role, team,
  responsibilities, reportingTo, sensitivity, createdAt, updatedAt`) plus free-text prose. The
  prose body and any field outside this fixed set is never surfaced by generic traversal, CLI
  `show`, or MCP.
- **Expertise file** (`profile/<id>.expertise.json`): `{schemaVersion, profileId, updatedAt,
  entries: [{id, name, level, evidence, source, status, createdAt, updatedAt}]}`. `level` is
  restricted to `foundational|working|proficient|advanced|lead`. `source` is `user` or
  `agent-suggested`; `status` is `proposed` or `approved`.
- **Evidence pointer**: `{type, ref}` — `type` is one of `project|role|source|session|
  workActivity|memory`; `ref` must be a normalized, lowercase-hyphenated identifier, never free
  text, a file path, or contact information. At least one evidence entry is required per
  expertise record (REQ-003's "evidence-based" requirement is structurally enforced).
- **Unresolved-reference behavior**: Phase 9 does not require `ref` to resolve against any other
  data source. An unresolved ref produces a validation *warning*, never a failure, and the entry
  is preserved exactly as authored — it is never dropped or inflated.
- **Sensitivity assumption**: every profile and expertise record defaults to `sensitivity: high`;
  `generated/profile-index.json`'s `{id, path, role, team, active}` summary shape is the one
  artifact explicitly treated as safe to expose more broadly, since it is itself generated and
  redaction-aware — raw records are not.

## 5. Security Model

- **Sanitizer** (`scripts/profile/sanitize.py`): deterministic, regex-based pattern matching
  applied at write time (not only after the fact) to every byte written under
  `knowledge/professional-context/` — private keys, API keys/tokens, passwords, generic secrets,
  SSNs, credit-card-like numbers, phone numbers, email addresses, street addresses, ZIP codes,
  employee IDs, internal IP ranges, reviewer/signature markers, confidential/County-security
  markers, and resume/evaluation markers. Findings never surface the matched value — only a
  masked excerpt internally, and only the pattern *name* in any raised error. This reduces risk
  but is not a substitute for human privacy review.
- **Reserved memory keys**: `scripts/memory_utils.py` imports `RESERVED_PROFILE_KEYS` from
  `scripts/profile/schema.py` (single source of truth) and rejects any `memory/` record carrying
  `role`, `team`, or `reportingTo` as a structural validation failure.
- **Approval boundary**: `profile-write`, `expertise-write`, and `profile-switch` are registered
  in the existing `scripts/orchestration/approvals.py` engine (no parallel mechanism). Scoping is
  `(type, target)` — an approval for `profile-switch` targeting `primary` never satisfies a check
  for `profile-write`, `expertise-write`, or a different target id. No approval is ever granted
  automatically; only an explicit `ai-os.py approval approve <id>` moves one from `pending` to
  `approved`.
- **Atomic writes**: `profile/registry.json` is written via a temp-file-plus-`os.replace`
  sequence; a failure partway through leaves the original content intact rather than a partial
  file.
- **Path normalization and no arbitrary reads**: profile ids are validated as normalized
  identifiers (`^[a-z0-9]+(-[a-z0-9]+)*$`, no `/`, no `..`) before being used to construct any
  file path, so a profile id can never escape `profile/`. MCP tools apply the same check and fail
  with `invalid_request` rather than resolving an attacker-controlled path.
- **No external integrations, no auto-promotion**: no network calls, no telemetry, no arbitrary
  shell execution anywhere in `scripts/profile/`; no Phase 9 code path writes into `memory/`, and
  no memory-suggestion is auto-promoted as a side effect of any profile operation.

## 6. Determinism Model

- Stable ordering: `profile/registry.json` entries sorted by `id`; `generated/profile-index.json`
  records sorted by `id`; `generated/work-activity.json` projects/focus areas sorted
  deterministically; expertise entries sorted by `(name, id)` wherever surfaced.
- Normalized paths and line endings: POSIX-style relative paths throughout (mirroring the
  knowledge-graph/discovery convention); files written with `\n` line endings via
  `newline="\n"`.
- Check mode: `generate-profile-index.py --check` and `generate-work-activity.py --check` fail
  without writing when the committed artifact is stale, wired into `validate-all.py` and
  `GENERATION_ORDER` exactly like every other generator.
- Stale detection: comparison ignores only `generatedAt`; any other field difference fails the
  check.
- Excluded runtime state: `.ai-os/sessions/` (git-ignored, machine-local) is excluded from the
  deterministic `generated/work-activity.json` for the same reason
  `generate-knowledge-health.py`'s deterministic view already excludes it — including it would
  make identical committed data differ across clones and CI environments.
- Generated timestamps: `generatedAt` on `profile-index.json`/`work-activity.json` reflects
  build time and is excluded from all staleness comparisons, matching every prior generator.
- Snapshot timestamps are explicit mutation output, not committed deterministic generation:
  `professional-context-YYYY-MM-DDTHHMMSSZ.md` filenames are derived from wall-clock time at the
  moment `--force-refresh` runs, are never regenerated by `ai-os.py generate`, and two invocations
  landing on the same second raise rather than silently overwriting or duplicating.

## 7. Integration Model

- **Graph classification**: `classify_document()` in `scripts/knowledge_graph/extract.py` returns
  `"profile"` for `profile/*.md` (excluding `README.md`), mirroring the existing `"memory"`
  pattern. The resulting node carries only `schemaVersion` and `active` (cross-referenced from
  `profile/registry.json`) in its metadata — never role/team/responsibilities — and pass 2's
  generic mention-extraction/link-mining is explicitly skipped for `profile`-classified files so
  prose is never mined into `uses`/`related_to` edges. `generated/profile-index.json` and
  `generated/work-activity.json` are represented once each, as supplemental `document`-type
  nodes, matching the existing `skills.json`/`memory-index.json` precedent.
- **Discovery deduplication**: semantic discovery derives its `entities` list directly from
  knowledge-graph nodes, so profile entities appear there automatically — `discover_source_files()`
  deliberately does *not* re-walk `generated/profile-index.json`/`work-activity.json` as raw
  documents, avoiding a second, duplicate representation of the same fact. Profile `.md` records
  that are walked as raw `documents` have their title/headings/snippet/frontMatter suppressed to
  structural-only fields. `knowledge/professional-context/snapshots/` is excluded from indexing
  entirely by both generators, so a stale snapshot can never rank as if it were current.
- **MCP allowlists**: `get_professional_profile` and `list_expertise` read only from
  `generated/profile-index.json` (already the redaction-aware summary artifact) and
  `profile/<id>.expertise.json`'s schema-restricted fields; `get_work_activity_summary` reads an
  explicit field allowlist from `generated/work-activity.json` rather than serializing the loaded
  object verbatim. No tool can create, edit, or switch a profile, or touch approvals/sync-
  knowledge/snapshots.
- **Dashboard static payload**: `aggregate_professional_context()` extends
  `dashboard.aggregate.build_dashboard_data()` with a `professionalContext` section built the same
  way as every other section (read generated artifacts, degrade to an `available: false`-style
  state on absence). The rendered page is fully static — data is embedded into `dashboard.html` at
  build time; there are no `/api/professional-context/*` live-fetch endpoints, unlike the Phase 8
  orchestration views.
- **Generator order and validation/release wiring**: `generate-profile-index.py` runs
  immediately after `generate-memory-index.py`; `generate-work-activity.py` runs after
  `generate-knowledge-graph.py` (it depends on graph output) and before `dashboard-build.py`.
  Both are wired into `scripts/validate-all.py`, `scripts/release/utils.py`'s
  `GENERATED_ARTIFACTS`/`GENERATION_ORDER`, and `scripts/release/manifest.py`'s
  `TRACKED_ARTIFACTS`, exactly like every prior generator.

## 8. Failure Behavior

| Condition | Behavior |
|---|---|
| Empty registry | Valid state everywhere: `profile list`/`show` report "not yet configured"; MCP tools return `configured: false`; dashboard renders an empty-state message. Never an error. |
| Invalid registry (zero/multiple active, duplicate id) | CLI fails with `FAIL invalid profile registry: ...`; `profile switch` mutates nothing. |
| Missing generated artifact (`profile-index.json`/`work-activity.json`) | MCP raises `Unavailable`; dashboard aggregation reports `*Available: false` and degrades gracefully rather than crashing. |
| Malformed expertise artifact | MCP raises `MalformedArtifact` for the whole file (never partially trusted); dashboard aggregation excludes it and reports zero expertise rather than crashing. |
| Unknown profile ID | CLI: `FAIL unknown profile id: ...`; MCP: `NotFound`. Neither fabricates a profile. |
| Missing approval | `profile switch` auto-requests a `profile-switch` approval and stops with a `FAIL ... requires approval` message; the registry is left byte-for-byte unchanged. |
| Sanitization failure | `sync-knowledge`/`--force-refresh` raise `SanitizationError` naming only the offending pattern type(s), never the matched value; nothing is written. |
| Snapshot collision (same second) | `--force-refresh` raises rather than silently overwriting or inventing a disambiguating suffix. |
| Stale generated artifacts | `generate --check` / `validate-all.py` fail closed, exactly like every other generator. |

## 9. Deferred Work

- Richer role/team/expertise/evidence-pointer graph and discovery relationships (e.g. `profile →
  has expertise → expertise`, `expertise → supported by → evidence`) — the current schema is
  forward-compatible with this but does not implement it; adding it requires new `NODE_TYPES`/
  `EDGE_TYPES` and a design amendment, not implied by the current, deliberately minimal
  integration.
- A live, session-inclusive work-activity view (today's `generated/work-activity.json` is
  repository-stable and excludes `.ai-os/sessions/` by design).
- A stronger sanitizer than deterministic regex pattern matching.
- Approval expiry (the `expired` status exists in `APPROVAL_STATUSES` but nothing sets it yet).
- Hardening the Phase 8 approval reader against malformed store records (`is_approved` can raise
  `KeyError` on a record missing expected keys; unrelated to Phase 9, not fixed here).
- Displaying evidence-resolution status (resolved/unresolved against known refs) through MCP or
  the dashboard — `scripts/profile/validate.py` supports the check, but no caller wires it up.
- A guided profile-authoring workflow (today, authoring `profile/<id>.md` and
  `<id>.expertise.json` is manual file editing).

## 10. Operational Examples

All examples below use the synthetic placeholder id `example-profile` — never real professional
data.

```text
python scripts/ai-os.py profile list
python scripts/ai-os.py profile show
python scripts/ai-os.py profile show example-profile
python scripts/ai-os.py profile switch example-profile
python scripts/ai-os.py approval list --status pending
python scripts/ai-os.py approval approve <approval-id>
python scripts/ai-os.py profile switch example-profile
python scripts/ai-os.py profile sync-knowledge
python scripts/ai-os.py profile sync-knowledge --force-refresh
python scripts/generate-profile-index.py --check
python scripts/generate-work-activity.py --check
```

[Back to AI OS](../../README.md)
