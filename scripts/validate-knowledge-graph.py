#!/usr/bin/env python3
"""Validate generated AI OS knowledge graph artifacts."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from knowledge_graph.validate import KnowledgeGraphError, load_graph, validate_graph_object

ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "generated" / "knowledge-graph.json"


def main() -> int:
    if not GRAPH_PATH.is_file():
        print("FAIL generated/knowledge-graph.json is missing; run scripts/generate-knowledge-graph.py", file=sys.stderr)
        return 1
    try:
        graph = load_graph(GRAPH_PATH)
    except KnowledgeGraphError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    failures, warnings = validate_graph_object(graph)
    for item in warnings:
        print(f"WARNING {item}")
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1
    stats = graph.get("stats", {})
    print(f"PASS knowledge graph validation ({stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
