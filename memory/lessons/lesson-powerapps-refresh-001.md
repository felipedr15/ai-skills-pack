---
id: lesson-powerapps-refresh-001
title: Refresh data before rebuilding collections
type: lesson
scope: global
project: null
status: active
created: 2026-07-12
updated: 2026-07-12
source: MWS Schedule App troubleshooting
summary: Refresh the source before rebuilding dependent collections.
tags:
  - power-apps
  - sharepoint
  - refresh
related: []
sensitivity: internal
retention: permanent
contentPath: memory/lessons/lesson-powerapps-refresh-001.md
---

# Refresh data before rebuilding collections

## Summary

Refresh the source dataset first, then rebuild dependent collections.

## Situation

A troubleshooting flow rebuilt local collections while source data remained stale.

## Observation

Dependent collections reflected stale results after rebuild.

## Root Cause

Rebuild order ran before a source refresh completed.

## Resolution

Refresh source data first and wait for completion before rebuilding.

## Reusable Lesson

Validate source freshness before any dependent rehydration.

## Preventive Action

Add explicit refresh checks in troubleshooting and implementation runbooks.

## Why It Matters

This reduces false debugging trails and repeated rework.

## Related Projects

- MWS Schedule App

## Related Decisions

- None

## Evidence or Source

Observed repeatedly in troubleshooting sessions.

## Review Date

2027-01-12
