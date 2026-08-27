# AI OS Command Reference

A practical cheat sheet of the commands used most often when working in this repository —
day-to-day CLI usage, validation, and the release/Git workflow. All commands run from the
repository root. `python scripts/ai-os.py <command>` is the unified entry point; standalone
scripts (`scripts/generate-*.py`, `scripts/validate-*.py`, etc.) exist for direct/CI use.

## Core CLI (`scripts/ai-os.py`)

| Command | What it does | Example |
|---|---|---|
| `version` | Print the current AI OS version (reads `VERSION`). | `python scripts/ai-os.py version` |
| `status` | Show subsystem health backed by generated-artifact freshness checks. | `python scripts/ai-os.py status --json` |
| `doctor` | Run environment diagnostics (Python version, Git, artifacts present, port availability). | `python scripts/ai-os.py doctor` |
| `bootstrap` | One-command setup for a fresh clone (generates artifacts, checks environment). | `python scripts/ai-os.py bootstrap` |
| `validate` | Run unified validation (wraps `validate-all.py`). | `python scripts/ai-os.py validate` |
| `test` | Run the unit test suite. | `python scripts/ai-os.py test` |
| `build` / `generate` | Generate all derived artifacts in dependency order. | `python scripts/ai-os.py generate` |
| `generate --check` | Verify generated artifacts are current without writing anything; fails if stale. | `python scripts/ai-os.py generate --check` |
| `dashboard` / `start-dashboard` | Start the local read-only web dashboard (default port 8080). | `python scripts/ai-os.py dashboard` |
| `start-mcp` | Start the MCP server over stdio. | `python scripts/ai-os.py start-mcp` |
| `smoke-test` | Run the MCP smoke test. | `python scripts/ai-os.py smoke-test` |
| `mcp check` | Run the MCP smoke test through the unified MCP command group. | `python scripts/ai-os.py mcp check` |
| `mcp start` | Start the MCP server through the unified MCP command group. | `python scripts/ai-os.py mcp start` |
| `release-check` | Run the full release-readiness gate (version, artifacts, MCP, validation). | `python scripts/ai-os.py release-check` |
| `package` | Build a release package (zip/tar + checksums) under `dist/`. | `python scripts/ai-os.py package` |
| `package --dry-run` | Preview what `package` would include without writing files. | `python scripts/ai-os.py package --dry-run` |
| `backup` | Archive `generated/*` to `.ai-os/backups/` (local only, git-ignored). | `python scripts/ai-os.py backup` |
| `restore` | Restore a previous backup archive. | `python scripts/ai-os.py restore <path>` |
| `clean-generated` | Remove generated artifacts (requires `--confirm`). | `python scripts/ai-os.py clean-generated --confirm` |
| `migrate` | Check/report migration status (schema/version compatibility). | `python scripts/ai-os.py migrate --check` |
| `help` | List all available commands. | `python scripts/ai-os.py help` |

## Task Planning and Orchestration (Phase 8)

| Command | What it does | Example |
|---|---|---|
| `classify` | Deterministically classify a task's intent (no execution). | `python scripts/ai-os.py classify "Fix the login bug"` |
| `plan` | Build a structured task plan (workflow, agents, retrieved knowledge). | `python scripts/ai-os.py plan "Fix the login bug" --explain` |
| `workflow list` \| `show <id>` | List or inspect workflow registry entries. | `python scripts/ai-os.py workflow show workflow:bug-fix` |
| `session start "<task>"` | Start a local work session from a task description. | `python scripts/ai-os.py session start "Fix the login bug"` |
| `session validate <id>` | Record a validation result against a session. | `python scripts/ai-os.py session validate <id> --name unit-tests --status pass` |
| `session complete <id>` | Complete a validated session (may trigger a memory suggestion). | `python scripts/ai-os.py session complete <id>` |
| `session archive <id>` | Archive a completed/cancelled session. | `python scripts/ai-os.py session archive <id>` |
| `approval list` | List approval gates, optionally filtered by status. | `python scripts/ai-os.py approval list --status pending` |
| `approval approve <id>` | Explicitly approve a pending approval — the only way anything becomes approved. | `python scripts/ai-os.py approval approve <id>` |
| `approval reject <id>` | Reject a pending approval. | `python scripts/ai-os.py approval reject <id> --reason "not needed"` |
| `memory-suggestions list` | List pending/approved memory suggestions. | `python scripts/ai-os.py memory-suggestions list --status pending` |
| `memory-suggestions approve <id>` | Promote a suggestion into `memory/` (requires an approved `permanent-memory` approval). | `python scripts/ai-os.py memory-suggestions approve <id>` |
| `knowledge-health` | Show the live knowledge health score and category breakdown. | `python scripts/ai-os.py knowledge-health` |
| `knowledge-gaps` | Show detected knowledge gaps and recommendations. | `python scripts/ai-os.py knowledge-gaps` |
| `review-due` | List documents due for review (opt-in freshness metadata). | `python scripts/ai-os.py review-due --days 30` |
| `feedback add` | Record local feedback about a skill/document/entity. | `python scripts/ai-os.py feedback add --type outdated --target-type document --target-id x.md` |
| `audit list` \| `validate` | Inspect or verify the hash-chained local audit trail. | `python scripts/ai-os.py audit validate` |

