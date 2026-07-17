# Tasks — Phase 9: Professional Context and Work Intelligence

Traces to `requirements.md` (REQ-001–REQ-007) and `design.md`. Do not begin implementation until requirements.md and design.md are both approved (they are, as of this document). Tasks are grouped in dependency order; within a group, tasks may proceed in parallel.

## Implementation Order

1. **Data layer** (TASK-001–004) before anything reads or writes `profile/`.
2. **Generators** (TASK-005–007) before anything consumes `generated/profile-index.json` or `generated/work-activity.json`.
3. **`sync-knowledge` + snapshots** (TASK-008–011) depend on the generators (Group 2) for the data they summarize.
4. **CLI / approvals / profile switching** (TASK-012–014) depend on the data layer (Group 1) and reuse the existing approval engine.
5. **Knowledge graph / discovery integration** (TASK-015–016) depend on the data layer existing on disk to classify and test against.
6. **MCP + dashboard** (TASK-017–019) depend on Groups 1, 2, and 5 being in place to read from.
7. **Tests** (TASK-020–023) are written alongside each group above, not deferred to the end; they are listed separately here for traceability but should land with the code they cover.
8. **Documentation** (TASK-024–025) once behavior is stable enough to describe accurately.
9. **Spec hygiene** (TASK-026–027) and **final validation / stop condition** (TASK-028–029) close out the phase.

## Data Layer

### TASK-001: Create the `profile/` directory and core schema
- Requirement references: REQ-001, REQ-006
- Description: Create `profile/README.md`, `profile/registry.json` (schema per design.md Data Model), and the `profile/primary.md` record schema (front matter + prose, mirroring memory record style). No content is authored yet — this is the schema and empty scaffold.
- Owner or agent role: builder
- Dependencies: none
- Status: pending
- Validation: `scripts/profile/validate.py` (TASK-002) passes against an empty/absent profile without error.
- Completion criteria: directory and schema exist; `profile/` is git-tracked; no profile record is required to exist for the repo to remain valid.

### TASK-002: Implement `scripts/profile/` package and structural validation
- Requirement references: REQ-001, REQ-006
- Description: `scripts/profile/__init__.py`, `schema.py` (field lists, proficiency enum, approval target types), `registry.py` (registry read/write, active-profile resolution), `validate.py` (structural validation: required fields, exactly-one-active invariant).
- Owner or agent role: builder
- Dependencies: TASK-001
- Status: pending
- Validation: unit tests in TASK-020 cover zero-active and multiple-active registry states as failures.
- Completion criteria: validation fails closed on malformed registries/records; mirrors `scripts/orchestration/` structure per design.md.

