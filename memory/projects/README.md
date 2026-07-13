# Project Memory

Purpose: store project-specific durable context that should outlive one session.

What belongs here:

- project requirements context snapshots
- project implementation notes that remain relevant
- cross-session project references

What must not be stored:

- secrets or confidential production data
- one-off scratch notes with no future value

Naming convention: `project-<topic>-NNN.md` or other valid memory IDs.

Retention: project lifecycle, then archive when no longer active.

[Back to Memory Engine](../README.md)
