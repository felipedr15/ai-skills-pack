from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import EDGE_TYPES, GENERATOR, NODE_TYPES, SCHEMA_VERSION
from .extract import (
    PLATFORMS,
    TOOLS,
    CONCEPTS,
    canonical_wiki_key,
    classify_document,
    discover_source_files,
    display_name_from_path,
    extract_explicit_skill_dependencies,
    extract_markdown_metadata,
    extract_memory_relationships,
    extract_mentions,
    markdown_links,
    project_name_from_path,
    read_json,
    resolve_markdown_target,
    wiki_links,
)
from .utils import edge_id, node_id, normalize_relpath, safe_source_path, slug


def _add_node(nodes: dict[str, dict], node: dict):
    node_id_value = node["id"]
    if node_id_value in nodes:
        return
    nodes[node_id_value] = node


def _add_edge(edges: dict[str, dict], edge_type: str, source: str, target: str, metadata: dict | None = None):
    if edge_type not in EDGE_TYPES:
        return
    meta = metadata or {}
    signature = "|".join(f"{key}:{meta[key]}" for key in sorted(meta))
    eid = edge_id(edge_type, source, target, signature)
    if eid in edges:
        return
    edges[eid] = {"id": eid, "type": edge_type, "from": source, "to": target, "metadata": meta}


