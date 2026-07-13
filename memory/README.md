# Memory Engine

The AI OS Memory Engine stores explicit, local, repository-based memory records in Markdown and JSON.

## Purpose

Provide durable and temporary memory layers for conventions, project context, sessions, decisions, lessons, and archived records.

## Source of truth

Source Markdown files under `memory/` and `memory/registry.json` are the source of truth.
Generated indexes under `generated/` are deterministic views and are never authoritative.

## What this is not

- Not a vector database.
- Not a cloud memory service.
- Not automatic access to ChatGPT, Claude, Copilot, or Kiro histories.
- Not an autonomous personal-memory system.

## Folders

- `permanent/`: long-lived conventions, preferences, principles.
- `projects/`: project-specific durable context.
- `sessions/`: temporary working memory that should be cleaned up or promoted.
- `decisions/`: ADR-style records.
- `lessons/`: reusable lessons learned.
- `archive/`: archived records retained for traceability.

## Naming convention

Use stable lowercase IDs in file names: `<type>-<topic>-NNN.md`.

## Retention guidance

- Permanent records stay active until superseded.
- Project records stay with project lifecycle.
- Session records are temporary.
- Archived records are retained for auditability.

## Security restrictions

Do not store secrets, production credentials, personal data, or confidential exports.
Use placeholders in examples.

## Commands

```text
python scripts/memory-add.py --type lesson --title "Example" --scope global --summary "..."
python scripts/memory-list.py --type lesson
python scripts/memory-search.py "keyword"
python scripts/memory-archive.py --id lesson-example-001
python scripts/memory-promote.py --id session-example-001 --target-type lesson --reason "Reusable finding"
python scripts/generate-memory-index.py
python scripts/generate-memory-index.py --check
python scripts/validate-memory-security.py
```

[Back to AI OS](../README.md)