### TASK-003: Implement expertise schema and evidence-pointer validation
- Requirement references: REQ-003
- Description: `profile/primary.expertise.json` schema; validation enforcing: at least one evidence entry per expertise record; `type`/`ref` both present and non-empty; `type` restricted to the fixed enum (`project`, `role`, `source`, `session`, `workActivity`, `memory`); `ref` normalized (lowercase, hyphenated, no whitespace/path traversal); `level` restricted to `foundational|working|proficient|advanced|lead`. An unresolved `ref` (doesn't match any known project/session/work-activity entry) produces a validation **warning**, never a failure, and the entry is preserved as-authored.
- Owner or agent role: builder
- Dependencies: TASK-002
- Status: pending
- Validation: TASK-020 covers the warning-not-failure behavior explicitly, plus rejection of malformed `type`/`ref`/`level`.
- Completion criteria: schema and validator match design.md's Data Model exactly; no evidence entry can contain free text or a file path in `ref`.

### TASK-004: Add the `memory/` ↔ `profile/` boundary guard
- Requirement references: REQ-001, REQ-005, Security/Privacy (NFR)
- Description: Extend memory validation (`scripts/memory_utils.py` or wherever front-matter validation lives) to reject any `memory/` record whose front matter contains reserved profile-only keys (`role`, `team`, `reportingTo`) as a structural failure — enforced actively, not by convention.
- Owner or agent role: builder
- Dependencies: TASK-001 (so the reserved-key list is defined once, shared between the two validators)
- Status: pending
- Validation: TASK-020 includes a regression test asserting a memory record with a `role:` front-matter key fails validation.
- Completion criteria: the boundary cannot be silently crossed by an agent-proposed memory suggestion.

## Generators

### TASK-005: Implement `scripts/generate-profile-index.py`
- Requirement references: REQ-004 (resolves requirements.md Open Question on repository-index category)
- Description: Standalone generator (`--check` mode supported) producing `generated/profile-index.json` and `.md`, mirroring `scripts/generate-memory-index.py`'s shape and conventions. `profile/` is **not** added to `scripts/index-repository.py`'s `CATEGORIES` — this dedicated indexer is the only path, matching the existing `memory/` precedent.
- Owner or agent role: builder
- Dependencies: TASK-001, TASK-002
- Status: pending
- Validation: staleness check produces identical output (ignoring `generatedAt`) across repeated runs on identical input.
- Completion criteria: wired into `GENERATION_ORDER` in `scripts/release/utils.py` alongside the other generators.

### TASK-006: Implement `scripts/generate-work-activity.py`
- Requirement references: REQ-002
- Description: Standalone generator aggregating `memory/`, `generated/knowledge-graph.json`, and `.ai-os/sessions/*.json` into `generated/work-activity.json` / `.md` (schema per design.md). No new raw inputs — pure aggregation over what Phases 2/3/8 already capture.
- Owner or agent role: builder
- Dependencies: none beyond existing Phase 2/3/8 artifacts
- Status: pending
- Validation: TASK-021 (determinism + aggregation-correctness tests).
- Completion criteria: deterministic, `--check` mode supported, wired into `GENERATION_ORDER`.

### TASK-007: Wire new generators into `scripts/validate-all.py`
- Requirement references: REQ-002, REQ-004
- Description: Add profile-index and work-activity staleness checks to the unified validation sequence, exactly like every existing generator.
- Owner or agent role: builder
- Dependencies: TASK-005, TASK-006
- Status: pending
- Validation: `python scripts/validate-all.py` reports both new checks in its PASS/FAIL summary.
- Completion criteria: `validate-all.py`'s total check count increases by exactly two; no existing check regresses.

## `sync-knowledge` and Snapshots

### TASK-008: Implement `ai-os.py profile sync-knowledge` (scaffold-once)
- Requirement references: REQ-002
- Description: New CLI subcommand that creates `knowledge/professional-context/overview.md` from current profile + work-activity state **only if the file does not already exist**. Re-running without `--force-refresh` is a no-op that reports the file already exists — it must never overwrite it.
- Owner or agent role: builder
- Dependencies: TASK-005, TASK-006
- Status: pending
- Validation: TASK-022.
- Completion criteria: matches design.md Data Flow step 5 exactly.

### TASK-009: Implement `--force-refresh` timestamped snapshots
- Requirement references: REQ-002
- Description: `--force-refresh` writes a new file under `knowledge/professional-context/snapshots/professional-context-YYYY-MM-DDTHHMMSSZ.md` (UTC, second precision) and never touches `overview.md`. Filenames must be deterministic for a given input/timestamp source, filesystem-safe on both Windows and POSIX, and collision-resistant; two invocations landing on the same second must error rather than silently overwrite or duplicate.
- Owner or agent role: builder
- Dependencies: TASK-008
- Status: pending
- Validation: TASK-022 covers filename determinism, collision handling, and the never-touches-`overview.md` guarantee.
- Completion criteria: matches design.md Security section's snapshot requirements exactly.

### TASK-010: Implement sanitization for `overview.md` and snapshot content
- Requirement references: Security/Privacy (NFR), explicit sanitization requirement
- Description: Before writing `overview.md` or any snapshot, strip/reject private contact information, signatures, reviewer names, credentials, and confidential operational data, reusing the existing secret-pattern scanning approach (`scripts/validate-memory-security.py` or equivalent) as the enforcement mechanism, applied at write time — not only after the fact.
- Owner or agent role: builder
- Dependencies: TASK-008
- Status: pending
- Validation: TASK-022 includes a fixture with injected contact-info/credential-shaped text and asserts it does not survive into output.
- Completion criteria: sanitization runs on every `sync-knowledge` and `--force-refresh` write path; no bypass exists.

### TASK-011: Guarantee `generate` / `generate --check` never touch `knowledge/professional-context/`
- Requirement references: REQ-002 (constraint), design.md Data Flow step 5
- Description: Confirm and, if necessary, enforce that `ai-os.py generate` and `generate --check` never invoke `sync-knowledge`, never create snapshots, and never mutate `overview.md`. This is a structural guarantee, not just an absence of a code path — add a regression test that fails loudly if a future change wires `sync-knowledge` into the generation pipeline by mistake.
- Owner or agent role: builder
- Dependencies: TASK-008, TASK-009
- Status: pending
- Validation: TASK-023 (extends `validate-all.py` generator-wiring tests).
- Completion criteria: `knowledge/professional-context/` is untouched by any `generate`/`generate --check` run in a test asserting file mtimes/hashes are unchanged.

## CLI, Approvals, and Profile Switching

### TASK-012: Implement `ai-os.py profile show`
- Requirement references: Interfaces (design.md)
- Description: Read-only CLI command displaying the active profile and its expertise summary.
- Owner or agent role: builder
- Dependencies: TASK-001, TASK-002, TASK-003
- Status: pending
- Validation: CLI test mirroring existing `ai-os.py` command tests.
- Completion criteria: output matches `profile/registry.json`'s active entry.

### TASK-013: Implement `ai-os.py profile switch <id>`
- Requirement references: REQ-006, REQ-005
- Description: The only code path allowed to change which profile is `active` in `profile/registry.json`. Always explicit (never automatic), and itself goes through the approval engine (type `profile_switch`). Refuses to proceed if the target id doesn't exist or if the result would leave zero or more than one profile active.
- Owner or agent role: builder
- Dependencies: TASK-002, TASK-014
- Status: pending
- Validation: TASK-020 covers the "exactly one active" invariant under switching.
- Completion criteria: no code path other than this command can change `active`.

### TASK-014: Extend `scripts/orchestration/approvals.py`
- Requirement references: REQ-005
- Description: Add `profile_write`, `expertise_write`, `profile_switch` to `APPROVAL_TYPES`; confirm the existing hash-chained audit trail (`scripts/orchestration/audit.py`) recognizes the new types without further changes, per design.md.
- Owner or agent role: builder
- Dependencies: none beyond existing Phase 8 approvals engine
- Status: pending
- Validation: extend `tests/test_orchestration_approvals.py`.
- Completion criteria: no parallel/duplicate approval mechanism is introduced; reuses the existing engine exactly.

## Knowledge Graph and Discovery Integration

### TASK-015: Classify `profile/` in the knowledge graph and discovery allowlists
- Requirement references: REQ-004, design.md Data Flow
- Description: Extend `classify_document()` in `scripts/knowledge_graph/extract.py` to return `"profile"` for `profile/*.md`; extend the `generated/` allowlist in `discover_source_files()` (both `knowledge_graph/extract.py` and `semantic_discovery/extract.py`) to include `generated/profile-index.json` and `generated/work-activity.json`.
- Owner or agent role: builder
- Dependencies: TASK-001, TASK-005, TASK-006
- Status: pending
- Validation: knowledge graph/discovery index include `profile`-typed nodes after regeneration; MCP adapter (TASK-017) redacts them the same way as `memory`-typed nodes.
- Completion criteria: no raw profile/expertise free text is exposed through generic document traversal without going through the MCP adapter's redaction.

### TASK-016: Extend untracked-directory regression coverage for the new content types
- Requirement references: Testing Strategy (design.md), builds on this session's `scripts/repo_files.py` fix
- Description: Add test cases (in the style of `tests/test_repo_files.py`) proving that with `profile/` and `knowledge/professional-context/` now present and git-tracked, an arbitrary untracked local directory (e.g. `local-temp/settings.json`) is still never indexed by the knowledge-graph or discovery-index generators.
- Owner or agent role: QA
- Dependencies: TASK-015
- Status: pending
- Validation: test fails if `discoverable_files()`/`classify_document()` regress to a broader, non-git-scoped walk.
- Completion criteria: explicit assertion that the new Phase 9 content types don't require or introduce any loosening of the existing git-tracked-file scoping.

## MCP and Dashboard

### TASK-017: Add read-only MCP tools
- Requirement references: REQ-004
- Description: `get_professional_profile`, `list_expertise`, `get_work_activity_summary` in `scripts/mcp_server/adapter.py` + `schemas.py`. All read-only, summary-only (no free-text notes, no evidence detail beyond type/ref), matching the existing memory redaction posture. No tool may mutate profile, expertise, or approval state.
- Owner or agent role: builder
- Dependencies: TASK-001–006, TASK-015
- Status: pending
- Validation: TASK-018.
- Completion criteria: matches design.md Interfaces exactly; smoke test proves no mutation path exists.

### TASK-018: Extend `mcp-smoke-test.py`
- Requirement references: REQ-004, Testing Strategy
- Description: Add coverage proving the three new tools are callable, read-only, and summary-only, extending the existing "no approval-mutating tool exposed" case.
- Owner or agent role: QA
- Dependencies: TASK-017
- Status: pending
- Validation: `python scripts/mcp-smoke-test.py` PASS count increases; 0 FAIL.
- Completion criteria: parity with Phase 8's smoke-test rigor.

### TASK-019: Add the "Professional Context" dashboard page
- Requirement references: REQ-007
- Description: Surface the active profile, expertise list, and work-activity highlights, following existing dashboard page conventions (`scripts/dashboard/aggregate.py`, `render.py`, `validate.py`); indicates which profile is active.
- Owner or agent role: builder
- Dependencies: TASK-005, TASK-006, TASK-015
- Status: pending
- Validation: TASK-023.
- Completion criteria: staleness check behaves like every other dashboard page.

## Tests

### TASK-020: `tests/test_profile.py`
- Requirement references: REQ-001, REQ-003, REQ-005, REQ-006
- Description: Schema/validation unit tests mirroring `tests/test_orchestration_*.py` patterns: registry active-flag invariants (zero/one/many-active states); evidence-requirement enforcement; unresolved-evidence-warning behavior; the `memory/`↔`profile/` boundary guard; profile-switch invariants.
- Owner or agent role: QA
- Dependencies: TASK-001–004, TASK-013
- Status: pending
- Validation: self (test suite).
- Completion criteria: covers every acceptance criterion in requirements.md REQ-001, REQ-003, REQ-005, REQ-006.

### TASK-021: `tests/test_work_activity.py`
- Requirement references: REQ-002
- Description: Determinism (identical fixture → identical output ignoring `generatedAt`) and aggregation-correctness tests against a small fixture.
- Owner or agent role: QA
- Dependencies: TASK-006
- Status: pending
- Validation: self.
- Completion criteria: matches design.md Testing Strategy.

### TASK-022: `tests/test_profile_sync_knowledge.py`
- Requirement references: REQ-002, Security/Privacy
- Description: No-overwrite behavior for normal `sync-knowledge`; `--force-refresh` snapshot creation, filename determinism/collision handling; sanitization of injected contact-info/credential-shaped fixture content.
- Owner or agent role: QA
- Dependencies: TASK-008, TASK-009, TASK-010
- Status: pending
- Validation: self.
- Completion criteria: matches design.md Testing Strategy and Security sections exactly.

### TASK-023: Extend `tests/test_dashboard.py` and `validate-all.py` generator-wiring tests
- Requirement references: REQ-002 (constraint), REQ-007
- Description: New dashboard page renders and stales correctly like existing pages; explicit assertion that `generate`/`generate --check` never touch `knowledge/professional-context/` (TASK-011).
- Owner or agent role: QA
- Dependencies: TASK-011, TASK-019
- Status: pending
- Validation: self.
- Completion criteria: both properties are asserted, not just implied.

## Documentation

### TASK-024: Update repository-level documentation
- Requirement references: cross-cutting
- Description: Update `ARCHITECTURE.md`, `SECURITY.md`, `WORKFLOW.md`, `ROADMAP.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, and `README.md` to describe Phase 9, following the same pattern Phase 8 used for these same files.
- Owner or agent role: documentation writer
- Dependencies: all implementation tasks substantially complete (so documentation describes actual behavior, not intent)
- Status: pending
- Validation: `scripts/validate-all.py`'s relative-link and required-template checks.
- Completion criteria: `ROADMAP.md` gains a "Phase 9 — Professional Context and Work Intelligence (Implemented)" entry mirroring the style of Phase 1–8 entries.

### TASK-025: Add `knowledge/architecture/phase-9-professional-context.md`
- Requirement references: cross-cutting, consistency with existing pattern
- Description: Architecture knowledge doc mirroring `knowledge/architecture/phase-8-learning-orchestration.md`'s structure and depth.
- Owner or agent role: documentation writer
- Dependencies: TASK-024
- Status: pending
- Validation: discovery-index/knowledge-graph pick it up correctly after regeneration.
- Completion criteria: matches the established phase-doc format exactly.

## Spec Hygiene

### TASK-026: Verify no stale references to the old `.kiro/specs/phase-9-professional-context/` path remain
- Requirement references: explicit instruction (this document's authoring session)
- Description: Repository-wide search confirming every reference now points at `specs/phase-9-professional-context/`, with only the intentional pointer files (`.kiro/specs/README.md`, `.kiro/specs/phase-9-professional-context/README.md`, `specs/README.md`) mentioning the old path by way of explanation.
- Owner or agent role: reviewer
- Dependencies: none (already performed once during spec authoring; re-run at implementation completion)
- Status: pending
- Validation: `grep -rn ".kiro/specs/phase-9-professional-context" --include="*.md" --include="*.py" --include="*.json" --include="*.yml" .` (excluding `generated/` and pointer files) returns nothing.
- Completion criteria: zero unexplained matches.

### TASK-027: Preserve tool-agnostic design
- Requirement references: explicit instruction (this document's authoring session)
- Description: Confirm nothing added in Phase 9 assumes a specific AI tool or vendor. Specs remain plain Markdown/JSON under `specs/`, usable by Kiro, ChatGPT, Claude, Codex, Copilot, and human contributors alike; `.kiro/` holds only Kiro-specific configuration/steering/prompts, never canonical specification content.
- Owner or agent role: reviewer
- Dependencies: TASK-026
- Status: pending
- Validation: manual review of `specs/phase-9-professional-context/` and `.kiro/` for any tool-specific coupling.
- Completion criteria: a contributor using any of the named tools (or none) can read and act on `specs/phase-9-professional-context/` without additional tooling.

## Final Validation and Stop Condition

### TASK-028: Run the full validation and manual acceptance sequence
- Requirement references: cross-cutting
- Description: `python scripts/ai-os.py generate`, `generate --check`, `python scripts/validate-all.py`, `python scripts/ai-os.py release-check`, `python scripts/mcp-smoke-test.py`, `git diff --check`, and the full `pytest` suite — the same sequence used throughout this repository's history for every phase.
- Owner or agent role: QA
- Dependencies: all prior tasks
- Status: pending
- Validation: all of the above pass cleanly, including with an arbitrary untracked local directory present (per the existing regression pattern).
- Completion criteria: matches the bar every prior phase in this repository has been held to.

### TASK-029: Stop before staging, committing, pushing, merging, tagging, or releasing
- Requirement references: explicit instruction (this document's authoring session)
- Description: Once TASK-001–028 are complete and validated, present the full diff for human review. Do not `git add`, commit, push, merge, tag, or create a release without explicit, separate authorization for that specific action.
- Owner or agent role: reviewer
- Dependencies: TASK-028
- Status: pending
- Validation: n/a (a process boundary, not a code check).
- Completion criteria: implementation is complete and validated, but sits unstaged/uncommitted until explicitly authorized.
