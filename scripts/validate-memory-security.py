#!/usr/bin/env python3
"""Scan memory source records for likely sensitive content."""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import masked, repo_root

PLACEHOLDER = re.compile(r"(?i)(example|placeholder|sample|dummy|redacted|fake|<[^>]+>|xxxx)")

PATTERNS = [
    ("private-key", "high", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("api-key", "high", re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*[\"']?([A-Za-z0-9_\-/+=]{16,})")),
    ("password-assignment", "high", re.compile(r"(?i)password\s*[:=]\s*[\"']?([^\s\"']{8,})")),
    ("connection-string", "high", re.compile(r"(?i)(server|host)\s*=\s*[^;\n]+;\s*(database|db)\s*=\s*[^;\n]+;.*(password|pwd)\s*=\s*[^;\n]+")),
    ("auth-cookie", "high", re.compile(r"(?i)(set-cookie|cookie)\s*[:=]\s*([^\s;]{12,})")),
    ("mfa-code", "medium", re.compile(r"(?i)(mfa|otp|one[- ]time|verification)\D{0,20}(\d{6})")),
    ("ssn", "high", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit-card-like", "high", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("employee-record", "medium", re.compile(r"(?i)(employee\s+record|employee\s+ssn|personnel\s+file)")),
    ("confidential-prod", "medium", re.compile(r"(?i)(confidential\s+production\s+data|prod\s+dump|customer\s+export)")),
]


def is_placeholder(line: str) -> bool:
    return bool(PLACEHOLDER.search(line))


def detect(root: Path):
    findings = []
    for path in sorted((root / "memory").rglob("*")):
        if path.name.lower() == "readme.md":
            continue
        if not path.is_file() or path.suffix.lower() not in {".md", ".json"}:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for number, line in enumerate(text.splitlines(), 1):
            if is_placeholder(line):
                continue
            for name, severity, pattern in PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                captured = match.group(match.lastindex) if match.lastindex else match.group(0)
                findings.append(
                    {
                        "path": rel,
                        "line": number,
                        "pattern": name,
                        "severity": severity,
                        "masked": masked(str(captured)),
                    }
                )
    return findings


def main() -> int:
    root = repo_root()
    findings = detect(root)
    if not findings:
        print("PASS memory security scan")
        return 0

    high = [row for row in findings if row["severity"] == "high"]
    medium = [row for row in findings if row["severity"] != "high"]

    for row in high:
        print(
            "FAIL {path}:{line} {pattern} severity={severity} value={masked}".format(
                path=row["path"],
                line=row["line"],
                pattern=row["pattern"],
                severity=row["severity"],
                masked=row["masked"],
            ),
            file=sys.stderr,
        )
    for row in medium:
        print(
            "WARNING {path}:{line} {pattern} severity={severity} value={masked}".format(
                path=row["path"],
                line=row["line"],
                pattern=row["pattern"],
                severity=row["severity"],
                masked=row["masked"],
            )
        )

    if high:
        print(f"FAIL memory security scan ({len(high)} high-confidence finding(s))", file=sys.stderr)
        return 1

    print(f"PASS memory security scan ({len(medium)} warning(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
