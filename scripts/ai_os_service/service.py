"""Core service operations for AI OS."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import (
    DEFAULT_LIMIT,
    MAX_EXCERPT_CHARS,
    MAX_LIMIT,
    MAX_TRAVERSAL_DEPTH,
    SERVICE_VERSION,
)
from .errors import (
    InvalidRequest,
    LimitExceeded,
    MalformedArtifact,
    NotFound,
    Unavailable,
)
from .pagination import clamp_limit, paginate
from .permissions import (
    is_secret_like,
    is_text_file,
    normalize_path,
    redact_sensitive_content,
    validate_path,
)
from .utils import artifact_status, load_json_artifact


class AiOsService:
    """Protocol-neutral service providing AI OS capabilities."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._ensure_scripts_path()

    def _ensure_scripts_path(self):
        scripts_dir = str(self.root / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

    def _gen(self, name: str) -> Path:
        return self.root / "generated" / name

    def _load_graph(self) -> dict:
        data = load_json_artifact(self._gen("knowledge-graph.json"))
        if data is None:
            raise Unavailable("knowledge graph not available")
        return data

    def _load_discovery(self) -> dict:
        data = load_json_artifact(self._gen("discovery-index.json"))
        if data is None:
            raise Unavailable("discovery index not available")
        return data

    # ── 1. Repository Status ──

    def get_repository_status(self) -> dict:
        return {
            "serviceVersion": SERVICE_VERSION,
            "repositoryRoot": str(self.root),
            "artifacts": self.list_generated_artifacts(),
        }

    # ── 2. Validation Status ──

    def get_validation_status(self) -> dict:
        """Return structured validation state without running commands."""
        artifacts = self.list_generated_artifacts()
        all_valid = all(a.get("valid") and a.get("exists") for a in artifacts.get("artifacts", []))
        return {
            "allArtifactsPresent": all_valid,
            "artifacts": artifacts.get("artifacts", []),
        }

    # ── 3. Skill Listing ──

    def list_skills(self, *, platform: str = "", tool: str = "",
                    category: str = "", path: str = "",
                    limit: int = DEFAULT_LIMIT, cursor: int = 0) -> dict:
        data = load_json_artifact(self._gen("skills.json"))
        if data is None:
            raise Unavailable("skills registry not available")
        skills = data.get("skills", [])

        results = []
        for s in skills:
            if platform and platform.lower() not in json.dumps(s.get("triggers", [])).lower():
                continue
            if tool and tool.lower() not in json.dumps(s).lower():
                continue
            if category and category.lower() not in s.get("path", "").lower():
                continue
            if path and not s.get("path", "").startswith(path):
                continue
            results.append({
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "version": s.get("version", ""),
                "status": s.get("status", ""),
                "description": s.get("description", ""),
                "path": s.get("path", ""),
                "triggers": s.get("triggers", []),
                "dependencies": s.get("dependencies", []),
            })

        results.sort(key=lambda x: (x["name"].lower(), x["id"]))
        return paginate(results, limit, cursor)

    # ── 4. Skill Lookup ──

    def get_skill(self, *, skill_id: str = "", source_path: str = "") -> dict:
        if not skill_id and not source_path:
            raise InvalidRequest("skill_id or source_path required")
        data = load_json_artifact(self._gen("skills.json"))
        if data is None:
            raise Unavailable("skills registry not available")
        for s in data.get("skills", []):
            if skill_id and s.get("id") == skill_id:
                return s
            if source_path and s.get("path") == source_path:
                return s
        raise NotFound(f"skill not found: {skill_id or source_path}")

    # ── 5. Memory Summary Listing ──

    def list_memory_summaries(self, *, project: str = "", category: str = "",
                              source: str = "", limit: int = DEFAULT_LIMIT,
                              cursor: int = 0) -> dict:
        data = load_json_artifact(self._gen("memory-index.json"))
        if data is None:
            raise Unavailable("memory index not available")
        records = data.get("records", [])

        results = []
        for r in records:
            if project and (r.get("project") or "") != project:
                continue
            if category and r.get("type", "") != category:
                continue
            if source and r.get("source", "") != source:
                continue
            # Never return full body - only safe summary fields
            results.append({
                "id": r.get("id", ""),
                "title": r.get("title", ""),
                "type": r.get("type", ""),
                "status": r.get("status", ""),
                "scope": r.get("scope", ""),
                "project": r.get("project"),
                "summary": r.get("summary", ""),
                "tags": r.get("tags", []),
                "created": r.get("created", ""),
                "updated": r.get("updated", ""),
                "path": r.get("path", ""),
            })

        results.sort(key=lambda x: (x["title"].lower(), x["id"]))
        return paginate(results, limit, cursor)

    # ── 6. Memory Summary Lookup ──

    def get_memory_summary(self, *, memory_id: str) -> dict:
        if not memory_id:
            raise InvalidRequest("memory_id required")
        data = load_json_artifact(self._gen("memory-index.json"))
        if data is None:
            raise Unavailable("memory index not available")
        for r in data.get("records", []):
            if r.get("id") == memory_id:
                return {
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "type": r.get("type", ""),
                    "status": r.get("status", ""),
                    "scope": r.get("scope", ""),
                    "project": r.get("project"),
                    "summary": r.get("summary", ""),
                    "tags": r.get("tags", []),
                    "created": r.get("created", ""),
                    "updated": r.get("updated", ""),
                    "path": r.get("path", ""),
                }
        raise NotFound(f"memory record not found: {memory_id}")

    # ── 7. Knowledge Graph Node Lookup ──

    def get_node(self, *, node_id: str) -> dict:
        if not node_id:
            raise InvalidRequest("node_id required")
        graph = self._load_graph()
        for n in graph.get("nodes", []):
            if n.get("id") == node_id:
                return n
        raise NotFound(f"node not found: {node_id}")

    # ── 8. Knowledge Graph Neighbors ──

    def get_neighbors(self, *, node_id: str, relationship: str = "",
                      direction: str = "", limit: int = DEFAULT_LIMIT) -> dict:
        if not node_id:
            raise InvalidRequest("node_id required")
        graph = self._load_graph()
        nodes_map = {n["id"]: n for n in graph.get("nodes", [])}
        if node_id not in nodes_map:
            raise NotFound(f"node not found: {node_id}")

        from semantic_discovery.traverse import direct_neighbors
        edges = graph.get("edges", [])
        neighbors = direct_neighbors(node_id, edges, relationship=relationship or None)

        if direction == "inbound":
            neighbors = [n for n in neighbors if n["direction"] == "inbound"]
        elif direction == "outbound":
            neighbors = [n for n in neighbors if n["direction"] == "outbound"]

        effective_limit = clamp_limit(limit)
        results = []
        for n in neighbors[:effective_limit]:
            node = nodes_map.get(n["nodeId"], {})
            results.append({
                "nodeId": n["nodeId"],
                "direction": n["direction"],
                "relationship": n["relationship"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
                "sourcePath": node.get("sourcePath", ""),
            })

        return {"nodeId": node_id, "neighbors": results, "total": len(neighbors)}

    # ── 9. Knowledge Graph Traversal ──

    def traverse_graph(self, *, node_id: str, depth: int = 2,
                       relationship: str = "", direction: str = "",
                       limit: int = DEFAULT_LIMIT) -> dict:
        if not node_id:
            raise InvalidRequest("node_id required")
        if depth > MAX_TRAVERSAL_DEPTH:
            raise LimitExceeded(f"depth exceeds maximum ({MAX_TRAVERSAL_DEPTH})")
        depth = max(1, min(depth, MAX_TRAVERSAL_DEPTH))

        graph = self._load_graph()
        nodes_map = {n["id"]: n for n in graph.get("nodes", [])}
        if node_id not in nodes_map:
            raise NotFound(f"node not found: {node_id}")

        from semantic_discovery.traverse import breadth_first_traverse
        edges = graph.get("edges", [])
        traversal = breadth_first_traverse(node_id, edges, depth=depth, relationship=relationship or None)

        if direction == "inbound":
            traversal = [t for t in traversal if t["direction"] == "inbound"]
        elif direction == "outbound":
            traversal = [t for t in traversal if t["direction"] == "outbound"]

        effective_limit = clamp_limit(limit)
        results = []
        for t in traversal[:effective_limit]:
            node = nodes_map.get(t["nodeId"], {})
            results.append({
                "nodeId": t["nodeId"],
                "depth": t["depth"],
                "relationship": t["relationship"],
                "direction": t["direction"],
                "name": node.get("name", ""),
                "type": node.get("type", ""),
            })

        return {"startNode": node_id, "depth": depth, "results": results, "total": len(traversal)}

    # ── 10. Shortest Path ──

    def find_path(self, *, source_id: str, target_id: str, relationship: str = "") -> dict:
        if not source_id or not target_id:
            raise InvalidRequest("source_id and target_id required")

        graph = self._load_graph()
        nodes_map = {n["id"]: n for n in graph.get("nodes", [])}
        if source_id not in nodes_map:
            raise NotFound(f"source node not found: {source_id}")
        if target_id not in nodes_map:
            raise NotFound(f"target node not found: {target_id}")

        from semantic_discovery.traverse import find_shortest_path
        edges = graph.get("edges", [])
        path = find_shortest_path(source_id, target_id, edges)

        if path is None:
            return {"found": False, "path": [], "length": 0}

        path_nodes = []
        for nid in path:
            node = nodes_map.get(nid, {})
            path_nodes.append({"nodeId": nid, "name": node.get("name", ""), "type": node.get("type", "")})

        return {"found": True, "path": path_nodes, "length": len(path)}

    # ── 11. Semantic Search ──

    def search(self, *, query: str, type_filter: str = "", path_filter: str = "",
               relationship: str = "", exact: bool = False,
               case_sensitive: bool = False, limit: int = DEFAULT_LIMIT) -> dict:
        if not query or not query.strip():
            raise InvalidRequest("query required")

        index = self._load_discovery()
        graph_data = load_json_artifact(self._gen("knowledge-graph.json")) or {}
        edges = graph_data.get("edges", [])

        from semantic_discovery.query import tokenize_query
        from semantic_discovery.rank import rank_results, score_document, score_entity
        from semantic_discovery.traverse import direct_neighbors

        query_tokens = tokenize_query(query)
        results = []

        for doc in index.get("documents", []):
            score, matched_fields, reasons = score_document(
                doc, query, query_tokens,
                type_filter=type_filter or None, path_filter=path_filter or None)
            if score > 0:
                results.append({
                    "id": doc["id"], "type": doc.get("category", "document"),
                    "name": doc.get("title", ""), "sourcePath": doc.get("sourcePath", ""),
                    "score": score, "matchedFields": matched_fields, "reasons": reasons,
                })

        for entity in index.get("entities", []):
            score, matched_fields, reasons = score_entity(
                entity, query, query_tokens,
                type_filter=type_filter or None, path_filter=path_filter or None)
            if score > 0:
                node_id = entity.get("nodeId", "")
                neighbors = direct_neighbors(node_id, edges)
                related = [{"nodeId": n["nodeId"], "relationship": n["relationship"]} for n in neighbors[:3]]
                results.append({
                    "id": entity["id"], "type": entity.get("type", ""),
                    "name": entity.get("name", ""), "sourcePath": entity.get("sourcePath", ""),
                    "score": score, "matchedFields": matched_fields, "reasons": reasons,
                    "related": related,
                })

        results = rank_results(results)
        effective_limit = clamp_limit(limit)
        total = len(results)
        results = results[:effective_limit]
        return {"query": query, "results": results, "total": total}

    # ── 12. Search Explanation ──

    def explain_search(self, *, entity_id: str, query: str) -> dict:
        if not entity_id:
            raise InvalidRequest("entity_id required")
        if not query or not query.strip():
            raise InvalidRequest("query required")

        index = self._load_discovery()
        graph_data = load_json_artifact(self._gen("knowledge-graph.json")) or {}
        nodes_map = {n["id"]: n for n in graph_data.get("nodes", [])}
        edges = graph_data.get("edges", [])

        from semantic_discovery.query import tokenize_query
        from semantic_discovery.rank import score_document, score_entity
        from semantic_discovery.traverse import direct_neighbors

        query_tokens = tokenize_query(query)

        # Try as entity
        entity_entry = None
        for entity in index.get("entities", []):
            if entity.get("nodeId") == entity_id:
                entity_entry = entity
                break

        score, matched_fields, reasons = 0, [], []
        if entity_entry:
            score, matched_fields, reasons = score_entity(entity_entry, query, query_tokens)

        # Try as document
        node = nodes_map.get(entity_id, {})
        node_source = node.get("sourcePath", "")
        for doc in index.get("documents", []):
            if doc.get("sourcePath") == node_source:
                ds, df, dr = score_document(doc, query, query_tokens)
                if ds > score:
                    score, matched_fields, reasons = ds, df, dr
                break

        neighbors = direct_neighbors(entity_id, edges)

        return {
            "entityId": entity_id,
            "query": query,
            "node": node or None,
            "score": score,
            "matchedFields": matched_fields,
            "reasons": reasons,
            "neighbors": len(neighbors),
        }

    # ── 13. Repository File Metadata ──

    def get_repository_file(self, *, source_path: str, max_chars: int = MAX_EXCERPT_CHARS) -> dict:
        if not source_path:
            raise InvalidRequest("source_path required")

        resolved = validate_path(source_path, self.root)

        if not resolved.is_file():
            raise NotFound(f"file not found: {source_path}")

        normalized = normalize_path(source_path)
        if is_secret_like(normalized):
            from .errors import Forbidden
            raise Forbidden(f"access to '{normalized}' is blocked for security")

        result = {
            "path": normalized,
            "exists": True,
            "size": resolved.stat().st_size,
            "isText": is_text_file(normalized),
        }

        if is_text_file(normalized):
            effective_max = min(max_chars, MAX_EXCERPT_CHARS)
            try:
                content = resolved.read_text(encoding="utf-8", errors="replace")[:effective_max]
                result["excerpt"] = redact_sensitive_content(content)
                result["truncated"] = len(content) >= effective_max
            except OSError:
                result["excerpt"] = None
                result["truncated"] = False
        else:
            result["excerpt"] = None
            result["truncated"] = False

        return result

    # ── 14. Generated Artifact Status ──

    def list_generated_artifacts(self) -> dict:
        artifacts_list = [
            "skills.json", "skills.md",
            "repository-index.json", "repository-map.md",
            "memory-index.json", "memory-index.md",
            "knowledge-graph.json", "knowledge-graph.md",
            "discovery-index.json", "discovery-index.md",
            "dashboard.html", "dashboard-data.json",
        ]
        results = []
        for name in artifacts_list:
            results.append(artifact_status(self._gen(name)))
        return {"artifacts": results}

    # ── 15. Dashboard Status ──

    def get_dashboard_status(self) -> dict:
        html_path = self._gen("dashboard.html")
        data_path = self._gen("dashboard-data.json")
        data = load_json_artifact(data_path)
        return {
            "htmlPresent": html_path.is_file(),
            "dataPresent": data_path.is_file(),
            "generatedAt": data.get("generatedAt") if data else None,
            "generator": data.get("generator") if data else None,
            "schemaVersion": data.get("schemaVersion") if data else None,
        }

    # ── Phase 8: Continuous Learning and Agent Orchestration ──
    # All methods below are read-only. No approval-mutating operations are
    # exposed via the service/MCP layer — approvals stay CLI-only.

    def plan_task(self, *, task: str, project: str = "", workflow: str = "",
                  limit: int = DEFAULT_LIMIT, no_memory: bool = False, no_history: bool = False) -> dict:
        if not task or not task.strip():
            raise InvalidRequest("task required")
        from orchestration.planner import create_plan
        return create_plan(
            self.root, task, project=project or None, workflow_override=workflow or None,
            limit=clamp_limit(limit), no_memory=no_memory, no_history=no_history)

    def classify_task(self, *, task: str, project: str = "", workflow: str = "") -> dict:
        if not task or not task.strip():
            raise InvalidRequest("task required")
        from orchestration.router import classify_task as _classify_task
        return _classify_task(self.root, task, project=project or None, requested_workflow=workflow or None)

    def list_workflows(self) -> dict:
        from orchestration.workflow import build_workflow_registry
        return build_workflow_registry(self.root)

    def get_workflow(self, *, workflow_id: str) -> dict:
        if not workflow_id:
            raise InvalidRequest("workflow_id required")
        registry = self.list_workflows()
        for workflow in registry.get("workflows", []):
            if workflow["id"] == workflow_id:
                return workflow
        raise NotFound(f"workflow not found: {workflow_id}")

    def list_agents(self) -> dict:
        from orchestration.registry import build_agent_registry
        return build_agent_registry(self.root)

    def get_agent(self, *, agent_id: str) -> dict:
        if not agent_id:
            raise InvalidRequest("agent_id required")
        registry = self.list_agents()
        for agent in registry.get("agents", []):
            if agent["id"] == agent_id:
                return agent
        raise NotFound(f"agent not found: {agent_id}")

    def list_sessions(self, *, status: str = "", limit: int = DEFAULT_LIMIT, cursor: int = 0) -> dict:
        from orchestration.session import list_sessions as _list_sessions
        sessions = _list_sessions(self.root, status=status or None)
        return paginate(sessions, limit, cursor)

    def get_session(self, *, session_id: str) -> dict:
        if not session_id:
            raise InvalidRequest("session_id required")
        from orchestration.session import SessionError, get_session as _get_session
        try:
            return _get_session(self.root, session_id)
        except SessionError as exc:
            raise NotFound(str(exc)) from exc

    def list_pending_approvals(self, *, limit: int = DEFAULT_LIMIT, cursor: int = 0) -> dict:
        from orchestration.approvals import list_approvals
        approvals = list_approvals(self.root, status="pending")
        return paginate(approvals, limit, cursor)

    def list_memory_suggestions(self, *, status: str = "", limit: int = DEFAULT_LIMIT, cursor: int = 0) -> dict:
        from orchestration.memory_suggestions import list_suggestions
        suggestions = list_suggestions(self.root, status=status or None)
        return paginate(suggestions, limit, cursor)

    def get_knowledge_health(self) -> dict:
        from orchestration.knowledge_gaps import build_knowledge_health
        return build_knowledge_health(self.root, include_live=True)

    def list_review_due(self, *, days: int = 30, limit: int = DEFAULT_LIMIT, cursor: int = 0) -> dict:
        from orchestration.freshness import review_due
        items = review_due(self.root, days=days)
        return paginate(items, limit, cursor)

    def list_feedback(self, *, status: str = "", limit: int = DEFAULT_LIMIT, cursor: int = 0) -> dict:
        from orchestration.feedback import list_feedback as _list_feedback
        entries = _list_feedback(self.root, status=status or None)
        return paginate(entries, limit, cursor)

    def get_audit_summary(self) -> dict:
        from orchestration.audit import summary
        return summary(self.root)
