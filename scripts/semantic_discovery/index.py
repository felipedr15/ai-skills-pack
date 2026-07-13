"""Discovery index construction from source files and knowledge graph."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from . import GENERATOR, SCHEMA_VERSION, SOURCE_GRAPH
from .extract import discover_source_files, extract_file_metadata
from .utils import is_secret_like_path, normalize_path, safe_source_path, stable_doc_id, stable_entity_id


def _tokenize_for_index(text: str) -> list[str]:
    """Tokenize text for indexing (lowercase, split on boundaries)."""
    from .query import tokenize
    return tokenize(text)


def _build_documents(root: Path) -> list[dict]:
    """Build document entries from source files."""
    files = discover_source_files(root)
    documents: list[dict] = []
    seen_ids: set[str] = set()

    for path in files:
        rel = normalize_path(str(path.relative_to(root)))
        if is_secret_like_path(rel):
            continue
        doc_id = stable_doc_id(rel)
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)

        meta = extract_file_metadata(path, root)

        documents.append({
            "id": doc_id,
            "sourcePath": rel,
            "title": meta.get("title", "") or path.stem,
            "category": meta.get("category", "document"),
            "headings": meta.get("headings", []),
            "snippet": meta.get("snippet", ""),
            "frontMatter": {
                key: value for key, value in (meta.get("frontMatter") or {}).items()
                if isinstance(value, (str, int, float, bool, type(None)))
                   or (isinstance(value, list) and all(isinstance(v, str) for v in value))
            },
        })

    documents.sort(key=lambda item: item["id"])
    return documents


def _build_entities(graph: dict) -> list[dict]:
    """Build entity entries from knowledge graph nodes."""
    entities: list[dict] = []
    seen_ids: set[str] = set()

    for node in graph.get("nodes", []):
        node_id = node.get("id", "")
        entity_id = stable_entity_id(node_id)
        if entity_id in seen_ids:
            continue
        seen_ids.add(entity_id)

        entities.append({
            "id": entity_id,
            "nodeId": node_id,
            "type": node.get("type", ""),
            "name": node.get("name", ""),
            "sourcePath": node.get("sourcePath", ""),
            "metadata": node.get("metadata", {}),
        })

    entities.sort(key=lambda item: item["id"])
    return entities


def _build_term_index(documents: list[dict], entities: list[dict]) -> dict[str, list[str]]:
    """Build an inverted term index mapping tokens to document/entity IDs."""
    term_index: dict[str, set[str]] = {}

    for doc in documents:
        doc_id = doc["id"]
        # Tokenize title
        for token in _tokenize_for_index(doc.get("title", "")):
            term_index.setdefault(token, set()).add(doc_id)
        # Tokenize headings
        for heading in doc.get("headings", []):
            for token in _tokenize_for_index(heading):
                term_index.setdefault(token, set()).add(doc_id)
        # Tokenize snippet
        for token in _tokenize_for_index(doc.get("snippet", "")):
            term_index.setdefault(token, set()).add(doc_id)
        # Tokenize path segments
        for token in _tokenize_for_index(doc.get("sourcePath", "").replace("/", " ").replace("-", " ").replace("_", " ")):
            term_index.setdefault(token, set()).add(doc_id)
        # Tokenize selected front matter values
        fm = doc.get("frontMatter", {})
        for key in ("name", "description", "title", "summary", "id"):
            value = fm.get(key)
            if isinstance(value, str):
                for token in _tokenize_for_index(value):
                    term_index.setdefault(token, set()).add(doc_id)
        tags = fm.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    for token in _tokenize_for_index(tag):
                        term_index.setdefault(token, set()).add(doc_id)

    for entity in entities:
        entity_id = entity["id"]
        # Tokenize entity name
        for token in _tokenize_for_index(entity.get("name", "")):
            term_index.setdefault(token, set()).add(entity_id)
        # Tokenize entity type
        for token in _tokenize_for_index(entity.get("type", "")):
            term_index.setdefault(token, set()).add(entity_id)
        # Tokenize entity source path
        for token in _tokenize_for_index(entity.get("sourcePath", "").replace("/", " ").replace("-", " ").replace("_", " ")):
            term_index.setdefault(token, set()).add(entity_id)
        # Tokenize metadata values
        meta = entity.get("metadata", {})
        for key, value in meta.items():
            if isinstance(value, str) and value:
                for token in _tokenize_for_index(value):
                    term_index.setdefault(token, set()).add(entity_id)

    # Convert sets to sorted lists for determinism
    sorted_index: dict[str, list[str]] = {}
    for term in sorted(term_index.keys()):
        sorted_index[term] = sorted(term_index[term])

    return sorted_index


def _compute_stats(documents: list[dict], entities: list[dict], term_index: dict, graph: dict) -> dict:
    """Compute index statistics."""
    return {
        "documents": len(documents),
        "entities": len(entities),
        "terms": len(term_index),
        "relationships": len(graph.get("edges", [])),
    }


def _compute_diagnostics(documents: list[dict], entities: list[dict], term_index: dict, root: Path) -> dict:
    """Compute diagnostic information."""
    warnings: list[str] = []

    # Find entities with no terms
    indexed_ids = set()
    for refs in term_index.values():
        indexed_ids.update(refs)

    no_terms = [entity["id"] for entity in entities if entity["id"] not in indexed_ids]
    if no_terms:
        warnings.append(f"entities with no searchable terms: {len(no_terms)}")

    # Find unindexed files
    indexed_paths = {doc["sourcePath"] for doc in documents}
    unindexed: list[str] = []
    all_source_files = discover_source_files(root)
    for path in all_source_files:
        rel = normalize_path(str(path.relative_to(root)))
        if rel not in indexed_paths:
            unindexed.append(rel)

    return {
        "warnings": warnings,
        "unindexedFiles": sorted(unindexed),
    }


def load_knowledge_graph(root: Path) -> dict:
    """Load the generated knowledge graph."""
    graph_path = root / SOURCE_GRAPH
    if not graph_path.is_file():
        return {"nodes": [], "edges": [], "stats": {}}
    try:
        text = graph_path.read_text(encoding="utf-8")
        return json.loads(text)
    except (OSError, json.JSONDecodeError):
        return {"nodes": [], "edges": [], "stats": {}}


def build_discovery_index(root: Path) -> dict:
    """Build the complete discovery index."""
    from datetime import datetime, timezone

    graph = load_knowledge_graph(root)
    documents = _build_documents(root)
    entities = _build_entities(graph)
    term_index = _build_term_index(documents, entities)
    stats = _compute_stats(documents, entities, term_index, graph)
    diagnostics = _compute_diagnostics(documents, entities, term_index, root)

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "generator": GENERATOR,
        "sourceGraph": SOURCE_GRAPH,
        "stats": stats,
        "documents": documents,
        "entities": entities,
        "termIndex": term_index,
        "diagnostics": diagnostics,
    }
