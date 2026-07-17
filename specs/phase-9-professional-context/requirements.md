# Requirements — Phase 9: Professional Context and Work Intelligence

## Summary
Extend the Phase 8 data model (memory engine, knowledge graph, session tracking, approval engine) with a new, strictly local-first layer that captures the user's professional role/organizational context as canonical authored records, derives work-activity signals from data already captured by prior phases, and maintains a queryable **expertise** profile — all read-only from the agent's perspective except where the user explicitly approves a write.

## Problem Statement
AI OS currently has no representation of *who the user is professionally* or *what they actually work on over time*. Agents operating against this repository have no way to tailor behavior to the user's role, team, or expertise, and no way to surface patterns in the user's own work activity that Phases 2 (Memory) and 8 (Sessions) already capture but never aggregate or expose.

## Goals
- Capture and query professional role/organizational context (role, team, responsibilities, reporting relationships) as canonical, explicitly-authored records, kept separate from the learned-memory system.
- Derive work-activity signals (what the user has actually been working on, and how often) from existing session and memory data — no new raw data collection.
- Maintain a queryable **expertise** profile using evidence-based proficiency levels, combining explicit user statements with signals inferred from work activity.
- Preserve every non-negotiable established by Phases 1–8: local-first, no network calls, no telemetry, deterministic generation, explicit approval before any write to durable state, read-only MCP tools by default.

