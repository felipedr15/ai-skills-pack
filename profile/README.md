# Professional Profile

Canonical, explicitly-authored professional context: role, team, responsibilities, reporting relationships, and an evidence-based expertise profile.

## Purpose

Give agents a durable, local representation of who the user is professionally and what they have demonstrated expertise in, so responses can be tailored to that context.

## Source of truth

`profile/registry.json` and the profile record files under `profile/` are the source of truth. `generated/profile-index.json` (once Phase 9's generator lands) is a deterministic, derived view and is never authoritative.

## What this is not

- Not `memory/`. `memory/` holds approval-gated *learned* records (lessons, decisions, sessions); `profile/` holds canonical *authored* identity data. Nothing here is inferred, learned, or auto-populated, and no `memory/` record may store profile-shaped facts (role, team, reporting line) — that boundary is enforced by validation, not just convention.
- Not `skill`. The `.agent/skills/` concept and the knowledge graph's `skill` node type describe reusable agent automation skills, not human professional ability. Human proficiency uses the term **expertise**, never "skill" or "competency".
- Not an integration with any external work tool (calendar, email, ticketing, HR system). All profile content is authored or imported locally as files.
- Not automatically switched. The schema supports multiple profiles, but exactly one is active at a time, and only an explicit, user-invoked action may change which one.

## Structure

- `registry.json`: lists every profile record and which single one is `active`.
- `<id>.md`: a profile record (front matter + prose) — role, team, responsibilities, reporting relationships.
- `<id>.expertise.json`: the expertise entries for that profile, each with an evidence-based proficiency level (`foundational`, `working`, `proficient`, `advanced`, `lead`) and at least one `{type, ref}` evidence pointer.

An empty `profile/` (no profile record yet) is a valid, expected starting state — nothing here is fabricated or guessed on the user's behalf.

## Evidence-based expertise

Every expertise entry must be backed by at least one evidence pointer: `{"type": "project|role|source|session|workActivity|memory", "ref": "<normalized-identifier>"}`. `ref` is a stable slug, never free text, a file path, or the source material itself — expertise claims must not be inflated beyond what the evidence actually supports.

## Security restrictions

Do not store secrets, credentials, production access details, or confidential material of any kind. Do not store personal contact information (home address, personal phone/email), employee or customer records, physical or IT asset details, or any County (or other employer) security-sensitive operational information. Evidence pointers reference such material conceptually by a normalized identifier — never the material itself. See `SECURITY.md` for repository-wide security policy.

## Commands

Phase 9 data-layer validation (`scripts/profile/validate.py`) is available now; CLI commands (`ai-os.py profile show|switch|sync-knowledge`) and generators land in later Phase 9 task groups.

[Back to AI OS](../README.md)
