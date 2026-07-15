# Phase 7 Release Hardening Architecture

## Purpose

Document the release hardening, unified CLI, and one-command bootstrap introduced in Phase 7.

## Version

Single source of truth: `VERSION` file at repository root. Semantic versioning. Current: `0.8.0`.

## Unified CLI

Entry point: `python scripts/ai-os.py <command>`

Commands: version, status, doctor, bootstrap, validate, test, build, generate, start-dashboard, start-mcp, smoke-test, release-check, package, backup, restore, clean-generated, migrate, help.

## One-Command Bootstrap

```text
python scripts/ai-os.py bootstrap
python scripts/ai-os.py bootstrap --check
python scripts/ai-os.py bootstrap --force-regenerate
```

Idempotent. Generates missing artifacts in dependency order. Does not modify source files or perform Git operations.

## Environment Doctor

```text
python scripts/ai-os.py doctor
python scripts/ai-os.py doctor --json
```

Non-destructive. Checks Python version, OS, Git, config, artifacts, ports, and readiness.

## Configuration

- Committed example: `config/ai-os.example.json`
- Local (ignored): `config/ai-os.local.json`
- Schema validated
- Localhost-only dashboard by default
- MCP read-only by default
- No secrets stored

## Build Orchestration

Dependency order: skill registry -> memory index -> repository index -> knowledge graph -> discovery index -> dashboard.

## Packaging

```text
python scripts/ai-os.py package
python scripts/ai-os.py package --dry-run
```

Produces zip, tar.gz, checksums, and file list in `dist/`. Excludes .git, .venv, secrets, local config.

## Backup and Restore

```text
python scripts/ai-os.py backup
python scripts/ai-os.py restore <path> --force
```

Backs up generated/ and local config. Path traversal protection on restore.

## Security

- No arbitrary shell execution
- No Git operations from CLI
- No network calls
- No telemetry
- Repository-root confinement
- Allowlisted clean targets only
- Symlink escape rejection in packaging
- Restore requires --force
- No secrets in packages

## Cross-Platform Wrappers

- `bootstrap.ps1` (Windows PowerShell)
- `bootstrap.sh` (macOS/Linux bash)

Thin wrappers calling Python implementation.

[Back to architecture knowledge](README.md)
