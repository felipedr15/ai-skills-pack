from __future__ import annotations

import json


def render_json(graph: dict) -> str:
    return json.dumps(graph, indent=2, ensure_ascii=False) + "\n"


def render_markdown(graph: dict) -> str:
    stats = graph.get("stats", {})
    unresolved = graph.get("unresolvedReferences", [])
    nodes_by_type = stats.get("nodesByType", {})
    edges_by_type = stats.get("edgesByType", {})

    lines = [
        "# Generated Knowledge Graph",
        "",
        "> Generated from repository source files. This file is not a source of truth.",
        "",
        f"Generated at: {graph.get('generatedAt', '')}",
        "",
        f"Nodes: {stats.get('nodes', 0)}",
        f"Edges: {stats.get('edges', 0)}",
        "",
        "## Node Counts By Type",
        "",
    ]
    for key, value in sorted(nodes_by_type.items()):
        lines.append(f"- {key}: {value}")
    if not nodes_by_type:
        lines.append("- none")

    lines.extend(["", "## Edge Counts By Type", ""])
    for key, value in sorted(edges_by_type.items()):
        lines.append(f"- {key}: {value}")
    if not edges_by_type:
        lines.append("- none")

    lines.extend(["", "## Unresolved References", "", f"Count: {len(unresolved)}", ""])
    for item in unresolved[:25]:
        lines.append(f"- {item.get('kind')}: {item.get('source')} -> {item.get('target')}")
    if len(unresolved) > 25:
        lines.append(f"- ... and {len(unresolved) - 25} more")
    if not unresolved:
        lines.append("- none")

    lines.extend(["", "## Relationship Overview", ""])
    top = sorted(edges_by_type.items(), key=lambda pair: (-pair[1], pair[0]))[:10]
    for edge_type, count in top:
        lines.append(f"- {edge_type}: {count}")
    if not top:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)
