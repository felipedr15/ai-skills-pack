"""Rendering for discovery index artifacts and CLI output."""
from __future__ import annotations

import json


def render_json(index: dict) -> str:
    """Render discovery index as formatted JSON."""
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def render_markdown(index: dict) -> str:
    """Render discovery index as a Markdown summary."""
    stats = index.get("stats", {})
    diagnostics = index.get("diagnostics", {})

    lines = [
        "# Generated Discovery Index",
        "",
        "> Generated from repository source files and knowledge graph. This file is not a source of truth.",
        "",
        f"Generated at: {index.get('generatedAt', '')}",
        f"Source graph: {index.get('sourceGraph', '')}",
        "",
        "## Statistics",
        "",
        f"- Documents: {stats.get('documents', 0)}",
        f"- Entities: {stats.get('entities', 0)}",
        f"- Terms: {stats.get('terms', 0)}",
        f"- Relationships: {stats.get('relationships', 0)}",
        "",
        "## Diagnostics",
        "",
    ]

    warnings = diagnostics.get("warnings", [])
    if warnings:
        for w in warnings:
            lines.append(f"- WARNING: {w}")
    else:
        lines.append("- No warnings")

    unindexed = diagnostics.get("unindexedFiles", [])
    lines.extend(["", f"Unindexed files: {len(unindexed)}", ""])
    if unindexed:
        for path in unindexed[:20]:
            lines.append(f"- `{path}`")
        if len(unindexed) > 20:
            lines.append(f"- ... and {len(unindexed) - 20} more")
    else:
        lines.append("- None")

    lines.append("")
    return "\n".join(lines)


def render_search_results_text(results: list[dict], query: str) -> str:
    """Render search results as readable terminal text."""
    lines = [f"Search results for: \"{query}\"", f"Found: {len(results)} result(s)", ""]

    if not results:
        lines.append("No results found.")
        return "\n".join(lines)

    lines.append(f"{'#':<4} {'Score':<7} {'Type':<12} {'Name':<40} Source Path")
    lines.append("-" * 100)

    for i, result in enumerate(results, 1):
        name = result.get("name", "")[:39]
        lines.append(
            f"{i:<4} {result.get('score', 0):<7} "
            f"{result.get('type', ''):<12} {name:<40} "
            f"{result.get('sourcePath', '')}"
        )
        reasons = result.get("reasons", [])
        if reasons:
            lines.append(f"     Reasons: {'; '.join(reasons[:3])}")

    lines.append("")
    return "\n".join(lines)


def render_search_results_json(results: list[dict]) -> str:
    """Render search results as JSON."""
    return json.dumps(results, indent=2, ensure_ascii=False) + "\n"


def render_related_text(node_id: str, neighbors: list[dict], nodes_map: dict[str, dict]) -> str:
    """Render related nodes as readable terminal text."""
    lines = [f"Related nodes for: {node_id}", f"Found: {len(neighbors)} neighbor(s)", ""]

    if not neighbors:
        lines.append("No related nodes found.")
        return "\n".join(lines)

    lines.append(f"{'#':<4} {'Direction':<10} {'Relationship':<16} {'Node ID':<50} Name")
    lines.append("-" * 120)

    for i, neighbor in enumerate(neighbors, 1):
        nid = neighbor.get("nodeId", "")
        node = nodes_map.get(nid, {})
        name = node.get("name", "")[:30]
        lines.append(
            f"{i:<4} {neighbor.get('direction', ''):<10} "
            f"{neighbor.get('relationship', ''):<16} {nid:<50} {name}"
        )

    lines.append("")
    return "\n".join(lines)


