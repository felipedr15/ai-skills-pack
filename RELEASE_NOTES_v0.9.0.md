# AI OS v0.9.0 — Professional Context and Work Intelligence

## Highlights

- Added a structured, local-first professional-context layer under `profile/`, structurally
  parallel to `memory/` but never stored inside it.
- Added a multiple-profile-capable schema with exactly one explicitly active profile at a time;
  an empty registry is a valid, expected state.
- Added evidence-based expertise records with five fixed proficiency levels: `foundational`,
  `working`, `proficient`, `advanced`, `lead`, each backed by a `{type, ref}` evidence pointer.
- Added deterministic `generated/profile-index.json`/`.md` and `generated/work-activity.json`/`.md`
  artifacts, wired into the existing generation order and `validate-all.py`.
- Added privacy, sanitization, and profile/memory boundary protections — `memory/` validation
  actively rejects records carrying reserved profile-only keys (`role`, `team`, `reportingTo`).
- Added read-only `profile list`/`profile show` CLI commands and explicit, approval-gated
  `profile switch`, reusing the existing Phase 8 approval engine with three new approval types
  (`profile-write`, `expertise-write`, `profile-switch`).
- Added safe `profile sync-knowledge` scaffolding (no-overwrite) and explicit
  `--force-refresh` checkpoint snapshots that never rewrite curated content.
- Added minimal `profile` node-type classification to the knowledge graph and semantic
  discovery, with role/team/expertise/prose deliberately withheld from generic traversal.
- Added three read-only, summary-only MCP tools: `get_professional_profile`, `list_expertise`,
  `get_work_activity_summary`.
- Added the Professional Context dashboard page (static, no browser-side network calls).
- Added complete tests and a dedicated architecture document
  (`knowledge/architecture/phase-9-professional-context.md`).

No professional profile is included with this release — `profile/registry.json` ships as an
empty scaffold, and no curated `knowledge/professional-context/` content exists.

## Validation

- Full pytest: 772/772
- `validate-all.py`: 23/23
- `release-check`: 16/16
- MCP smoke test: 29/29
- Knowledge graph: 357 nodes / 611 edges
- Semantic discovery: 333 documents / 357 entities / 1089 terms
- `git diff --check`: clean
- CI passed on `main`

## Privacy and security

- No real professional profile is populated by default.
- `profile/registry.json` remains an empty scaffold.
- No raw resume or performance-evaluation content is stored.
- No network calls, telemetry, automatic approvals, or automatic memory promotion.
- MCP and dashboard integrations are read-only.

## Known limitations

- `scripts/profile/` shadows Python's standard-library `profile` module.
- Approval expiry is not implemented.
- Malformed approval-store records may trigger the pre-existing Phase 8 `KeyError`.
- Live `.ai-os/sessions/` data is excluded from deterministic work-activity artifacts.
- `windowDays` is descriptive metadata, not a wall-clock filter.
- `--force-refresh` creates a checkpoint snapshot but does not regenerate curated content.
- Sanitization is regex-based and still requires human review.
- Richer role/team/expertise graph relationships are deferred to a later phase.
- Evidence-resolution status is not shown through MCP or the dashboard.

**Full Changelog**: https://github.com/frojas15/ai-skills-pack/compare/v0.8.0...v0.9.0