## Non-Goals
- No integration with external work tools (calendar, email, ticketing, HR systems) — all professional-context data is authored or imported locally as files.
- No automatic inference of role/org data from repo content — role/org context is explicitly authored, not guessed.
- No execution engine or automated action-taking based on inferred context (consistent with Phase 8's "planning and tracking only" boundary).
- Does not reuse or overload the existing `skill` node type / `.agent/skills/` concept — professional expertise is a distinct concept with its own vocabulary ("expertise", not "skill" or "competency").
- No automatic profile switching. Phase 9 implements exactly one active primary professional profile; multi-profile schema support exists but only one profile is populated and switching is always an explicit user action.

## Users
- The individual using AI OS day-to-day, whose professional context is being captured.
- Agents (Claude Code and others) consuming this context via MCP to tailor responses.

## Functional Requirements

### REQ-001: Professional profile source records
- Description: Canonical, explicitly-authored professional profile records (role, team, responsibilities, reporting relationships) live under a new top-level `profile/` directory, structurally parallel to `memory/` but never stored inside it.
- Priority: Must
- Rationale: `memory/` is reserved for approval-gated *learned* memory (lessons, decisions, session artifacts); the canonical professional profile is authored identity data, not something the system learns or infers, and mixing the two would blur an important distinction the rest of the system already relies on.
- Acceptance criteria: A schema exists under `profile/` with required fields (profile id, role, team, responsibilities, updatedAt, `active` flag); a validation script checks it; `memory/` validation explicitly rejects any attempt to store canonical profile records there.

### REQ-002: Work-activity aggregation
- Description: A deterministic generator that derives work-activity signals (active projects, recent focus areas, frequency of engagement) purely from existing `memory/`, `generated/knowledge-graph.json`, and `.ai-os/sessions/` data — no new inputs. Machine-readable output is a generated artifact under `generated/`; a human-readable derived summary is maintained under `knowledge/professional-context/`.
- Priority: Must
- Rationale: This directly answers "work intelligence" without introducing new tracking surface area, and follows the existing split between machine-readable `generated/` artifacts and human-readable `knowledge/` documents used elsewhere in the repo.
- Acceptance criteria: The `generated/` artifact has a staleness check wired into `validate-all.py`, exactly like every other Phase 1–8 generator; the `knowledge/professional-context/` document's generation/authorship mechanism is defined precisely in design.md.

### REQ-003: Expertise profile
- Description: A queryable record of the user's expertise, combining explicit entries (user states they have expertise in X) with signals derived from REQ-002. Each entry has an evidence-based proficiency level from the fixed set: `foundational`, `working`, `proficient`, `advanced`, `lead`.
- Priority: Must
- Rationale: Answers "work intelligence" from the expertise angle without colliding with the existing `skill` (agent-automation) vocabulary.
- Acceptance criteria: Uses "expertise" exclusively as the vocabulary term throughout schema, node types, MCP tool names, and docs (never "skill" or "competency" for this concept); each entry's proficiency level is backed by a recorded evidence reference (e.g. linked work-activity signal, project, or session), not asserted without support; validated for the "expertise" vs "skill" distinction explicitly.

### REQ-004: Read-only MCP exposure
- Description: New MCP tools/resources to query the professional profile, work-activity signals, and expertise, following the exact pattern of Phase 8's 14 read-only tools.
- Priority: Must
- Rationale: Consistency with the established MCP contract (no approval-mutating tools exposed, per the existing smoke test).
- Acceptance criteria: `mcp-smoke-test.py` gains coverage proving no new tool can mutate profile, expertise, or approval state; responses are summary-only by default, matching the existing memory redaction pattern.

### REQ-005: Approval-gated writes
- Description: Any write to `profile/` or the expertise record — whether user-initiated or agent-suggested — goes through Phase 8's existing approval engine; no auto-approve path. This is distinct from, and does not replace, the existing memory-suggestion approval flow: the system may still propose approval-gated *learned* memory entries (e.g. a lesson about how the user works) under `memory/`, but those are never treated as, or promoted to, canonical profile data.
- Priority: Must
- Rationale: This is more sensitive personal data than repo lessons/decisions; the bar should be at least as high, not lower, and the `profile/` vs `memory/` boundary (REQ-001) must hold even under agent-proposed writes.
- Acceptance criteria: Reuses `scripts/orchestration/approvals.py` rather than introducing a parallel approval mechanism; approval records distinguish a "profile" target type from existing target types.

### REQ-006: Profile switching
- Description: The profile schema supports multiple professional profiles (e.g. a contractor working across multiple client contexts), each with a unique id, but Phase 9 implements and populates exactly one active primary profile. Switching which profile is active is always an explicit, user-initiated action — never automatic or inferred.
- Priority: Must
- Rationale: Avoids a schema migration later if multi-profile support is needed, without taking on the complexity of implementing or exposing multi-profile switching in this phase.
- Acceptance criteria: Schema supports an `active` flag/pointer across potentially many profile records; exactly one record is marked active at any time; only one profile record is created by Phase 9 tooling; no code path switches `active` without an explicit user-invoked command.

### REQ-007: Dashboard visibility
- Description: A new dashboard page (or section of an existing one) surfacing the active professional profile, work-activity signals, and expertise, consistent with Phase 8's 8 new dashboard pages.
- Priority: Should
- Rationale: Parity with how every other generated artifact in this system is made visible.
- Acceptance criteria: Follows existing dashboard page conventions (`scripts/dashboard/`); indicates which profile is currently active.

## Non-Functional Requirements

### Security / Privacy
- No network calls, no telemetry — matches every prior phase.
- Professional-context and expertise data defaults to high sensitivity; MCP responses return summaries only (mirroring the existing "memory returns summary only" behavior), never full records, unless a future requirement explicitly changes that.
- A clear, documented way to purge/redact professional-context data entirely (this is personal data about the user, not project knowledge).
- `memory/` validation must actively guard against canonical profile data being stored there (REQ-001), not merely rely on convention.

### Reliability
- Deterministic generation — identical inputs produce byte-identical output (ignoring `generatedAt`), matching the standard already enforced across all generators.

### Maintainability
- New record/artifact types follow the exact schema-versioning, validation, and staleness-check conventions already established (schemaVersion field, `--check` mode, `validate-all.py` wiring).

### Compatibility
- No changes to existing Phase 1–8 schemas, node types, or CLI commands; strictly additive.

## Dependencies
- Phase 2 Memory Engine (schema/validation conventions to mirror; also the system whose boundary with `profile/` must be enforced)
- Phase 3 Knowledge Graph (for linking professional-context nodes to existing entities; repository indexing conventions may need a new `profile` category)
- Phase 8 Orchestration (approval engine, session tracking data as an input to REQ-002)

## Assumptions
- The user is willing to manually author/import professional-context data as local files; no external system will ever push data into this phase.
- "Work activity signals" derived purely from existing local data is sufficient value without external tool integration.

## Constraints
- Must not introduce any new external dependency (matches every prior phase's "standard library only" pattern where applicable).
- Must not store canonical profile data under `memory/`.
- Must use "expertise" as the vocabulary term for human proficiency; must not reuse "skill" or "competency" for this concept.
- Proficiency levels are limited to the fixed set: `foundational`, `working`, `proficient`, `advanced`, `lead`.

## Risks
- **`generated/` vs `knowledge/` boundary for REQ-002**: placing a "derived" document under `knowledge/professional-context/` sits slightly against the existing convention that `knowledge/` holds hand-authored, versioned content while `generated/` holds fully regenerable output. The exact authorship/regeneration mechanism must be resolved precisely in design.md to avoid ambiguity about whether that document is a source of truth.
- **Evidence requirement enforcement**: REQ-003's "evidence-based" proficiency levels are only meaningful if evidence linkage is actually validated, not just documented as a convention.
- **Profile/memory boundary drift**: without an active validation guard (not just convention), agent-proposed memory suggestions could drift into storing profile-like facts under `memory/` over time.

## Open Questions
- Exact generation/authorship mechanism for the `knowledge/professional-context/` document (fully auto-generated like `generated/*.md`, or periodically synthesized with human review) — to be resolved in design.md.
- Whether `profile/` needs to be added as a new category in `scripts/index-repository.py`'s `CATEGORIES` tuple, and if so, whether repository-index inclusion is appropriate for data this sensitive — to be resolved in design.md.
