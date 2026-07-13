"""Graph traversal operations for semantic discovery."""
from __future__ import annotations

from collections import deque

from . import DEFAULT_TRAVERSAL_DEPTH, MAX_TRAVERSAL_DEPTH


def _build_adjacency(edges: list[dict]) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Build outbound and inbound adjacency lists from graph edges.

    Returns (outbound, inbound) where each maps node_id -> list of edge dicts.
    """
    outbound: dict[str, list[dict]] = {}
    inbound: dict[str, list[dict]] = {}

    for edge in edges:
        source = edge.get("from", "")
        target = edge.get("to", "")
        edge_type = edge.get("type", "")
        if source:
            outbound.setdefault(source, []).append(edge)
        if target:
            inbound.setdefault(target, []).append(edge)

    # Sort for deterministic traversal
    for key in outbound:
        outbound[key].sort(key=lambda e: (e.get("type", ""), e.get("to", ""), e.get("id", "")))
    for key in inbound:
        inbound[key].sort(key=lambda e: (e.get("type", ""), e.get("from", ""), e.get("id", "")))

    return outbound, inbound


def direct_neighbors(node_id: str, edges: list[dict], *, relationship: str | None = None) -> list[dict]:
    """Find direct neighbors (both inbound and outbound) of a node.

    Returns list of neighbor info dicts with: nodeId, direction, relationship, edgeId.
    """
    outbound, inbound = _build_adjacency(edges)
    neighbors: list[dict] = []
    seen: set[str] = set()

    for edge in outbound.get(node_id, []):
        if relationship and edge.get("type") != relationship:
            continue
        target = edge.get("to", "")
        key = f"out:{target}:{edge.get('type', '')}"
        if key not in seen:
            seen.add(key)
            neighbors.append({
                "nodeId": target,
                "direction": "outbound",
                "relationship": edge.get("type", ""),
                "edgeId": edge.get("id", ""),
            })

    for edge in inbound.get(node_id, []):
        if relationship and edge.get("type") != relationship:
            continue
        source = edge.get("from", "")
        key = f"in:{source}:{edge.get('type', '')}"
        if key not in seen:
            seen.add(key)
            neighbors.append({
                "nodeId": source,
                "direction": "inbound",
                "relationship": edge.get("type", ""),
                "edgeId": edge.get("id", ""),
            })

    return neighbors


def breadth_first_traverse(node_id: str, edges: list[dict], *, depth: int = DEFAULT_TRAVERSAL_DEPTH, relationship: str | None = None) -> list[dict]:
    """Perform breadth-first traversal from a starting node.

    Returns list of traversal entries: nodeId, depth, path, relationship.
    Cycle protection: each node visited at most once.
    """
    effective_depth = min(depth, MAX_TRAVERSAL_DEPTH)
    outbound, inbound = _build_adjacency(edges)

    visited: set[str] = {node_id}
    queue: deque[tuple[str, int, list[str]]] = deque([(node_id, 0, [node_id])])
    results: list[dict] = []

    while queue:
        current, current_depth, path = queue.popleft()
        if current_depth >= effective_depth:
            continue

        # Explore outbound edges
        for edge in outbound.get(current, []):
            if relationship and edge.get("type") != relationship:
                continue
            target = edge.get("to", "")
            if target not in visited:
                visited.add(target)
                new_path = path + [target]
                results.append({
                    "nodeId": target,
                    "depth": current_depth + 1,
                    "path": new_path,
                    "relationship": edge.get("type", ""),
                    "direction": "outbound",
                })
                queue.append((target, current_depth + 1, new_path))

        # Explore inbound edges
        for edge in inbound.get(current, []):
            if relationship and edge.get("type") != relationship:
                continue
            source = edge.get("from", "")
            if source not in visited:
                visited.add(source)
                new_path = path + [source]
                results.append({
                    "nodeId": source,
                    "depth": current_depth + 1,
                    "path": new_path,
                    "relationship": edge.get("type", ""),
                    "direction": "inbound",
                })
                queue.append((source, current_depth + 1, new_path))

    return results


def find_shortest_path(source_id: str, target_id: str, edges: list[dict], *, max_depth: int = MAX_TRAVERSAL_DEPTH) -> list[str] | None:
    """Find the shortest relationship path between two nodes.

    Returns list of node IDs forming the path, or None if no path exists.
    Uses BFS for shortest path guarantee.
    """
    if source_id == target_id:
        return [source_id]

    outbound, inbound = _build_adjacency(edges)
    visited: set[str] = {source_id}
    queue: deque[tuple[str, list[str]]] = deque([(source_id, [source_id])])

    while queue:
        current, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue

        # Check outbound
        for edge in outbound.get(current, []):
            target = edge.get("to", "")
            if target == target_id:
                return path + [target]
            if target not in visited:
                visited.add(target)
                queue.append((target, path + [target]))

        # Check inbound
        for edge in inbound.get(current, []):
            source = edge.get("from", "")
            if source == target_id:
                return path + [source]
            if source not in visited:
                visited.add(source)
                queue.append((source, path + [source]))

    return None


def inbound_edges(node_id: str, edges: list[dict], *, relationship: str | None = None) -> list[dict]:
    """Get all inbound edges for a node."""
    _, inbound_map = _build_adjacency(edges)
    result = inbound_map.get(node_id, [])
    if relationship:
        result = [e for e in result if e.get("type") == relationship]
    return result


def outbound_edges(node_id: str, edges: list[dict], *, relationship: str | None = None) -> list[dict]:
    """Get all outbound edges for a node."""
    outbound_map, _ = _build_adjacency(edges)
    result = outbound_map.get(node_id, [])
    if relationship:
        result = [e for e in result if e.get("type") == relationship]
    return result
