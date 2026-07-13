"""Tokenization and query parsing for semantic discovery."""
from __future__ import annotations

import re

from .utils import PRESERVED_TERMS


# Simple stop words that add noise without helping search precision
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "from", "by",
    "as", "or", "and", "but", "if", "not", "no", "so", "it",
    "this", "that", "its", "my", "your", "their", "our",
}


def _split_camel_case(text: str) -> list[str]:
    """Split camelCase and PascalCase into tokens."""
    # Insert space before uppercase letters that follow lowercase
    split = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Insert space before uppercase letters that are followed by lowercase (acronyms)
    split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", split)
    return split.split()


def tokenize(text: str) -> list[str]:
    """Tokenize text into normalized search tokens.

    Supports:
    - Lowercase normalization
    - Punctuation removal
    - Hyphenated term splitting
    - snake_case splitting
    - camelCase splitting
    - Preserved technical terms
    """
    if not text:
        return []

    tokens: list[str] = []
    # First check for preserved terms (case-insensitive)
    lowered = text.lower()
    for term in PRESERVED_TERMS:
        if term in lowered:
            tokens.append(term)

    # Split on common boundaries
    # Replace hyphens, underscores, slashes, dots with spaces
    normalized = re.sub(r"[_\-/\\.]", " ", text)
    # Remove punctuation except alphanumeric and spaces
    normalized = re.sub(r"[^a-zA-Z0-9\s]", " ", normalized)

    # Split and process each word
    for word in normalized.split():
        if not word:
            continue
        # Try camelCase splitting
        camel_parts = _split_camel_case(word)
        for part in camel_parts:
            lower_part = part.lower()
            if lower_part and len(lower_part) > 1:
                tokens.append(lower_part)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)

    return unique


def tokenize_query(text: str, remove_stop_words: bool = True) -> list[str]:
    """Tokenize a search query, optionally removing stop words."""
    tokens = tokenize(text)
    if remove_stop_words:
        filtered = [t for t in tokens if t not in STOP_WORDS]
        # If all tokens were stop words, keep original tokens
        return filtered if filtered else tokens
    return tokens


def phrase_matches(text: str, phrase: str) -> bool:
    """Check if the phrase appears in the text (case-insensitive)."""
    return phrase.lower() in text.lower()


def exact_match(text: str, query: str) -> bool:
    """Check if query exactly matches text (case-insensitive)."""
    return text.lower().strip() == query.lower().strip()
