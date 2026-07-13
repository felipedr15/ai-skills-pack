#!/usr/bin/env python3
"""Semantic discovery CLI for querying the AI OS knowledge base."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_discovery import DEFAULT_RESULT_LIMIT, DEFAULT_TRAVERSAL_DEPTH
from semantic_discovery.cli import cmd_explain, cmd_path, cmd_related, cmd_search, cmd_stats, cmd_traverse

ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Semantic discovery and graph-query engine for AI OS.",
        prog="discover.py",
    )
    subparsers = parser.add_subparsers(dest="command", help="Discovery command")

    # search
    search_parser = subparsers.add_parser("search", help="Search for matching nodes and documents")
    search_parser.add_argument("query", help="Search query text")
    search_parser.add_argument("--type", dest="type_filter", help="Filter by entity/document type")
    search_parser.add_argument("--path", dest="path_filter", help="Filter by source path prefix")
    search_parser.add_argument("--relationship", help="Filter by relationship type")
    search_parser.add_argument("--limit", type=int, default=DEFAULT_RESULT_LIMIT, help="Maximum results")
    search_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    search_parser.add_argument("--include-isolated", action="store_true", help="Include isolated entities")
    search_parser.add_argument("--case-sensitive", action="store_true", help="Case-sensitive search")
    search_parser.add_argument("--exact", action="store_true", help="Exact match only")
    search_parser.add_argument("--json", action="store_true", help="Output as JSON (shorthand for --format json)")

    # related
    related_parser = subparsers.add_parser("related", help="Find directly related nodes")
    related_parser.add_argument("node_id", help="Node ID to find neighbors for")
    related_parser.add_argument("--relationship", help="Filter by relationship type")
    related_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    related_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # traverse
    traverse_parser = subparsers.add_parser("traverse", help="Traverse relationships from a node")
    traverse_parser.add_argument("node_id", help="Starting node ID")
    traverse_parser.add_argument("--depth", type=int, default=DEFAULT_TRAVERSAL_DEPTH, help="Traversal depth")
    traverse_parser.add_argument("--relationship", help="Filter by relationship type")
    traverse_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    traverse_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # path
    path_parser = subparsers.add_parser("path", help="Find shortest path between two nodes")
    path_parser.add_argument("source_id", help="Source node ID")
    path_parser.add_argument("target_id", help="Target node ID")
    path_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    path_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # explain
    explain_parser = subparsers.add_parser("explain", help="Explain why a node matches a query")
    explain_parser.add_argument("node_id", help="Node ID to explain")
    explain_parser.add_argument("query", help="Query to explain against")
    explain_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    explain_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Display discovery index statistics")
    stats_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    output_json = getattr(args, "json", False) or getattr(args, "format", "text") == "json"

    if args.command == "search":
        return cmd_search(
            ROOT,
            args.query,
            type_filter=args.type_filter,
            path_filter=args.path_filter,
            relationship_filter=args.relationship,
            limit=args.limit,
            output_json=output_json,
            include_isolated=args.include_isolated,
            case_sensitive=args.case_sensitive,
            exact=args.exact,
        )
    elif args.command == "related":
        return cmd_related(ROOT, args.node_id, relationship=args.relationship, output_json=output_json)
    elif args.command == "traverse":
        return cmd_traverse(ROOT, args.node_id, depth=args.depth, relationship=args.relationship, output_json=output_json)
    elif args.command == "path":
        return cmd_path(ROOT, args.source_id, args.target_id, output_json=output_json)
    elif args.command == "explain":
        return cmd_explain(ROOT, args.node_id, args.query, output_json=output_json)
    elif args.command == "stats":
        return cmd_stats(ROOT, output_json=output_json)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
