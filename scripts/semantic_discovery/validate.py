"""Validation for discovery index artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from . import SCHEMA_VERSION
from .utils import is_secret_like_path, safe_source_path


class DiscoveryError(ValueError):
    """Raised when discovery validation fails."""
    pass


def load_discovery_index(path: Path) -> dict:
    """Load a discovery index JSON file."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DiscoveryError(f"unable to read discovery index: {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise DiscoveryError(f"unable to read discovery index: {path}: {exc}") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise DiscoveryError(f"invalid JSON in discovery index: {exc}") from exc


def validate_index_object(index: object) -> tuple[list[str], list[str]]:
    """Validate a discovery index object.

    Returns (failures, warnings).
    """
    failures: list[str] = []
    warnings: list[str] = []

    if not isinstance(index, dict):
        failures.append("discovery index root must be an object")
        return failures, warnings

    # Schema version
    if index.get("schemaVersion") != SCHEMA_VERSION:
        failures.append("schemaVersion is missing or unsupported")

    # Required string fields
    for field in ("generatedAt", "generator", "sourceGraph"):
        value = index.get(field)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{field} must be a nonempty string")

    # Stats validation
    stats = index.get("stats")
    if not isinstance(stats, dict):
        failures.append("stats must be an object")
    else:
        for key in ("documents", "entities", "terms", "relationships"):
            if not isinstance(stats.get(key), int):
                failures.append(f"stats.{key} must be an integer")

    # Documents validation
    documents = index.get("documents")
    if not isinstance(documents, list):
        failures.append("documents must be a list")
        documents = []

    doc_ids: set[str] = set()
    for doc in documents:
        if not isinstance(doc, dict):
            failures.append("document entry is not an object")
            continue
        doc_id = doc.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            failures.append("document id must be a nonempty string")
            continue
        if doc_id in doc_ids:
            failures.append(f"duplicate document id: {doc_id}")
        doc_ids.add(doc_id)

        source_path = doc.get("sourcePath")
        if not isinstance(source_path, str):
            failures.append(f"document sourcePath must be a string: {doc_id}")
        elif not safe_source_path(source_path):
            failures.append(f"invalid document sourcePath: {source_path}")
        elif source_path.startswith("/"):
            failures.append(f"absolute document sourcePath: {source_path}")
        elif "\\" in source_path:
            failures.append(f"backslash in document sourcePath: {source_path}")
        elif ".." in Path(source_path).parts:
            failures.append(f"document sourcePath escapes repository: {source_path}")

        if is_secret_like_path(source_path or ""):
            failures.append(f"secret-like file in discovery index: {source_path}")

    # Entities validation
    entities = index.get("entities")
    if not isinstance(entities, list):
        failures.append("entities must be a list")
        entities = []

    entity_ids: set[str] = set()
    node_ids_in_entities: set[str] = set()
    for entity in entities:
        if not isinstance(entity, dict):
            failures.append("entity entry is not an object")
            continue
        entity_id = entity.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            failures.append("entity id must be a nonempty string")
            continue
        if entity_id in entity_ids:
            failures.append(f"duplicate entity id: {entity_id}")
        entity_ids.add(entity_id)

        node_id = entity.get("nodeId")
        if isinstance(node_id, str):
            node_ids_in_entities.add(node_id)

        source_path = entity.get("sourcePath")
        if isinstance(source_path, str) and source_path:
            if not safe_source_path(source_path):
                failures.append(f"invalid entity sourcePath: {source_path}")
            elif "\\" in source_path:
                failures.append(f"backslash in entity sourcePath: {source_path}")

        entity_type = entity.get("type")
        if not isinstance(entity_type, str) or not entity_type:
            failures.append(f"entity type must be a nonempty string: {entity_id}")

    # Term index validation
    term_index = index.get("termIndex")
    if not isinstance(term_index, dict):
        failures.append("termIndex must be an object")
        term_index = {}

    all_valid_ids = doc_ids | entity_ids
    for term, refs in term_index.items():
        if not isinstance(term, str) or not term:
            failures.append("term index key must be a nonempty string")
            continue
        if not isinstance(refs, list):
            failures.append(f"term index value must be a list: {term}")
            continue
        for ref in refs:
            if ref not in all_valid_ids:
                failures.append(f"term index references nonexistent id: {term} -> {ref}")

    # Statistics cross-check
    if isinstance(stats, dict):
        doc_count = stats.get("documents")
        if isinstance(doc_count, int) and doc_count != len(documents):
            failures.append(f"stats.documents ({doc_count}) does not match documents length ({len(documents)})")
        entity_count = stats.get("entities")
        if isinstance(entity_count, int) and entity_count != len(entities):
            failures.append(f"stats.entities ({entity_count}) does not match entities length ({len(entities)})")
        term_count = stats.get("terms")
        if isinstance(term_count, int) and term_count != len(term_index):
            failures.append(f"stats.terms ({term_count}) does not match termIndex length ({len(term_index)})")

    # Diagnostics
    diagnostics = index.get("diagnostics")
    if isinstance(diagnostics, dict):
        diag_warnings = diagnostics.get("warnings", [])
        if isinstance(diag_warnings, list):
            for w in diag_warnings:
                warnings.append(str(w))
        unindexed = diagnostics.get("unindexedFiles", [])
        if isinstance(unindexed, list) and unindexed:
            warnings.append(f"unindexed files: {len(unindexed)}")

    # Warnings for isolated entities
    indexed_entity_ids = set()
    for refs in term_index.values():
        for ref in refs:
            if ref in entity_ids:
                indexed_entity_ids.add(ref)
    isolated = [eid for eid in entity_ids if eid not in indexed_entity_ids]
    if isolated:
        warnings.append(f"entities with no searchable terms: {len(isolated)}")

    return failures, warnings


def compare_indexes_ignoring_generated_at(current: dict, saved: dict) -> bool:
    """Compare two discovery indexes ignoring generatedAt timestamp."""
    left = dict(current)
    right = dict(saved)
    left["generatedAt"] = "<ignored>"
    right["generatedAt"] = "<ignored>"
    return left == right
