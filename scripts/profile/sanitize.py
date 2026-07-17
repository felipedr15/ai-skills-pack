"""Write-time sanitization for professional-context knowledge content
(Tasks 010-011).

Applied *before* any content is written to knowledge/professional-context/
overview.md or a snapshot -- not only as a post-hoc scan, unlike
scripts/validate-memory-security.py's after-the-fact detector (whose
pattern set this module extends and reuses the masking convention of).

Findings never surface the raw matched value anywhere -- not in the
returned findings, not in raised exceptions, not in anything a caller
might log or print -- only a masked excerpt or, for the hard gate
(assert_sanitized), only the pattern *name*. This is deliberate: a
prohibited-content check that leaks the value it found would defeat its
own purpose.
"""
from __future__ import annotations

import re

PLACEHOLDER = re.compile(r"(?i)(example|placeholder|sample|dummy|redacted|fake|<[^>]+>|xxxx|n/a|tbd)")

# (name, pattern) -- name is safe to surface, the matched text never is.
PROHIBITED_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("api-key-or-token", re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*[\"']?([A-Za-z0-9_\-/+=]{16,})")),
    ("password", re.compile(r"(?i)password\s*[:=]\s*[\"']?([^\s\"']{6,})")),
    ("generic-secret", re.compile(r"(?i)\bsecret\s*[:=]\s*[\"']?([A-Za-z0-9_\-/+=]{8,})")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit-card-like", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("phone-number", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("email-address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("street-address", re.compile(r"(?i)\b\d{1,6}\s+\w+(?:\s\w+){0,3}\s+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd)\b")),
    ("zip-code", re.compile(r"(?i)\bzip(?:\s*code)?\s*[:#]?\s*\d{5}(?:-\d{4})?\b")),
    ("employee-id", re.compile(r"(?i)\bemployee\s*(?:id|#|number)\s*[:#]?\s*[A-Za-z0-9-]{3,}\b")),
    ("internal-ip", re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b")),
    ("reviewer-or-signature", re.compile(r"(?i)\b(?:reviewed\s+by|reviewer|signed\s+by|signature)\s*[:]\s*\S")),
    ("confidential-marker", re.compile(r"(?i)\b(?:confidential|do not distribute|internal use only|county security)\b")),
    ("resume-or-evaluation-marker", re.compile(r"(?i)\b(?:curriculum vitae|performance evaluation|performance review score|annual review rating)\b")),
]


class SanitizationError(ValueError):
    """Raised when content contains a prohibited pattern. Never carries the
    matched value -- only the offending pattern name(s)."""


def _mask(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) <= 6:
        return "***"
    return trimmed[:3] + "***" + trimmed[-2:]


def find_prohibited(text: str) -> list[tuple[str, str]]:
    """Return [(pattern_name, masked_excerpt), ...] for every match.

    Lines that look like documentation placeholders (e.g. "<role>",
    "example@example.com") are skipped, matching the existing
    scripts/validate-memory-security.py convention.
    """
    findings: list[tuple[str, str]] = []
    for line in text.splitlines():
        if PLACEHOLDER.search(line):
            continue
        for name, pattern in PROHIBITED_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append((name, _mask(match.group(0))))
    return findings


def assert_sanitized(text: str, context: str = "content") -> None:
    """Hard gate: raise SanitizationError if any prohibited pattern is
    found. The exception message names only the pattern types found,
    never any matched value, masked or otherwise.
    """
    findings = find_prohibited(text)
    if findings:
        names = sorted({name for name, _masked in findings})
        raise SanitizationError(
            f"{context} contains prohibited content pattern(s): {', '.join(names)}"
        )
