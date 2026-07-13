"""CLI command implementations for semantic discovery."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import DEFAULT_RESULT_LIMIT, DEFAULT_TRAVERSAL_DEPTH, MAX_TRAVERSAL_DEPTH
from .index import load_knowledge_graph
from .query import tokenize_query
from .rank import rank_results, score_document, score_entity
from .render import (
    render_explain_text,
    render_path_text,
    render_related_text,
    render_search_results_json,
    render_search_results_text,
    render_stats_text,
    render_traverse_text,
)
from .traverse import breadth_first_traverse, direct_neighbors, find_shortest_path
from .validate import DiscoveryError, load_discovery_index


def _load_index_and_graph(root: Path) -> tuple[dict, dict]:
    """Load discovery index and knowledge graph."""
    index_path = root / "generated" / "discovery-index.json"
    if not index_path.is_file():
        print("FAIL discovery index not found. Run: python scripts/discovery-build.py", file=sys.stderr)
        raise SystemExit(1)
    try:
        index = load_discovery_index(index_path)
    except DiscoveryError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
    graph = load_knowledge_graph(root)
    return index, graph


def _nodes_map(graph: dict) -> dict[str, dict]:
    """Build node ID -> node dict mapping."""
    return {node["id"]: node for node in graph.get("nodes", [])}


def cmd_search(root: Path, query: str, *, type_filter: str | None = None, path_filter: str | None = None, relationship_filter: str | None = None, limit: int = DEFAULT_RESULT_LIMIT, output_json: bool = False, include_isolated: bool = False, case_sensitive: bool = False, exact: bool = False) -> int:
    """Execute a search command."""
    if not query.strip():
        print("FAIL search query cannot be empty", file=sys.stderr)
        return 1

    index, graph = _load_index_and_graph(root)
    query_tokens = tokenize_query(query)
    edges = graph.get("edges", [])

    # Determine neighbors of any node matching the query (for relationship boost)
    nodes_map_data = _nodes_map(graph)
    neighbor_node_ids: set[str] = set()
    if relationship_filter:
        for node in graph.get("nodes", []):
            if query.lower() in node.get("name", "").lower():
                for n in direct_neighbors(node["id"], edges, relationship=relationship_filter):
                    neighbor_node_ids.add(n["nodeId"])

    results: list[dict] = []

    # Score documents
    for doc in index.get("documents", []):
        score, matched_fields, reasons = score_document(
            doc, query, query_tokens,
            type_filter=type_filter,
            path_filter=path_filter,
        )
        if score > 0:
            results.append({
                "id": doc["id"],
                "type": doc.get("category", "document"),
                "name": doc.get("title", ""),
                "sourcePath": doc.get("sourcePath", ""),
                "score": score,
                "matchedFields": matched_fields,
                "reasons": reasons,
                "relationships": [],
            })

    # Score entities
    for entity in index.get("entities", []):
        score, matched_fields, reasons = score_entity(
            entity, query, query_tokens,
            type_filter=type_filter,
            path_filter=path_filter,
            relationship_filter=relationship_filter,
            neighbors=neighbor_node_ids,
        )
        if score > 0:
            # Get relationships for this entity
            node_id = entity.get("nodeId", "")
            entity_neighbors = direct_neighbors(node_id, edges)
            relationships = [
                {"nodeId": n["nodeId"], "relationship": n["relationship"], "direction": n["direction"]}
                for n in entity_neighbors[:5]
            ]
            results.append({
                "id": entity["id"],
                "type": entity.get("type", ""),
                "name": entity.get("name", ""),
                "sourcePath": entity.get("sourcePath", ""),
                "score": score,
                "matchedFields": matched_fields,
                "reasons": reasons,
                "relationships": relationships,
            })

    # Filter isolated entities if requested
    if not include_isolated:
        edges_set = set()
        for edge in edges:
            edges_set.add(edge.get("from", ""))
            edges_set.add(edge.get("to", ""))
        # Only filter entity results, not document results
        results = [
            r for r in results
            if not r["id"].startswith("entity:") or r["id"].replace("entity:", "") in edges_set or r["id"].replace("entity:", "").split(":", 1)[-1] in {e.get("from", "").split(":", 1)[-1] for e in edges} or r.get("score", 0) > 30
        ]

    results = rank_results(results)
    if limit > 0:
        results = results[:limit]

    if output_json:
        print(render_search_results_json(results), end="")
    else:
        print(render_search_results_text(results, query), end="")

    return 0


def cmd_related(root: Path, node_id: str, *, relationship: str | None = None, output_json: bool = False) -> int:
    """Execute a related command."""
    _, graph = _load_index_and_graph(root)
    edges = graph.get("edges", [])
    nodes_map_data = _nodes_map(graph)

    # Check if node exists
    if node_id not in nodes_map_data:
        print(f"FAIL node not found: {node_id}", file=sys.stderr)
        return 1

    neighbors = direct_neighbors(node_id, edges, relationship=relationship)

    if output_json:
        output = []
        for n in neighbors:
            node = nodes_map_data.get(n["nodeId"], {})
            output.append({
                "nodeId": n["nodeId"],
                "direction": n["direction"],
                "relationship": n["relationship"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "sourcePath": node.get("sourcePath", ""),
            })
        print(json.dumps(output, indent=2, ensure_ascii=False) + "\n", end="")
    else:
        print(render_related_text(node_id, neighbors, nodes_map_data), end="")

    return 0


def cmd_traverse(root: Path, node_id: str, *, depth: int = DEFAULT_TRAVERSAL_DEPTH, relationship: str | None = None, output_json: bool = False) -> int:
    """Execute a traverse command."""
    _, graph = _load_index_and_graph(root)
    edges = graph.get("edges", [])
    nodes_map_data = _nodes_map(graph)

    if node_id not in nodes_map_data:
        print(f"FAIL node not found: {node_id}", file=sys.stderr)
        return 1

    effective_depth = min(depth, MAX_TRAVERSAL_DEPTH)
    traversal = breadth_first_traverse(node_id, edges, depth=effective_depth, relationship=relationship)

    if output_json:
        output = []
        for entry in traversal:
            node = nodes_map_data.get(entry["nodeId"], {})
            output.append({
                "nodeId": entry["nodeId"],
                "depth": entry["depth"],
                "path": entry["path"],
                "relationship": entry["relationship"],
                "direction": entry["direction"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
            })
        print(json.dumps(output, indent=2, ensure_ascii=False) + "\n", end="")
    else:
        print(render_traverse_text(node_id, traversal, nodes_map_data), end="")

    return 0


def cmd_path(root: Path, source_id: str, target_id: str, *, output_json: bool = False) -> int:
    """Execute a path command."""
    _, graph = _load_index_and_graph(root)
    edges = graph.get("edges", [])
    nodes_map_data = _nodes_map(graph)

    if source_id not in nodes_map_data:
        print(f"FAIL source node not found: {source_id}", file=sys.stderr)
        return 1
    if target_id not in nodes_map_data:
        print(f"FAIL target node not found: {target_id}", file=sys.stderr)
        return 1

    path = find_shortest_path(source_id, target_id, edges)

    if output_json:
        if path is None:
            output = {"found": False, "path": []}
        else:
            output = {
                "found": True,
                "path": [
                    {"nodeId": nid, "name": nodes_map_data.get(nid, {}).get("name", ""), "type": nodes_map_data.get(nid, {}).get("type", "")}
                    for nid in path
                ],
            }
        print(json.dumps(output, indent=2, ensure_ascii=False) + "\n", end="")
    else:
        print(render_path_text(path, nodes_map_data), end="")

    return 0


def cmd_explain(root: Path, node_id: str, query: str, *, output_json: bool = False) -> int:
    """Execute an explain command."""
    index, graph = _load_index_and_graph(root)
    edges = graph.get("edges", [])
    nodes_map_data = _nodes_map(graph)

    if node_id not in nodes_map_data:
        print(f"FAIL node not found: {node_id}", file=sys.stderr)
        return 1

    query_tokens = tokenize_query(query)

    # Try scoring as entity
    entity_entry = None
    for entity in index.get("entities", []):
        if entity.get("nodeId") == node_id:
            entity_entry = entity
            break

    if entity_entry:
        score, matched_fields, reasons = score_entity(entity_entry, query, query_tokens)
    else:
        score, matched_fields, reasons = 0, [], []

    # Also try as document
    doc_entry = None
    node_data = nodes_map_data.get(node_id, {})
    node_source = node_data.get("sourcePath", "")
    for doc in index.get("documents", []):
        if doc.get("sourcePath") == node_source:
            doc_entry = doc
            break

    if doc_entry:
        doc_score, doc_fields, doc_reasons = score_document(doc_entry, query, query_tokens)
        if doc_score > score:
            score = doc_score
            matched_fields = doc_fields
            reasons = doc_reasons

    result = {
        "score": score,
        "matchedFields": matched_fields,
        "reasons": reasons,
    }

    neighbors = direct_neighbors(node_id, edges)

    if output_json:
        output = {
            "nodeId": node_id,
            "query": query,
            "node": nodes_map_data.get(node_id, {}),
            "score": score,
            "matchedFields": matched_fields,
            "reasons": reasons,
            "neighbors": len(neighbors),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False) + "\n", end="")
    else:
        print(render_explain_text(node_id, query, result, neighbors, nodes_map_data), end="")

    return 0


def cmd_stats(root: Path, *, output_json: bool = False) -> int:
    """Execute a stats command."""
    index, _ = _load_index_and_graph(root)

    if output_json:
        output = {
            "schemaVersion": index.get("schemaVersion", ""),
            "generator": index.get("generator", ""),
            "sourceGraph": index.get("sourceGraph", ""),
            "generatedAt": index.get("generatedAt", ""),
            "stats": index.get("stats", {}),
            "diagnostics": index.get("diagnostics", {}),
        }
        print(json.dumps(output, indent=2, ensure_ascii=False) + "\n", end="")
    else:
        print(render_stats_text(index), end="")

    return 0
