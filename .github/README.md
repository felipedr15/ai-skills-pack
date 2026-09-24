# GitHub Configuration

This folder contains Copilot guidance, path-specific instructions, and repository automation.

## Workflows

### `validate.yml` — Continuous Integration

The primary CI/CD workflow runs on every push to `main` and on pull requests.

**Triggered by:**
- Push to `main` branch
- Pull requests targeting `main`
- Manual workflow dispatch (Actions tab)

**Jobs:**
1. **Repository Validation** — Runs `python scripts/validate-all.py` to check generated artifacts, registries, and repository structure
2. **Unit Tests** — Runs `python -m unittest discover -s tests` for Python test suite
3. **MCP Smoke Tests** — Runs `python scripts/ai-os.py mcp check` to validate MCP configuration
4. **Release Readiness** — Runs `python scripts/ai-os.py release-check` to verify release prerequisites
5. **Diff Hygiene** — Runs `git diff --check` to ensure proper whitespace
6. **Secrets Scan** — Runs memory and pattern-based secret validation

**Status badges:** [![AI OS CI](https://github.com/felipedr15/ai-skills-pack/actions/workflows/validate.yml/badge.svg)](https://github.com/felipedr15/ai-skills-pack/actions/workflows/validate.yml)

**Configuration:**
- Concurrency: Only one workflow run per branch; cancel in-progress runs
- Permissions: Read-only access to repository contents
- Python version: 3.12
- Caching: pip dependencies cached for faster runs

**What must pass before merge:**
- All validation jobs must succeed
- No whitespace violations
- No detected secrets in memory
- Generated artifacts must be current (not stale)
- All unit tests must pass
- MCP configuration must be valid
- Release prerequisites must be met

## Branch Protection

Recommended branch protection settings for `main`:

- ✅ Require pull request review
- ✅ Require status checks to pass: `validate.yml` jobs
- ✅ Require branches to be up to date before merging
- ✅ Dismiss stale reviews when new commits are pushed
- ⚠️ Restrict force pushes and deletions

See [Settings → Branches](https://github.com/felipedr15/ai-skills-pack/settings/branches) to configure.

## Guidance for Contributors

### Before Pushing

1. Run `python scripts/validate-all.py` locally
2. Run `python scripts/validate-memory-security.py` if memory changed
3. Regenerate any stale generated files (see [CONTRIBUTING.md](../CONTRIBUTING.md))
4. Commit your changes

### Creating a Pull Request

1. Create a PR targeting `main`
2. CI/CD workflow will run automatically
3. All checks must pass
4. Address any failures and push updates
5. Once approved and green, merge

### Monitoring Workflow Status

- View results in **Actions** tab on GitHub
- Check individual job logs for detailed error messages
- Review job "Summary" for quick overview

## Copilot Integration

Path-specific Copilot instructions are available in:
- `.github/instructions/` — GitHub-specific guidance
- See [copilot-instructions.md](copilot-instructions.md) for entry point

[Back to AI OS](../README.md)
