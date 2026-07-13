---
id: decision-memory-index-source-truth-001
title: Generated memory indexes are derived views, not source of truth
type: decision
scope: project
project: ai-os
status: active
created: 2026-07-12
updated: 2026-07-12
source: AI OS Phase 2 implementation
summary: Source Markdown and registry records remain authoritative; generated indexes are deterministic outputs.
tags:
  - memory
  - indexing
  - governance
related:
  - convention-documentation-structure-001
sensitivity: internal
retention: project
contentPath: memory/decisions/decision-memory-index-source-truth-001.md
---

# Generated memory indexes are derived views, not source of truth

## Summary

Indexes help discovery and validation but cannot replace source records.

## Context

The Memory Engine introduces generated index files for searchability and checks.

## Decision

Treat Markdown source records and `memory/registry.json` as authoritative content.

## Reason

Generated files can be regenerated and should never be manually edited as primary data.

## Alternatives Considered

Using generated files as primary data was rejected because it risks drift and accidental data loss.

## Consequences

Validation must verify generated index freshness and preserve source records.

## Why It Matters

This keeps repository memory explicit, auditable, and local.

## Related Projects

- AI OS

## Related Decisions

- convention-documentation-structure-001

## Evidence or Source

AI OS governance and architecture constraints for deterministic generated artifacts.

## Review Date

2027-01-12
