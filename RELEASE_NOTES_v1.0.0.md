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

## Validation Results

Current results recorded during this branch work:

- Targeted approval and release tests: 72 passed.
- MCP integration tests: 126 passed.
- MCP smoke test baseline: 29 passed, 0 failed.
- Baseline `validate-all.py`: 15 passed, 8 failed before regeneration.
- Baseline pytest in the managed Windows sandbox: 457 passed, 320 failed, 70 errors, dominated by temp-directory permission failures.
- Baseline release-check: 8/16 passed before regeneration.
- `git diff --check`: passed at baseline.

Final full-suite validation must be rerun after deterministic artifact regeneration.

## Security And Privacy

- No credentials, secrets, tokens, usernames, private keys, or `.env` files are introduced.
- MCP remains read-only and auditable.
- Approval mutation remains CLI-only.
- Memory promotion remains explicitly approval-gated.
- Professional profile switching remains explicitly approval-gated.
- Sanitization remains deterministic and still requires human review for sensitive data.

## Known Limitations

- Full generated-artifact regeneration and final acceptance validation are required before tagging.
- Approval expiration remains deferred.
- `scripts/profile/` still shadows Python's standard-library `profile` module.
- Richer professional-context graph relationships remain deferred pending privacy review.
- Evidence-resolution visibility in MCP/dashboard remains deferred.
- Local sandbox test execution on Windows/Python 3.14.4 can fail due to temporary-directory permissions.

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

Prepared for review. Do not create the `v1.0.0` tag or GitHub Release until the final acceptance table passes.

**Full Changelog**: https://github.com/felipedr15/ai-skills-pack/compare/v0.9.0...v1.0.0
