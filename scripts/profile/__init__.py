"""Professional profile and expertise modules (Phase 9).

This package holds canonical, explicitly-authored professional context
(role, team, responsibilities, reporting relationships) and an
evidence-based expertise profile. It is structurally parallel to
`memory/` but never stored inside it: `memory/` is reserved for
approval-gated *learned* records, while `profile/` holds authored
identity data that the system never infers or guesses on the user's
behalf.

Like `scripts/orchestration/`, this package performs no Git operations,
arbitrary shell execution, network access, or automatic writes to
source-of-truth documents. Nothing here fabricates profile content —
an empty `profile/` (no profile record yet) is a valid, expected state.
"""
from __future__ import annotations

SCHEMA_VERSION = "1.0.0"
