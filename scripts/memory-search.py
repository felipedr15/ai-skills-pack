#!/usr/bin/env python3
"""Search memory records by keywords in metadata and Markdown content."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_utils import load_registry, parse_front_matter, repo_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phrase", help="Search phrase")
    parser.add_argument("--type")
    parser.add_argument("--project")
    parser.add_argument("--tag")
    parser.add_argument("--max-results", type=int, default=10)
    return parser


def score_record(phrase: str, tokens, title: str, summary: str, tags, body: str) -> int:
    score = 0
    lowered_phrase = phrase.lower()
    title_l = title.lower()
    summary_l = summary.lower()
    tags_l = " ".join(tag.lower() for tag in tags)
    body_l = body.lower()

    if lowered_phrase in title_l:
        score += 30
    if lowered_phrase in summary_l:
        score += 20
    if lowered_phrase in tags_l:
        score += 15
    if lowered_phrase in body_l:
        score += 8

    for token in tokens:
        if token in title_l:
            score += 8
        if token in summary_l:
            score += 5
        if token in tags_l:
            score += 4
        if token in body_l:
            score += 2
    return score


def excerpt_for(body: str, phrase: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    lowered = phrase.lower()
    for line in lines:
        if lowered in line.lower():
            return line[:180]
    for line in lines:
        if line.startswith("## "):
            continue
        return line[:180]
    return ""


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    phrase = args.phrase.strip()
    tokens = [token for token in re.split(r"\s+", phrase.lower()) if token]
    if not phrase:
        print("FAIL search phrase cannot be empty", file=sys.stderr)
        return 1

    try:
        registry = load_registry(repo_root())["records"]
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    root = repo_root()
    matches = []
    for row in registry:
        if args.type and row.get("type") != args.type:
            continue
        if args.project and (row.get("project") or "") != args.project:
            continue
        if args.tag and args.tag not in row.get("tags", []):
            continue
        path = root / row["path"]
        if not path.is_file():
            continue
        metadata, body = parse_front_matter(path)
        title = str(metadata.get("title", row.get("title", "")))
        summary = str(metadata.get("summary", ""))
        tags = metadata.get("tags", row.get("tags", []))
        score = score_record(phrase, tokens, title, summary, tags, body)
        if score <= 0:
            continue
        matches.append(
            {
                "score": score,
                "id": row["id"],
                "title": title,
                "type": row["type"],
                "project": row.get("project") or "-",
                "path": row["path"],
                "excerpt": excerpt_for(body + "\n" + summary, phrase) or summary,
            }
        )

    matches.sort(key=lambda item: (-item["score"], item["id"]))
    if args.max_results > 0:
        matches = matches[: args.max_results]

    print(f"{'Score':<7} {'ID':<40} {'Title':<40} {'Type':<10} {'Project':<12} Path")
    print("-" * 150)
    for item in matches:
        print(f"{item['score']:<7} {item['id']:<40} {item['title'][:39]:<40} {item['type']:<10} {item['project'][:11]:<12} {item['path']}")
        print(f"  Excerpt: {item['excerpt']}")
    print(f"\n{len(matches)} match(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
