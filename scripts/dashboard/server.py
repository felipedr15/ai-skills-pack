"""Minimal local HTTP server for the AI OS dashboard."""
from __future__ import annotations

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import DEFAULT_PORT
from .aggregate import build_dashboard_data, _load_json


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve dashboard files and API endpoints for exploration views."""

    root: Path = Path(".")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json({"status": "ok", "generator": "ai-os-dashboard"})
        elif path == "/api/data":
            data = build_dashboard_data(self.root)
            self._send_json(data)
        elif path == "/api/skills":
            self._handle_skills(params)
        elif path == "/api/memory":
            self._handle_memory(params)
        elif path == "/api/graph/nodes":
            self._handle_graph_nodes(params)
        elif path == "/api/graph/edges":
            self._handle_graph_edges(params)
        elif path.startswith("/api/graph/node/"):
            node_id = path[len("/api/graph/node/"):]
            self._handle_graph_node_detail(node_id)
        elif path == "/api/discovery/search":
            self._handle_discovery_search(params)
        elif path.startswith("/api/discovery/explain/"):
            node_id = path[len("/api/discovery/explain/"):]
            query = params.get("q", [""])[0]
            self._handle_discovery_explain(node_id, query)
        elif path == "/api/repository":
            self._handle_repository(params)
        elif path == "/api/graph/visualize":
            self._handle_graph_visualize(params)
        elif path == "/" or path == "/index.html":
            self._serve_dashboard_html()
        else:
            super().do_GET()

    def _send_json(self, data):
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def _send_error_json(self, status: int, message: str):
        content = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_dashboard_html(self):
        html_path = self.root / "generated" / "dashboard.html"
        if not html_path.is_file():
            self.send_error(404, "Dashboard not built. Run: python scripts/dashboard-build.py")
            return
        content = html_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ── Skills API ──

    def _handle_skills(self, params: dict):
        data = _load_json(self.root / "generated" / "skills.json")
        if data is None:
            self._send_json({"available": False, "skills": [], "total": 0})
            return
        skills = data.get("skills", [])
        q = params.get("q", [""])[0].lower()
        platform = params.get("platform", [""])[0].lower()
        category = params.get("category", [""])[0].lower()
        path_filter = params.get("path", [""])[0]

        results = []
        for s in skills:
            if q and q not in s.get("name", "").lower() and q not in s.get("description", "").lower() and q not in s.get("id", "").lower():
                continue
            if path_filter and not s.get("path", "").startswith(path_filter):
                continue
            # Category filter: match against path segments
            if category:
                skill_path = s.get("path", "").lower()
                if category not in skill_path:
                    continue
            results.append({
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "version": s.get("version", ""),
                "status": s.get("status", ""),
                "description": s.get("description", ""),
                "path": s.get("path", ""),
                "triggers": s.get("triggers", []),
                "inputs": s.get("inputs", []),
                "outputs": s.get("outputs", []),
                "dependencies": s.get("dependencies", []),
            })

        results.sort(key=lambda x: (x.get("name", "").lower(), x.get("id", "")))
        self._send_json({"available": True, "skills": results, "total": len(results)})

    # ── Memory API ──

    def _handle_memory(self, params: dict):
        data = _load_json(self.root / "generated" / "memory-index.json")
        if data is None:
            self._send_json({"available": False, "records": [], "total": 0})
            return
        records = data.get("records", [])
        project = params.get("project", [""])[0]
        category = params.get("category", [""])[0]
        status_filter = params.get("status", [""])[0]

        # Load graph for related entities
        graph = _load_json(self.root / "generated" / "knowledge-graph.json") or {}
        edges = graph.get("edges", [])
        nodes_map = {n["id"]: n for n in graph.get("nodes", [])}

        results = []
        for rec in records:
            if project and (rec.get("project") or "") != project:
                continue
            if category and rec.get("type", "") != category:
                continue
            if status_filter and rec.get("status", "") != status_filter:
                continue

            # Find related graph entities (never expose full content)
            node_id = f"memory:{rec.get('id', '')}"
            related = []
            for edge in edges:
                if edge.get("from") == node_id or edge.get("to") == node_id:
                    other_id = edge["to"] if edge["from"] == node_id else edge["from"]
                    other = nodes_map.get(other_id, {})
                    related.append({
                        "nodeId": other_id,
                        "name": other.get("name", ""),
                        "type": other.get("type", ""),
                        "relationship": edge.get("type", ""),
                    })

            results.append({
                "id": rec.get("id", ""),
                "title": rec.get("title", ""),
                "type": rec.get("type", ""),
                "status": rec.get("status", ""),
                "scope": rec.get("scope", ""),
                "project": rec.get("project"),
                "summary": rec.get("summary", ""),
                "tags": rec.get("tags", []),
                "created": rec.get("created", ""),
                "updated": rec.get("updated", ""),
                "path": rec.get("path", ""),
                "related": related[:10],
            })

        results.sort(key=lambda x: (x.get("title", "").lower(), x.get("id", "")))
        self._send_json({"available": True, "records": results, "total": len(results)})

    # ── Knowledge Graph API ──

    def _handle_graph_nodes(self, params: dict):
        data = _load_json(self.root / "generated" / "knowledge-graph.json")
        if data is None:
            self._send_json({"available": False, "nodes": [], "total": 0})
            return
        nodes = data.get("nodes", [])
        type_filter = params.get("type", [""])[0]
        q = params.get("q", [""])[0].lower()
        limit = int(params.get("limit", ["100"])[0])

        results = []
        for n in nodes:
            if type_filter and n.get("type", "") != type_filter:
                continue
            if q and q not in n.get("name", "").lower() and q not in n.get("id", "").lower():
                continue
            results.append(n)

        results.sort(key=lambda x: (x.get("type", ""), x.get("name", "").lower(), x.get("id", "")))
        total = len(results)
        results = results[:limit]
        self._send_json({"available": True, "nodes": results, "total": total})

    def _handle_graph_edges(self, params: dict):
        data = _load_json(self.root / "generated" / "knowledge-graph.json")
        if data is None:
            self._send_json({"available": False, "edges": [], "total": 0})
            return
        edges = data.get("edges", [])
        type_filter = params.get("type", [""])[0]
        node_filter = params.get("node", [""])[0]
        limit = int(params.get("limit", ["100"])[0])

        results = []
        for e in edges:
            if type_filter and e.get("type", "") != type_filter:
                continue
            if node_filter and node_filter != e.get("from", "") and node_filter != e.get("to", ""):
                continue
            results.append(e)

        results.sort(key=lambda x: (x.get("type", ""), x.get("from", ""), x.get("to", "")))
        total = len(results)
        results = results[:limit]
        self._send_json({"available": True, "edges": results, "total": total})

    def _handle_graph_node_detail(self, node_id: str):
        from urllib.parse import unquote
        node_id = unquote(node_id)
        data = _load_json(self.root / "generated" / "knowledge-graph.json")
        if data is None:
            self._send_error_json(404, "Knowledge graph not available")
            return
        nodes_map = {n["id"]: n for n in data.get("nodes", [])}
        node = nodes_map.get(node_id)
        if node is None:
            self._send_error_json(404, f"Node not found: {node_id}")
            return

        edges = data.get("edges", [])
        inbound = [e for e in edges if e.get("to") == node_id]
        outbound = [e for e in edges if e.get("from") == node_id]

        inbound_details = []
        for e in sorted(inbound, key=lambda x: (x.get("type", ""), x.get("from", ""))):
            source = nodes_map.get(e["from"], {})
            inbound_details.append({
                "edgeId": e.get("id", ""),
                "relationship": e.get("type", ""),
                "nodeId": e.get("from", ""),
                "name": source.get("name", ""),
                "type": source.get("type", ""),
            })

        outbound_details = []
        for e in sorted(outbound, key=lambda x: (x.get("type", ""), x.get("to", ""))):
            target = nodes_map.get(e["to"], {})
            outbound_details.append({
                "edgeId": e.get("id", ""),
                "relationship": e.get("type", ""),
                "nodeId": e.get("to", ""),
                "name": target.get("name", ""),
                "type": target.get("type", ""),
            })

        self._send_json({
            "node": node,
            "inbound": inbound_details,
            "outbound": outbound_details,
            "totalInbound": len(inbound_details),
            "totalOutbound": len(outbound_details),
        })

    # ── Discovery API ──

    def _handle_discovery_search(self, params: dict):
        query = params.get("q", [""])[0]
        type_filter = params.get("type", [""])[0]
        path_filter = params.get("path", [""])[0]
        limit = int(params.get("limit", ["20"])[0])

        if not query.strip():
            self._send_json({"results": [], "total": 0, "query": ""})
            return

        # Use semantic discovery engine
        import sys as _sys
        scripts_dir = str(self.root / "scripts")
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)

        try:
            from semantic_discovery.query import tokenize_query
            from semantic_discovery.rank import rank_results, score_document, score_entity
            from semantic_discovery.traverse import direct_neighbors
            from semantic_discovery.validate import load_discovery_index
        except ImportError:
            self._send_error_json(500, "Semantic discovery module not available")
            return

        index_path = self.root / "generated" / "discovery-index.json"
        if not index_path.is_file():
            self._send_json({"results": [], "total": 0, "query": query, "error": "Discovery index not found"})
            return

        try:
            index = load_discovery_index(index_path)
        except Exception:
            self._send_json({"results": [], "total": 0, "query": query, "error": "Failed to load discovery index"})
            return

        graph = _load_json(self.root / "generated" / "knowledge-graph.json") or {}
        edges = graph.get("edges", [])
        query_tokens = tokenize_query(query)
        results = []

        for doc in index.get("documents", []):
            score, matched_fields, reasons = score_document(
                doc, query, query_tokens, type_filter=type_filter or None, path_filter=path_filter or None)
            if score > 0:
                results.append({
                    "id": doc["id"], "type": doc.get("category", "document"),
                    "name": doc.get("title", ""), "sourcePath": doc.get("sourcePath", ""),
                    "score": score, "matchedFields": matched_fields, "reasons": reasons,
                })

        for entity in index.get("entities", []):
            score, matched_fields, reasons = score_entity(
                entity, query, query_tokens, type_filter=type_filter or None, path_filter=path_filter or None)
            if score > 0:
                node_id = entity.get("nodeId", "")
                neighbors = direct_neighbors(node_id, edges)
                related = [{"nodeId": n["nodeId"], "relationship": n["relationship"]} for n in neighbors[:5]]
                results.append({
                    "id": entity["id"], "type": entity.get("type", ""),
                    "name": entity.get("name", ""), "sourcePath": entity.get("sourcePath", ""),
                    "score": score, "matchedFields": matched_fields, "reasons": reasons,
                    "related": related,
                })

        results = rank_results(results)
        total = len(results)
        results = results[:limit]
        self._send_json({"results": results, "total": total, "query": query})

    def _handle_discovery_explain(self, node_id: str, query: str):
        from urllib.parse import unquote
        node_id = unquote(node_id)

        if not query.strip():
            self._send_error_json(400, "Query parameter 'q' is required")
            return

        import sys as _sys
        scripts_dir = str(self.root / "scripts")
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)

        try:
            from semantic_discovery.query import tokenize_query
            from semantic_discovery.rank import score_entity, score_document
            from semantic_discovery.traverse import direct_neighbors
            from semantic_discovery.validate import load_discovery_index
        except ImportError:
            self._send_error_json(500, "Semantic discovery module not available")
            return

        graph = _load_json(self.root / "generated" / "knowledge-graph.json") or {}
        nodes_map = {n["id"]: n for n in graph.get("nodes", [])}
        node = nodes_map.get(node_id)
        if node is None:
            self._send_error_json(404, f"Node not found: {node_id}")
            return

        index_path = self.root / "generated" / "discovery-index.json"
        try:
            index = load_discovery_index(index_path)
        except Exception:
            self._send_error_json(500, "Failed to load discovery index")
            return

        query_tokens = tokenize_query(query)
        edges = graph.get("edges", [])

        # Score as entity
        entity_entry = None
        for entity in index.get("entities", []):
            if entity.get("nodeId") == node_id:
                entity_entry = entity
                break

        score, matched_fields, reasons = 0, [], []
        if entity_entry:
            score, matched_fields, reasons = score_entity(entity_entry, query, query_tokens)

        # Also try as document
        node_source = node.get("sourcePath", "")
        for doc in index.get("documents", []):
            if doc.get("sourcePath") == node_source:
                ds, df, dr = score_document(doc, query, query_tokens)
                if ds > score:
                    score, matched_fields, reasons = ds, df, dr
                break

        neighbors = direct_neighbors(node_id, edges)

        self._send_json({
            "nodeId": node_id,
            "node": node,
            "query": query,
            "score": score,
            "matchedFields": matched_fields,
            "reasons": reasons,
            "neighbors": len(neighbors),
            "neighborDetails": [
                {"nodeId": n["nodeId"], "direction": n["direction"], "relationship": n["relationship"],
                 "name": nodes_map.get(n["nodeId"], {}).get("name", "")}
                for n in neighbors[:10]
            ],
        })

    # ── Repository API ──

    def _handle_repository(self, params: dict):
        data = _load_json(self.root / "generated" / "repository-index.json")
        if data is None:
            self._send_json({"available": False, "files": [], "counts": {}, "total": 0})
            return
        files = data.get("files", [])
        category = params.get("category", [""])[0]
        q = params.get("q", [""])[0].lower()
        limit = int(params.get("limit", ["100"])[0])

        results = []
        for f in files:
            if category and f.get("category", "") != category:
                continue
            if q and q not in f.get("path", "").lower():
                continue
            results.append({"path": f.get("path", ""), "category": f.get("category", ""), "size": f.get("size", 0)})

        results.sort(key=lambda x: (x.get("category", ""), x.get("path", "")))
        total = len(results)
        results = results[:limit]

        counts = data.get("counts", {})
        self._send_json({"available": True, "files": results, "counts": counts, "total": total})

    # ── Graph Visualization API ──

    MAX_VIS_NODES = 50
    MAX_VIS_DEPTH = 3

    def _handle_graph_visualize(self, params: dict):
        """Return a subgraph suitable for visualization.

        Params:
            focus: node ID to center on (optional)
            depth: 1-3, how many hops from focus (default 1)
            nodeType: filter nodes by type
            edgeType: filter edges by type
            limit: max nodes to return (default 50, max 50)
        """
        from urllib.parse import unquote
        data = _load_json(self.root / "generated" / "knowledge-graph.json")
        if data is None:
            self._send_json({"available": False, "nodes": [], "edges": [], "total": 0, "truncated": False})
            return

        all_nodes = data.get("nodes", [])
        all_edges = data.get("edges", [])
        nodes_map = {n["id"]: n for n in all_nodes}

        focus = unquote(params.get("focus", [""])[0])
        depth = min(int(params.get("depth", ["1"])[0]), self.MAX_VIS_DEPTH)
        node_type = params.get("nodeType", [""])[0]
        edge_type = params.get("edgeType", [""])[0]
        limit = min(int(params.get("limit", [str(self.MAX_VIS_NODES)])[0]), self.MAX_VIS_NODES)

        if focus and focus in nodes_map:
            # BFS from focus node up to depth
            visited = {focus}
            frontier = {focus}
            for _ in range(depth):
                next_frontier = set()
                for edge in all_edges:
                    if edge_type and edge.get("type") != edge_type:
                        continue
                    src, tgt = edge.get("from", ""), edge.get("to", "")
                    if src in frontier and tgt not in visited:
                        if not node_type or nodes_map.get(tgt, {}).get("type") == node_type:
                            next_frontier.add(tgt)
                    if tgt in frontier and src not in visited:
                        if not node_type or nodes_map.get(src, {}).get("type") == node_type:
                            next_frontier.add(src)
                visited.update(next_frontier)
                frontier = next_frontier
                if len(visited) >= limit:
                    break

            vis_node_ids = sorted(visited)[:limit]
        else:
            # No focus: return top connected nodes by degree
            degree: dict[str, int] = {}
            for edge in all_edges:
                if edge_type and edge.get("type") != edge_type:
                    continue
                src, tgt = edge.get("from", ""), edge.get("to", "")
                if node_type:
                    if nodes_map.get(src, {}).get("type") == node_type:
                        degree[src] = degree.get(src, 0) + 1
                    if nodes_map.get(tgt, {}).get("type") == node_type:
                        degree[tgt] = degree.get(tgt, 0) + 1
                else:
                    degree[src] = degree.get(src, 0) + 1
                    degree[tgt] = degree.get(tgt, 0) + 1

            sorted_nodes = sorted(degree.keys(), key=lambda nid: (-degree[nid], nid))
            vis_node_ids = sorted_nodes[:limit]

        vis_node_set = set(vis_node_ids)
        vis_nodes = []
        for nid in vis_node_ids:
            node = nodes_map.get(nid)
            if node:
                vis_nodes.append({
                    "id": node["id"],
                    "name": node.get("name", ""),
                    "type": node.get("type", ""),
                    "sourcePath": node.get("sourcePath", ""),
                })

        vis_edges = []
        for edge in all_edges:
            if edge_type and edge.get("type") != edge_type:
                continue
            if edge.get("from") in vis_node_set and edge.get("to") in vis_node_set:
                vis_edges.append({
                    "id": edge.get("id", ""),
                    "type": edge.get("type", ""),
                    "from": edge.get("from", ""),
                    "to": edge.get("to", ""),
                })

        vis_edges.sort(key=lambda e: (e["type"], e["from"], e["to"]))
        truncated = len(all_nodes) > len(vis_nodes)

        self._send_json({
            "available": True,
            "nodes": vis_nodes,
            "edges": vis_edges,
            "total": len(all_nodes),
            "showing": len(vis_nodes),
            "truncated": truncated,
            "focus": focus if focus in nodes_map else None,
            "depth": depth,
            "maxNodes": self.MAX_VIS_NODES,
        })

    def translate_path(self, path):
        """Serve files from the generated/ directory."""
        from urllib.parse import unquote
        clean = unquote(path).lstrip("/")
        return str(self.root / "generated" / clean)

    def log_message(self, format, *args):
        """Suppress request logs unless verbose."""
        pass


def make_handler(root: Path):
    """Create a handler class configured with the repository root."""
    class ConfiguredHandler(DashboardHandler):
        pass
    ConfiguredHandler.root = root
    return ConfiguredHandler


def serve(root: Path, port: int = DEFAULT_PORT, open_browser: bool = True) -> None:
    """Start the dashboard server."""
    handler = make_handler(root)
    server = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}"
    print(f"AI OS Dashboard running at {url}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        import webbrowser
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