## Professional Context / Profile (Phase 9)

| Command | What it does | Example |
|---|---|---|
| `profile list` | List registered professional profiles (read-only). | `python scripts/ai-os.py profile list` |
| `profile show [id]` | Show the active profile, or a specific one by id (read-only). | `python scripts/ai-os.py profile show` |
| `profile switch <id>` | Explicitly switch the active profile — requires an approved `profile-switch` approval; the first run requests it and stops. | `python scripts/ai-os.py profile switch example-profile` |
| `profile sync-knowledge` | Scaffold `knowledge/professional-context/overview.md` only if it doesn't already exist (safe, no-overwrite). | `python scripts/ai-os.py profile sync-knowledge` |
| `profile sync-knowledge --force-refresh` | Checkpoint the current curated overview into a dated snapshot — never rewrites `overview.md`. | `python scripts/ai-os.py profile sync-knowledge --force-refresh` |
| `generate-profile-index.py --check` | Verify `generated/profile-index.json`/`.md` are current. | `python scripts/generate-profile-index.py --check` |
| `generate-work-activity.py --check` | Verify `generated/work-activity.json`/`.md` are current. | `python scripts/generate-work-activity.py --check` |

## Memory Engine (Phase 2)

| Command | What it does | Example |
|---|---|---|
| `memory-add.py` | Create a new memory record (lesson, decision, convention, etc.). | `python scripts/memory-add.py --type lesson --title "Example" --scope global --summary "..."` |
| `memory-list.py` | List memory records, optionally filtered by type. | `python scripts/memory-list.py --type lesson` |
| `memory-search.py` | Search memory records by keyword/tag. | `python scripts/memory-search.py "keyword" --tag refresh` |
| `memory-archive.py` | Archive a memory record (never deletes it). | `python scripts/memory-archive.py --id lesson-example-001` |
| `memory-promote.py` | Promote a session record into a permanent lesson/decision. | `python scripts/memory-promote.py --id session-example-001 --target-type lesson --reason "..."` |
| `generate-memory-index.py [--check]` | (Re)generate or verify `generated/memory-index.{json,md}`. | `python scripts/generate-memory-index.py --check` |

## Knowledge Graph and Semantic Discovery (Phases 3–4)

| Command | What it does | Example |
|---|---|---|
| `generate-knowledge-graph.py [--check]` | (Re)generate or verify `generated/knowledge-graph.{json,md}`. | `python scripts/generate-knowledge-graph.py --check` |
| `validate-knowledge-graph.py` | Structurally validate the knowledge graph (also reports unresolved-reference/isolated-node warnings). | `python scripts/validate-knowledge-graph.py` |
| `discovery-build.py [--check]` | (Re)generate or verify `generated/discovery-index.{json,md}`. | `python scripts/discovery-build.py --check` |
| `discovery-validate.py` | Structurally validate the discovery index. | `python scripts/discovery-validate.py` |

## Validation and Release