def render_traverse_text(start_id: str, traversal: list[dict], nodes_map: dict[str, dict]) -> str:
    """Render traversal results as readable terminal text."""
    lines = [f"Traversal from: {start_id}", f"Visited: {len(traversal)} node(s)", ""]

    if not traversal:
        lines.append("No reachable nodes found.")
        return "\n".join(lines)

    lines.append(f"{'#':<4} {'Depth':<6} {'Relationship':<16} {'Direction':<10} {'Node ID':<50} Name")
    lines.append("-" * 130)

    for i, entry in enumerate(traversal, 1):
        nid = entry.get("nodeId", "")
        node = nodes_map.get(nid, {})
        name = node.get("name", "")[:30]
        lines.append(
            f"{i:<4} {entry.get('depth', 0):<6} "
            f"{entry.get('relationship', ''):<16} {entry.get('direction', ''):<10} "
            f"{nid:<50} {name}"
        )

    lines.append("")
    return "\n".join(lines)


def render_path_text(path: list[str] | None, nodes_map: dict[str, dict]) -> str:
    """Render a relationship path as readable terminal text."""
    if path is None:
        return "No path found between the specified nodes.\n"

    lines = [f"Path found ({len(path)} nodes):", ""]
    for i, node_id in enumerate(path):
        node = nodes_map.get(node_id, {})
        name = node.get("name", "")
        connector = " -> " if i < len(path) - 1 else ""
        lines.append(f"  [{i + 1}] {node_id} ({name}){connector}")

    lines.append("")
    return "\n".join(lines)


def render_explain_text(node_id: str, query: str, result: dict, neighbors: list[dict], nodes_map: dict[str, dict]) -> str:
    """Render an explanation for why a node matches a query."""
    lines = [f"Explanation for: {node_id}", f"Query: \"{query}\"", ""]

    node = nodes_map.get(node_id, {})
    if node:
        lines.append(f"Node type: {node.get('type', 'unknown')}")
        lines.append(f"Node name: {node.get('name', '')}")
        lines.append(f"Source path: {node.get('sourcePath', '')}")
        lines.append("")

    score = result.get("score", 0)
    lines.append(f"Score: {score}")
    lines.append("")

    matched_fields = result.get("matchedFields", [])
    if matched_fields:
        lines.append("Matched fields:")
        for field in matched_fields:
            lines.append(f"  - {field}")
        lines.append("")

    reasons = result.get("reasons", [])
    if reasons:
        lines.append("Scoring reasons:")
        for reason in reasons:
            lines.append(f"  - {reason}")
        lines.append("")

    if neighbors:
        lines.append(f"Graph neighbors: {len(neighbors)}")
        for n in neighbors[:5]:
            nid = n.get("nodeId", "")
            nnode = nodes_map.get(nid, {})
            lines.append(f"  - {n.get('direction', '')} {n.get('relationship', '')}: {nnode.get('name', nid)}")
        if len(neighbors) > 5:
            lines.append(f"  ... and {len(neighbors) - 5} more")
        lines.append("")

    if score == 0 and not matched_fields:
        lines.append("This node did not match the query directly.")
        lines.append("")

    return "\n".join(lines)


def render_stats_text(index: dict) -> str:
    """Render discovery index statistics."""
    stats = index.get("stats", {})
    diagnostics = index.get("diagnostics", {})

    lines = [
        "Discovery Index Statistics",
        "=" * 40,
        "",
        f"Schema version: {index.get('schemaVersion', '')}",
        f"Generator: {index.get('generator', '')}",
        f"Source graph: {index.get('sourceGraph', '')}",
        f"Generated at: {index.get('generatedAt', '')}",
        "",
        "Counts:",
        f"  Documents: {stats.get('documents', 0)}",
        f"  Entities: {stats.get('entities', 0)}",
        f"  Terms: {stats.get('terms', 0)}",
        f"  Relationships: {stats.get('relationships', 0)}",
        "",
    ]

    warnings = diagnostics.get("warnings", [])
    unindexed = diagnostics.get("unindexedFiles", [])
    lines.append(f"Warnings: {len(warnings)}")
    for w in warnings:
        lines.append(f"  - {w}")
    lines.append(f"Unindexed files: {len(unindexed)}")
    lines.append("")

    return "\n".join(lines)