def build_graph(root: Path):
    root = root.resolve()
    files = discover_source_files(root)
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    path_to_node: dict[str, str] = {}
    memory_id_to_node: dict[str, str] = {}
    skill_id_to_node: dict[str, str] = {}
    wiki_index: dict[str, str] = {}
    unresolved_refs: list[dict] = []

    # Pass 1: create core nodes from source files.
    for path in files:
        rel = normalize_relpath(path, root)
        category = classify_document(rel)
        if category == "project":
            name = project_name_from_path(rel)
            if name:
                pid = node_id("project", slug(name))
                _add_node(
                    nodes,
                    {
                        "id": pid,
                        "type": "project",
                        "name": name,
                        "sourcePath": f"templates/project-starters/{name}",
                        "metadata": {"origin": "starter"},
                    },
                )
                wiki_index[canonical_wiki_key(name)] = pid
                did = node_id("document", rel)
                _add_node(
                    nodes,
                    {
                        "id": did,
                        "type": "document",
                        "name": display_name_from_path(rel),
                        "sourcePath": rel,
                        "metadata": {"extension": path.suffix.lower()},
                    },
                )
                path_to_node[rel] = did
                wiki_index[canonical_wiki_key(display_name_from_path(rel))] = did
                _add_edge(edges, "contains", pid, did, {"reason": "starter_path"})
                continue

        if category == "skill":
            front, body = extract_markdown_metadata(path)
            skill_name = str(front.get("name") or display_name_from_path(rel))
            skill_slug = slug(str(front.get("id") or rel))
            sid = node_id("skill", skill_slug)
            _add_node(
                nodes,
                {
                    "id": sid,
                    "type": "skill",
                    "name": skill_name,
                    "sourcePath": rel,
                    "metadata": {
                        "skillId": front.get("id"),
                        "status": front.get("status"),
                        "version": front.get("version"),
                    },
                },
            )
            path_to_node[rel] = sid
            wiki_index[canonical_wiki_key(skill_name)] = sid
            if front.get("id"):
                skill_id_to_node[str(front.get("id"))] = sid
            mentions = body + "\n" + str(front.get("description", ""))
            for platform in extract_mentions(mentions, PLATFORMS):
                pid = node_id("platform", slug(platform))
                _add_node(nodes, {"id": pid, "type": "platform", "name": platform, "sourcePath": rel, "metadata": {"kind": "mention"}})
                _add_edge(edges, "uses", sid, pid, {"source": "skill_text"})
            for tool in extract_mentions(mentions, TOOLS):
                tid = node_id("tool", slug(tool))
                _add_node(nodes, {"id": tid, "type": "tool", "name": tool, "sourcePath": rel, "metadata": {"kind": "mention"}})
                _add_edge(edges, "uses", sid, tid, {"source": "skill_text"})
            for concept in extract_mentions(mentions, CONCEPTS):
                cid = node_id("concept", slug(concept))
                _add_node(nodes, {"id": cid, "type": "concept", "name": concept, "sourcePath": rel, "metadata": {"kind": "mention"}})
                _add_edge(edges, "supports", sid, cid, {"source": "skill_text"})
            for dep in extract_explicit_skill_dependencies(front):
                dep_id = dep.strip()
                if dep_id:
                    _add_edge(edges, "related_to", sid, node_id("skill", slug(dep_id)), {"source": "dependency"})
            continue

        if category == "memory":
            front, _body = extract_markdown_metadata(path)
            mid_value = str(front.get("id") or slug(rel))
            mid = node_id("memory", mid_value)
            _add_node(
                nodes,
                {
                    "id": mid,
                    "type": "memory",
                    "name": str(front.get("title") or display_name_from_path(rel)),
                    "sourcePath": rel,
                    "metadata": {
                        "memoryType": front.get("type"),
                        "scope": front.get("scope"),
                        "status": front.get("status"),
                    },
                },
            )
            path_to_node[rel] = mid
            memory_id_to_node[mid_value] = mid
            wiki_index[canonical_wiki_key(str(front.get("title") or mid_value))] = mid
            related, project_name = extract_memory_relationships(front)
            for value in related:
                _add_edge(edges, "related_to", mid, node_id("memory", value), {"source": "memory_related"})
            if project_name:
                pid = node_id("project", slug(project_name))
                _add_node(nodes, {"id": pid, "type": "project", "name": project_name, "sourcePath": "memory/registry.json", "metadata": {"origin": "memory_project"}})
                _add_edge(edges, "belongs_to", mid, pid, {"source": "memory_project"})
            continue

        # Fallback document node.
        did = node_id("document", rel)
        _add_node(
            nodes,
            {
                "id": did,
                "type": "document",
                "name": display_name_from_path(rel),
                "sourcePath": rel,
                "metadata": {"extension": path.suffix.lower()},
            },
        )
        path_to_node[rel] = did
        wiki_index[canonical_wiki_key(display_name_from_path(rel))] = did

    # Pass 1b: include referenced generated registries as supplemental docs if present.
    for rel in ["generated/skills.json", "generated/repository-index.json", "generated/memory-index.json"]:
        p = root / rel
        if p.is_file():
            did = node_id("document", rel)
            _add_node(nodes, {"id": did, "type": "document", "name": display_name_from_path(rel), "sourcePath": rel, "metadata": {"supplemental": True}})
            path_to_node.setdefault(rel, did)

    # Pass 2: relationships from links and text mentions.
    for path in files:
        rel = normalize_relpath(path, root)
        source = path_to_node.get(rel)
        if not source:
            continue
        if path.suffix.lower() == ".json":
            try:
                data = read_json(path)
            except Exception:  # noqa: BLE001
                continue
            if rel == "skills.json" and isinstance(data.get("skills"), list):
                for item in data.get("skills", []):
                    sid = skill_id_to_node.get(str(item.get("id")))
                    if sid:
                        _add_edge(edges, "generated_from", sid, source, {"source": "skills_registry"})
            continue

        front, body = extract_markdown_metadata(path)
        text = body

        for raw_target in markdown_links(text):
            resolved = resolve_markdown_target(path, raw_target, root)
            if not resolved:
                unresolved_refs.append({"source": rel, "target": raw_target, "kind": "markdown"})
                continue
            target = path_to_node.get(resolved)
            if target:
                _add_edge(edges, "references", source, target, {"kind": "markdown"})
            else:
                unresolved_refs.append({"source": rel, "target": resolved, "kind": "markdown"})

        for raw_target in wiki_links(text):
            key = canonical_wiki_key(raw_target)
            target = wiki_index.get(key)
            if target:
                _add_edge(edges, "references", source, target, {"kind": "wiki"})
            else:
                unresolved_refs.append({"source": rel, "target": raw_target, "kind": "wiki"})

        mentions = text + "\n" + str(front)
        for platform in extract_mentions(mentions, PLATFORMS):
            pid = node_id("platform", slug(platform))
            if pid in nodes:
                _add_edge(edges, "uses", source, pid, {"source": "document_text"})
        for tool in extract_mentions(mentions, TOOLS):
            tid = node_id("tool", slug(tool))
            if tid in nodes:
                _add_edge(edges, "uses", source, tid, {"source": "document_text"})
        for concept in extract_mentions(mentions, CONCEPTS):
            cid = node_id("concept", slug(concept))
            if cid in nodes:
                _add_edge(edges, "related_to", source, cid, {"source": "document_text"})

    # Resolve placeholder skill and memory IDs created from dependency/related references.
    node_keys = list(nodes.keys())
    for nid in node_keys:
        if nid.startswith("skill:") and nid not in skill_id_to_node.values() and nodes[nid].get("sourcePath") == None:
            pass

    # Remove edges to missing nodes and convert to unresolved warnings.
    valid_nodes = set(nodes)
    filtered_edges: list[dict] = []
    for edge in edges.values():
        if edge["from"] not in valid_nodes or edge["to"] not in valid_nodes:
            unresolved_refs.append({"source": edge["from"], "target": edge["to"], "kind": "dangling_edge"})
            continue
        filtered_edges.append(edge)

    node_list = sorted(nodes.values(), key=lambda item: item["id"])
    edge_list = sorted(filtered_edges, key=lambda item: (item["type"], item["from"], item["to"], item["id"]))

    node_counts = Counter(item["type"] for item in node_list)
    edge_counts = Counter(item["type"] for item in edge_list)

    graph = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "stats": {
            "nodes": len(node_list),
            "edges": len(edge_list),
            "nodesByType": dict(sorted(node_counts.items())),
            "edgesByType": dict(sorted(edge_counts.items())),
        },
        "nodes": node_list,
        "edges": edge_list,
        "unresolvedReferences": sorted(unresolved_refs, key=lambda item: (item.get("source", ""), item.get("target", ""), item.get("kind", ""))),
    }

    return graph


def validate_source_paths(graph: dict) -> list[str]:
    failures: list[str] = []
    for node in graph.get("nodes", []):
        path = node.get("sourcePath")
        if not isinstance(path, str) or not safe_source_path(path):
            failures.append(f"invalid sourcePath for node {node.get('id')}: {path}")
    return failures