| Command | What it does | Example |
|---|---|---|
| `validate-all.py` | Run every structural/staleness/security check in the repository (the full gate). | `python scripts/validate-all.py` |
| `validate-memory-security.py` | Scan memory records for secret-like patterns. | `python scripts/validate-memory-security.py` |
| `mcp-smoke-test.py` | Exercise the MCP server end-to-end over stdio. | `python scripts/mcp-smoke-test.py` |
| `dashboard-check.py` | Verify dashboard artifacts are current. | `python scripts/dashboard-check.py` |
| `dashboard-validate.py` | Structurally validate dashboard artifacts. | `python scripts/dashboard-validate.py` |
| `python -m pytest -q` | Run the full test suite directly (equivalent to `ai-os.py test`, useful for isolating failures). | `python -m pytest tests/test_profile.py -q` |

**Run validation/pytest commands one at a time, not concurrently** — several share local
`.ai-os/` runtime state and can race against each other if run in parallel.

## Release and Git Workflow

These are the commands actually used to prepare, validate, and publish a release in this
repository (see `CHANGELOG.md`/`RELEASE_NOTES_v*.md` for what each release contains).

| Command | What it does | Example |
|---|---|---|
| `git fetch origin` | Update remote-tracking refs without touching your working tree. | `git fetch origin` |
| `git status -sb` | Show branch, ahead/behind count, and changed files in one line each. | `git status -sb` |
| `git rev-list --left-right --count origin/main...HEAD` | Print `<behind> <ahead>` commit counts vs. the remote. | `git rev-list --left-right --count origin/main...HEAD` |
| `git log --oneline v0.8.0..HEAD` | List commits since a given tag. | `git log --oneline v0.8.0..HEAD` |
| `git diff --stat` / `--cached --stat` | Summarize unstaged/staged changes by file. | `git diff --cached --stat` |
| `git diff --check` / `--cached --check` | Fail if the (staged) diff contains whitespace errors. | `git diff --cached --check` |
| `git add <path> [<path> ...]` | Stage specific reviewed files (prefer explicit paths over `-A`). | `git add VERSION CHANGELOG.md` |
| `git commit -m "<message>"` | Create a new commit (never amend/squash existing pushed commits without being asked). | `git commit -m "chore: prepare AI OS v1.0.0 release"` |
| `git push origin main` | Push commits on `main` (never force-push without explicit instruction). | `git push origin main` |
| `git tag -a vX.Y.Z -m "<message>"` | Create an annotated tag on the current commit. | `git tag -a v0.9.0 -m "AI OS v0.9.0 — ..."` |
| `git push origin vX.Y.Z` | Push a single tag (prefer this over `git push --tags`). | `git push origin v0.9.0` |
| `git show vX.Y.Z --no-patch` | Verify what commit a tag points to and its message. | `git show v0.9.0 --no-patch` |
| `gh run list --branch main --limit 5` | Check recent CI run status for a branch. | `gh run list --branch main --limit 5` |
| `gh run view <id> --log-failed` | Show logs for the failing step(s) of a CI run. | `gh run view 123456 --log-failed` |
| `gh release create vX.Y.Z --title "..." --notes-file <file> --target main --latest` | Publish a GitHub release from a pushed tag. | `gh release create v0.9.0 --title "AI OS v0.9.0" --notes-file RELEASE_NOTES_v0.9.0.md --target main --latest` |
| `gh release view vX.Y.Z --json isDraft,isPrerelease,url` | Verify a release's publish state. | `gh release view v0.9.0 --json isDraft,isPrerelease,url` |
| `git describe --tags --always` | Show how far HEAD is from the nearest tag (or the tag itself, if exact). | `git describe --tags --always` |
| `git switch --detach vX.Y.Z` | Check out an exact tagged release read-only, without moving `main`. | `git switch --detach v0.9.0` |
| `git pull --ff-only origin main` | Update a local clone, refusing to create a merge commit. | `git pull --ff-only origin main` |

## Syncing another machine

**Existing clone:**
```bash
git switch main
git status                       # check for local work first
git fetch origin --tags
git pull --ff-only origin main
git describe --tags --always
python scripts/ai-os.py version
python scripts/ai-os.py doctor
python scripts/ai-os.py generate --check
python scripts/validate-all.py
```

**New clone:**
```bash
git clone https://github.com/felipedr15/ai-skills-pack.git
cd ai-skills-pack
git fetch --tags
git switch main
git pull --ff-only origin main
python scripts/ai-os.py doctor
python scripts/ai-os.py generate --check
python scripts/validate-all.py
```

[Back to AI OS](../README.md)
