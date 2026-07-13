"""Pagination utilities for the AI OS service layer."""
from __future__ import annotations

from . import DEFAULT_LIMIT, MAX_LIMIT


def clamp_limit(limit: int | None) -> int:
    """Clamp a limit value to valid range."""
    if limit is None or limit <= 0:
        return DEFAULT_LIMIT
    return min(limit, MAX_LIMIT)


def paginate(items: list, limit: int, cursor: int = 0) -> dict:
    """Apply pagination to a list of items.

    Returns dict with items, total, limit, cursor, hasMore.
    """
    effective_limit = clamp_limit(limit)
    start = max(0, cursor)
    end = start + effective_limit
    page = items[start:end]
    return {
        "items": page,
        "total": len(items),
        "limit": effective_limit,
        "cursor": start,
        "nextCursor": end if end < len(items) else None,
        "hasMore": end < len(items),
    }
