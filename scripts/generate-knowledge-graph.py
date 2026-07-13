#!/usr/bin/env python3
"""Build or check the local AI OS knowledge graph artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from knowledge_graph.build import build_graph, validate_source_paths
from knowledge_graph.render import render_json, render_markdown
from knowledge_graph.validate import KnowledgeGraphError, compare_graphs_ignoring_generated_at, load_graph, validate_graph_object

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "generated" / "knowledge-graph.json"
OUT_MD = ROOT / "generated" / "knowledge-graph.md"


class GraphBuildError(ValueError):
    pass


def _normalize_markdown_timestamp(content: str) -> str:
    lines = content.splitlines()
    normalized: list[str] = []
    for line in lines:
        if line.startswith("Generated at: "):
            normalized.append("Generated at: <ignored>")
        else:
            normalized.append(line)
    return "\n".join(normalized)


def build() -> dict:
    graph = build_graph(ROOT)
    source_path_errors = validate_source_paths(graph)
    if source_path_errors:
        raise GraphBuildError("\n".join(source_path_errors))
    failures, _warnings = validate_graph_object(graph)
    if failures:
        raise GraphBuildError("\n".join(failures))
    return graph


def write_graph(graph: dict) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(render_json(graph), encoding="utf-8", newline="\n")
    OUT_MD.write_text(render_markdown(graph), encoding="utf-8", newline="\n")


def check_graph(graph: dict) -> None:
    if not OUT_JSON.is_file() or not OUT_MD.is_file():
        raise GraphBuildError("stale generated files: generated/knowledge-graph.json, generated/knowledge-graph.md")

    expected_json = json.loads(render_json(graph))
    expected_md = render_markdown(graph)

    try:
        saved = load_graph(OUT_JSON)
    except KnowledgeGraphError as exc:
        raise GraphBuildError(str(exc)) from exc

    if not compare_graphs_ignoring_generated_at(expected_json, saved):
        raise GraphBuildError("stale generated files: generated/knowledge-graph.json")

    try:
        saved_md_text = OUT_MD.read_text(encoding="utf-8")
    except OSError as exc:
        raise GraphBuildError(f"unable to read generated files: {exc}") from exc

    if _normalize_markdown_timestamp(saved_md_text) != _normalize_markdown_timestamp(expected_md):
        raise GraphBuildError("stale generated files: generated/knowledge-graph.md")



def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated graph files are stale")
    args = parser.parse_args(argv)

    try:
        graph = build()
        if args.check:
            check_graph(graph)
            print(f"PASS knowledge graph is current ({graph['stats']['nodes']} nodes, {graph['stats']['edges']} edges)")
            return 0
        write_graph(graph)
        print(f"PASS knowledge graph generated ({graph['stats']['nodes']} nodes, {graph['stats']['edges']} edges)")
        return 0
    except GraphBuildError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
