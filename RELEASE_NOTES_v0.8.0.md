## What's Changed
* feat: add Phase 8 continuous learning and agent orchestration by @frojas15 in https://github.com/frojas15/ai-skills-pack/pull/2

## New Contributors
* @frojas15 made their first contribution in https://github.com/frojas15/ai-skills-pack/pull/2

**Full Changelog**: https://github.com/frojas15/ai-skills-pack/compare/v0.7.0...v0.8.0

## Additional fixes included after PR #2

The following follow-up changes were committed directly to `main` after the Phase 8 pull request and are included in the `v0.8.0` tag:

- Fixed cross-platform generated-artifact consistency by normalizing line endings for PowerShell, HTML, and shell files.
- Reworked dashboard staleness validation so it no longer depends on filesystem modification times that Git does not preserve across checkouts.
- Regenerated the release manifest after the artifact-normalization changes so recorded file sizes and hashes match the final release contents.
- Restricted discovery-index and knowledge-graph file collection to Git-tracked repository files, with a deterministic fallback allowlist when Git is unavailable.
- Added regression coverage to prevent arbitrary local or untracked directories such as `.vscode/` from affecting generated artifacts.
- Updated the project version for the `v0.8.0` release.

## Final validation

- Full test suite: 508/508
- Unified validation: 21/21
- Release checks: 14/14
- MCP smoke tests: 24/24
- Deterministic generated output verified with arbitrary local directories present
- CI passed on `main`
