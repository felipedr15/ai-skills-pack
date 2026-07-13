"""Deterministic scoring and ranking for search results."""
from __future__ import annotations

from .query import exact_match, phrase_matches, tokenize_query


# Scoring weights
EXACT_NAME_MATCH = 100
EXACT_PHRASE_IN_NAME = 60
NAME_TOKEN_MATCH = 20
TITLE_PHRASE_MATCH = 50
TITLE_TOKEN_MATCH = 15
HEADING_PHRASE_MATCH = 30
HEADING_TOKEN_MATCH = 10
SNIPPET_PHRASE_MATCH = 20
SNIPPET_TOKEN_MATCH = 5
METADATA_MATCH = 12
SOURCE_PATH_MATCH = 8
NODE_TYPE_MATCH = 25
DIRECT_RELATIONSHIP = 15
GRAPH_DISTANCE_BONUS = 5


def score_document(doc: dict, query: str, query_tokens: list[str], *, type_filter: str | None = None, path_filter: str | None = None) -> tuple[int, list[str], list[str]]:
    """Score a document against a query.

    Returns (score, matched_fields, reasons).
    """
    score = 0
    matched_fields: list[str] = []
    reasons: list[str] = []

    # Empty query cannot match anything
    if not query.strip() and not query_tokens:
        return 0, [], []

    title = doc.get("title", "")
    headings = doc.get("headings", [])
    snippet = doc.get("snippet", "")
    source_path = doc.get("sourcePath", "")
    category = doc.get("category", "")
    front_matter = doc.get("frontMatter", {})

    # Type filter check
    if type_filter and category != type_filter:
        return 0, [], []

    # Path filter check
    if path_filter and not source_path.startswith(path_filter):
        return 0, [], []

    # Exact name/title match
    if exact_match(title, query):
        score += EXACT_NAME_MATCH
        matched_fields.append("title")
        reasons.append(f"exact title match: '{title}'")

    # Phrase in title
    elif phrase_matches(title, query):
        score += EXACT_PHRASE_IN_NAME
        matched_fields.append("title")
        reasons.append(f"phrase in title: '{title}'")

    # Token matches in title
    else:
        title_lower = title.lower()
        title_token_hits = [t for t in query_tokens if t in title_lower]
        if title_token_hits:
            score += TITLE_TOKEN_MATCH * len(title_token_hits)
            matched_fields.append("title")
            reasons.append(f"title tokens: {title_token_hits}")

    # Heading matches
    for heading in headings:
        if phrase_matches(heading, query):
            score += HEADING_PHRASE_MATCH
            matched_fields.append("headings")
            reasons.append(f"phrase in heading: '{heading}'")
            break
    else:
        for heading in headings:
            heading_lower = heading.lower()
            heading_token_hits = [t for t in query_tokens if t in heading_lower]
            if heading_token_hits:
                score += HEADING_TOKEN_MATCH * len(heading_token_hits)
                matched_fields.append("headings")
                reasons.append(f"heading tokens in '{heading}': {heading_token_hits}")
                break

    # Snippet match
    if phrase_matches(snippet, query):
        score += SNIPPET_PHRASE_MATCH
        matched_fields.append("snippet")
        reasons.append("phrase found in snippet")
    else:
        snippet_lower = snippet.lower()
        snippet_token_hits = [t for t in query_tokens if t in snippet_lower]
        if snippet_token_hits:
            score += SNIPPET_TOKEN_MATCH * len(snippet_token_hits)
            matched_fields.append("snippet")
            reasons.append(f"snippet tokens: {snippet_token_hits}")

    # Source path match
    path_lower = source_path.lower()
    path_token_hits = [t for t in query_tokens if t in path_lower]
    if path_token_hits:
        score += SOURCE_PATH_MATCH * len(path_token_hits)
        matched_fields.append("sourcePath")
        reasons.append(f"path tokens: {path_token_hits}")

    # Front matter metadata match
    for key, value in front_matter.items():
        if isinstance(value, str) and value:
            if phrase_matches(value, query):
                score += METADATA_MATCH
                matched_fields.append(f"frontMatter.{key}")
                reasons.append(f"metadata '{key}' contains phrase")
                break
            value_lower = value.lower()
            meta_hits = [t for t in query_tokens if t in value_lower]
            if meta_hits:
                score += METADATA_MATCH
                matched_fields.append(f"frontMatter.{key}")
                reasons.append(f"metadata '{key}' tokens: {meta_hits}")
                break

    return score, matched_fields, reasons


def score_entity(entity: dict, query: str, query_tokens: list[str], *, type_filter: str | None = None, path_filter: str | None = None, relationship_filter: str | None = None, neighbors: set[str] | None = None) -> tuple[int, list[str], list[str]]:
    """Score a graph entity against a query.

    Returns (score, matched_fields, reasons).
    """
    score = 0
    matched_fields: list[str] = []
    reasons: list[str] = []

    # Empty query cannot match anything
    if not query.strip() and not query_tokens:
        return 0, [], []

    name = entity.get("name", "")
    node_type = entity.get("type", "")
    source_path = entity.get("sourcePath", "")
    node_id = entity.get("nodeId", "")
    metadata = entity.get("metadata", {})

    # Type filter check
    if type_filter and node_type != type_filter:
        return 0, [], []

    # Path filter check
    if path_filter and not source_path.startswith(path_filter):
        return 0, [], []

    # Exact name match
    if exact_match(name, query):
        score += EXACT_NAME_MATCH
        matched_fields.append("name")
        reasons.append(f"exact name match: '{name}'")

    # Phrase in name
    elif phrase_matches(name, query):
        score += EXACT_PHRASE_IN_NAME
        matched_fields.append("name")
        reasons.append(f"phrase in name: '{name}'")

    # Token matches in name
    else:
        name_lower = name.lower()
        name_token_hits = [t for t in query_tokens if t in name_lower]
        if name_token_hits:
            score += NAME_TOKEN_MATCH * len(name_token_hits)
            matched_fields.append("name")
            reasons.append(f"name tokens: {name_token_hits}")

    # Node type match
    type_lower = node_type.lower()
    type_token_hits = [t for t in query_tokens if t in type_lower]
    if type_token_hits:
        score += NODE_TYPE_MATCH
        matched_fields.append("type")
        reasons.append(f"type match: '{node_type}'")

    # Source path match
    path_lower = source_path.lower()
    path_token_hits = [t for t in query_tokens if t in path_lower]
    if path_token_hits:
        score += SOURCE_PATH_MATCH * len(path_token_hits)
        matched_fields.append("sourcePath")
        reasons.append(f"path tokens: {path_token_hits}")

    # Metadata match
    for key, value in metadata.items():
        if isinstance(value, str) and value:
            if phrase_matches(value, query):
                score += METADATA_MATCH
                matched_fields.append(f"metadata.{key}")
                reasons.append(f"metadata '{key}' contains phrase")
                break

    # Graph neighbor bonus
    if neighbors and node_id in neighbors:
        score += DIRECT_RELATIONSHIP
        matched_fields.append("relationship")
        reasons.append("direct graph relationship to query context")

    return score, matched_fields, reasons


def rank_results(results: list[dict]) -> list[dict]:
    """Sort results by score descending with stable tie-breaking.

    Tie-breaking order:
    1. Score descending
    2. Type alphabetically
    3. Name alphabetically (normalized)
    4. ID alphabetically
    """
    return sorted(
        results,
        key=lambda item: (
            -item.get("score", 0),
            item.get("type", ""),
            item.get("name", "").lower(),
            item.get("id", ""),
        ),
    )
