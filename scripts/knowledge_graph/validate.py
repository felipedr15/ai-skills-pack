from __future__ import annotations

import json
from pathlib import Path

from . import EDGE_TYPES, NODE_TYPES, SCHEMA_VERSION
from .utils import safe_source_path


class KnowledgeGraphError(ValueError):
    pass


def _required_fields(item: dict, required: set[str]) -> list[str]:
    return sorted(required - set(item))


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_graph_object(graph: object) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []

    if not isinstance(graph, dict):
        failures.append("graph root must be an object")
        return failures, warnings

    if graph.get("schemaVersion") != SCHEMA_VERSION:
        failures.append("schemaVersion is missing or unsupported")

    if not _is_nonempty_string(graph.get("generatedAt")):
        failures.append("generatedAt must be a nonempty string")

    if not _is_nonempty_string(graph.get("generator")):
        failures.append("generator must be a nonempty string")

    stats = graph.get("stats")
    stats_nodes: int | None = None
    stats_edges: int | None = None
    if not isinstance(stats, dict):
        failures.append("stats must be an object")
    else:
        stats_nodes_value = stats.get("nodes")
        stats_edges_value = stats.get("edges")
        if not isinstance(stats_nodes_value, int):
            failures.append("stats.nodes must be an integer")
        else:
            stats_nodes = stats_nodes_value
        if not isinstance(stats_edges_value, int):
            failures.append("stats.edges must be an integer")
        else:
            stats_edges = stats_edges_value

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list):
        failures.append("nodes must be a list")
        nodes = []
    if not isinstance(edges, list):
        failures.append("edges must be a list")
        edges = []

    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            failures.append("node entry is not an object")
            continue
        missing = _required_fields(node, {"id", "type", "name", "sourcePath", "metadata"})
        if missing:
            failures.append(f"node missing required properties: {missing}")
            continue

        node_id = node["id"]
        if not _is_nonempty_string(node_id):
            failures.append("node id must be a nonempty string")
            continue
        if node_id in node_ids:
            failures.append(f"duplicate node id: {node_id}")
        node_ids.add(node_id)

        if node.get("type") not in NODE_TYPES:
            failures.append(f"unsupported node type: {node.get('type')}")

        node_name = node.get("name")
        if not _is_nonempty_string(node_name):
            failures.append(f"node name must be a nonempty string: {node_id}")

        node_metadata = node.get("metadata")
        if not isinstance(node_metadata, dict):
            failures.append(f"node metadata must be an object: {node_id}")

        source_path = node.get("sourcePath")
        if not isinstance(source_path, str) or not safe_source_path(source_path):
            failures.append(f"invalid sourcePath: {source_path}")
        else:
            if source_path.startswith("/"):
                failures.append(f"absolute sourcePath is not allowed: {source_path}")
            if ".." in Path(source_path).parts:
                failures.append(f"sourcePath escapes repository: {source_path}")

    edge_ids: set[str] = set()
    referenced_nodes: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            failures.append("edge entry is not an object")
            continue
        missing = _required_fields(edge, {"id", "type", "from", "to", "metadata"})
        if missing:
            failures.append(f"edge missing required properties: {missing}")
            continue

        edge_id = edge["id"]
        if not _is_nonempty_string(edge_id):
            failures.append("edge id must be a nonempty string")
            continue
        if edge_id in edge_ids:
            failures.append(f"duplicate edge id: {edge_id}")
        edge_ids.add(edge_id)

        if edge.get("type") not in EDGE_TYPES:
            failures.append(f"unsupported edge type: {edge.get('type')}")

        edge_from = edge.get("from")
        edge_to = edge.get("to")
        if not _is_nonempty_string(edge_from):
            failures.append(f"edge from must be a nonempty string: {edge_id}")
            edge_from = None
        if not _is_nonempty_string(edge_to):
            failures.append(f"edge to must be a nonempty string: {edge_id}")
            edge_to = None

        edge_metadata = edge.get("metadata")
        if not isinstance(edge_metadata, dict):
            failures.append(f"edge metadata must be an object: {edge_id}")

        if edge_from is not None and edge_to is not None and (edge_from not in node_ids or edge_to not in node_ids):
            failures.append(f"edge references nonexistent node: {edge_id}")
        if edge_from is not None:
            referenced_nodes.add(edge_from)
        if edge_to is not None:
            referenced_nodes.add(edge_to)

    if stats_nodes is not None and stats_nodes != len(nodes):
        failures.append("stats.nodes does not match nodes length")
    if stats_edges is not None and stats_edges != len(edges):
        failures.append("stats.edges does not match edges length")

    unresolved = graph.get("unresolvedReferences", [])
    if unresolved:
        warnings.append(f"unresolved references: {len(unresolved)}")

    isolated = [node_id for node_id in node_ids if node_id not in referenced_nodes]
    if isolated:
        warnings.append(f"isolated nodes: {len(isolated)}")

    return failures, warnings


def load_graph(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise KnowledgeGraphError(f"unable to read graph file: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise KnowledgeGraphError(f"unable to read graph file: {path}: {exc}") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise KnowledgeGraphError(f"invalid JSON: {exc}") from exc


def compare_graphs_ignoring_generated_at(current: dict, saved: dict) -> bool:
    left = dict(current)
    right = dict(saved)
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    return left == right
