# AI OS v1.0.0 — Production Hardening & Unified Experience

## Overview

AI OS v1.0.0 prepares the existing AI development operating system for its first production-quality release. This release focuses on hardening, portability, validation, repository ownership cleanup, and a unified operator experience.

## Major Improvements

- Added a formal baseline audit and v1.0 acceptance criteria.
- Classified known technical debt into critical, recommended, deferred, and no-longer-defect categories.
- Hardened approval-store handling for malformed records.
- Improved unified status reporting so readiness is based on real generated-artifact checks.
- Added canonical multi-device setup documentation.

## Portability

- MCP can now honor `AI_OS_HOME` when it points at a valid AI OS root.
- MCP safely falls back to the repository containing `scripts/mcp-server.py`.
- MCP documentation no longer uses committed user-specific absolute paths as canonical examples.
- Added `python scripts/ai-os.py mcp check` and `python scripts/ai-os.py mcp start`.

## CI Improvements

- Reworked GitHub Actions into **AI OS CI**.
- CI now runs on pushes to `main`, pull requests into `main`, and manual dispatch.
- Python is pinned to 3.12 for intentional compatibility.
- Jobs are named for repository validation, unit tests, MCP smoke tests, release readiness, and diff hygiene.
- Workflow permissions remain read-only.
- Obsolete runs are cancelled through workflow concurrency.

## Technical Debt Fixes

- Malformed approval records no longer trigger unsafe direct-key crashes during normal approval operations.
- `status` no longer reports release readiness from artifact existence alone.
- Repository ownership references now point at `felipedr15/ai-skills-pack`.
- Generated-artifact regeneration is now idempotent: `python scripts/ai-os.py build` and
  `python scripts/dashboard-build.py` no longer rewrite committed artifacts (and dirty the working
  tree) on a rerun with no meaningful source change. The dashboard's filesystem-mtime-derived
  `fileTimestamp` field, which varied across clones and computers, was removed from committed
  output entirely. See [docs/v1.0-technical-debt.md](docs/v1.0-technical-debt.md#stale-generated-artifacts).
- Fixed a repository-indexing/knowledge-graph/semantic-discovery/MCP-path-permission bug where the
  `.agent/skills/build/` skill category collided with a generic "skip build-output directories"
  exclusion rule, silently hiding all 7 files under that category (creator, frontend,
  performance-optimization, vercel-agent, vercel-react, web-design-guidelines, and the category's
  own index file) from indexing, search, the knowledge graph, and MCP file access.
- `.kiro/settings/mcp.json` no longer commits a device-specific absolute path; it now uses the same
  `<PYTHON_EXECUTABLE>`/`<REPOSITORY_ROOT>` placeholders as `examples/mcp/`.

## Validation Results

Final results, recorded on this machine (Windows, Python 3.12.10) after the fixes above:

- `python scripts/ai-os.py doctor`: 15/15 PASS.
- `python scripts/ai-os.py status`: `Overall: HEALTHY`.
- Two consecutive `python scripts/ai-os.py build` runs: idempotent, no diff on the second run.
- `python scripts/ai-os.py build --check`: PASS.
- `python scripts/validate-all.py`: 23 PASS, 0 WARNING, 0 FAIL.
- `python -m unittest discover -s tests -v`: 790 passed.
- `python -m pytest -q` (local `.venv`, pytest 9.1.1): 790 passed, 15 subtests passed.
- `python scripts/ai-os.py release-check`: 16/16 PASS.
- `python scripts/mcp-smoke-test.py`: 29 PASS, 0 FAIL.
- `git diff --check`: PASS.

Full detail, including the knowledge-graph warning breakdown, is in
[docs/v1.0-final-acceptance.md](docs/v1.0-final-acceptance.md).

## Security And Privacy

- No credentials, secrets, tokens, usernames, private keys, or `.env` files are introduced.
- MCP remains read-only and auditable.
- Approval mutation remains CLI-only.
- Memory promotion remains explicitly approval-gated.
- Professional profile switching remains explicitly approval-gated.
- Sanitization remains deterministic and still requires human review for sensitive data.

## Known Limitations (Deferred Post-v1.0)

- Approval expiration remains deferred.
- `scripts/profile/` still shadows Python's standard-library `profile` module.
- Richer professional-context graph relationships remain deferred pending privacy review.
- Evidence-resolution visibility in MCP/dashboard remains deferred.
- The knowledge graph reports 3 unresolved references and 51 isolated nodes; both are reviewed and
  documented as intentional/by-design, not defects -- see
  [docs/v1.0-final-acceptance.md](docs/v1.0-final-acceptance.md#knowledge-graph-warnings).
- Local test execution inside some managed/sandboxed environments on Windows can hit
  temporary-directory permission errors unrelated to application code; running directly (as done
  for this release's validation) does not reproduce this.

## Upgrade Instructions

```powershell
git switch main
git pull --ff-only origin main
python scripts/ai-os.py doctor
python scripts/ai-os.py status
python scripts/ai-os.py build --check
python scripts/ai-os.py validate
```

If generated artifacts are stale:

```powershell
python scripts/ai-os.py build
git diff --check
```

Review generated diffs before committing them.

## Fresh Clone Instructions

```powershell
git clone https://github.com/felipedr15/ai-skills-pack.git
cd ai-skills-pack
python --version
python scripts/ai-os.py doctor
python scripts/ai-os.py status
python scripts/ai-os.py build --check
python scripts/ai-os.py validate
python scripts/ai-os.py mcp check
```

## Release Status

The `v1.0.0` Git tag and the GitHub Release both already exist (published 2026-08-27) and are not
modified by this document or by the work described here.

This document distinguishes four separate things:

1. **Technical validation status**: complete and passing as of this update -- see Validation
   Results above and [docs/v1.0-final-acceptance.md](docs/v1.0-final-acceptance.md) for the full
   PASS/FAIL table, run after the idempotency and indexing fixes described under Technical Debt
   Fixes.
2. **Existing tag/release status**: unchanged. The `v1.0.0` tag and GitHub Release were created
   before this final validation pass completed; they are not retroactively moved, edited, or
   deleted by this work. If the release body should reflect the corrected validation results, copy
   the updated text over manually through the normal GitHub Release edit flow -- this repository's
   tooling does not do that automatically.
3. **Remaining documentation/process cleanup**: this file and
   [docs/v1.0-technical-debt.md](docs/v1.0-technical-debt.md) have been corrected to match actual
   repository state as of this update.
4. **Deferred post-v1.0 technical debt**: see Known Limitations above -- none of these block v1.0
   and all are explicitly deferred, not silently dropped.

**Full Changelog**: https://github.com/felipedr15/ai-skills-pack/compare/v0.9.0...v1.0.0
