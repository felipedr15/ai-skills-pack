"""MCP adapter that maps MCP tool calls to the AI OS service layer."""
from __future__ import annotations

from pathlib import Path

from ai_os_service.errors import ServiceError
from ai_os_service.service import AiOsService

from .schemas import RESOURCES


class McpAdapter:
    """Adapts MCP tool/resource requests to the AI OS service layer."""

    def __init__(self, root: Path):
        self.service = AiOsService(root)
        self.root = root

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Dispatch a tool call to the service layer."""
        try:
            handler = getattr(self, f"_tool_{name}", None)
            if handler is None:
                return {"error": {"code": "unknown_tool", "message": f"unknown tool: {name}"}}
            return {"result": handler(arguments)}
        except ServiceError as exc:
            return {"error": exc.to_dict()}
        except Exception as exc:
            return {"error": {"code": "internal_error", "message": "an internal error occurred"}}

    def read_resource(self, uri: str) -> dict:
        """Read a resource by URI."""
        try:
            handler = self._resource_handlers().get(uri)
            if handler is None:
                return {"error": {"code": "not_found", "message": f"unknown resource: {uri}"}}
            content, mime_type = handler()
            return {"result": {"uri": uri, "content": content, "mimeType": mime_type}}
        except ServiceError as exc:
            return {"error": exc.to_dict()}
        except Exception:
            return {"error": {"code": "internal_error", "message": "an internal error occurred"}}

    # ── Tool Handlers ──

    def _tool_ai_os_status(self, args: dict) -> dict:
        return self.service.get_repository_status()

    def _tool_search_ai_os(self, args: dict) -> dict:
        return self.service.search(
            query=args.get("query", ""),
            type_filter=args.get("type", ""),
            path_filter=args.get("path", ""),
            relationship=args.get("relationship", ""),
            exact=args.get("exact", False),
            case_sensitive=args.get("case_sensitive", False),
            limit=args.get("limit", 20),
        )

    def _tool_explain_search_result(self, args: dict) -> dict:
        return self.service.explain_search(
            entity_id=args.get("entity_id", ""),
            query=args.get("query", ""),
        )

    def _tool_get_entity(self, args: dict) -> dict:
        return self.service.get_node(node_id=args.get("entity_id", ""))

    def _tool_get_related_entities(self, args: dict) -> dict:
        return self.service.get_neighbors(
            node_id=args.get("entity_id", ""),
            relationship=args.get("relationship", ""),
            direction=args.get("direction", ""),
            limit=args.get("limit", 20),
        )

    def _tool_traverse_knowledge_graph(self, args: dict) -> dict:
        return self.service.traverse_graph(
            node_id=args.get("entity_id", ""),
            depth=args.get("depth", 2),
            relationship=args.get("relationship", ""),
            direction=args.get("direction", ""),
            limit=args.get("limit", 20),
        )

    def _tool_find_knowledge_path(self, args: dict) -> dict:
        return self.service.find_path(
            source_id=args.get("source_id", ""),
            target_id=args.get("target_id", ""),
            relationship=args.get("relationship", ""),
        )

    def _tool_list_skills(self, args: dict) -> dict:
        return self.service.list_skills(
            platform=args.get("platform", ""),
            tool=args.get("tool", ""),
            category=args.get("category", ""),
            path=args.get("path", ""),
            limit=args.get("limit", 20),
            cursor=args.get("cursor", 0),
        )

    def _tool_get_skill(self, args: dict) -> dict:
        return self.service.get_skill(
            skill_id=args.get("skill_id", ""),
            source_path=args.get("source_path", ""),
        )

    def _tool_list_memory_summaries(self, args: dict) -> dict:
        return self.service.list_memory_summaries(
            project=args.get("project", ""),
            category=args.get("category", ""),
            source=args.get("source", ""),
            limit=args.get("limit", 20),
            cursor=args.get("cursor", 0),
        )

    def _tool_get_memory_summary(self, args: dict) -> dict:
        return self.service.get_memory_summary(memory_id=args.get("memory_id", ""))

    def _tool_get_repository_file(self, args: dict) -> dict:
        return self.service.get_repository_file(
            source_path=args.get("source_path", ""),
            max_chars=args.get("max_chars", 2000),
        )

    def _tool_get_validation_status(self, args: dict) -> dict:
        return self.service.get_validation_status()

    def _tool_list_generated_artifacts(self, args: dict) -> dict:
        return self.service.list_generated_artifacts()

    def _tool_get_dashboard_status(self, args: dict) -> dict:
        return self.service.get_dashboard_status()

    # ── Phase 8: Continuous Learning and Agent Orchestration ──
    # Read-only. No approval-mutating tool is registered here by design.

    def _tool_plan_task(self, args: dict) -> dict:
        return self.service.plan_task(
            task=args.get("task", ""),
            project=args.get("project", ""),
            workflow=args.get("workflow", ""),
            limit=args.get("limit", 20),
            no_memory=args.get("no_memory", False),
            no_history=args.get("no_history", False),
        )

    def _tool_classify_task(self, args: dict) -> dict:
        return self.service.classify_task(
            task=args.get("task", ""),
            project=args.get("project", ""),
            workflow=args.get("workflow", ""),
        )

    def _tool_list_workflows(self, args: dict) -> dict:
        return self.service.list_workflows()

    def _tool_get_workflow(self, args: dict) -> dict:
        return self.service.get_workflow(workflow_id=args.get("workflow_id", ""))

    def _tool_list_agents(self, args: dict) -> dict:
        return self.service.list_agents()

    def _tool_get_agent(self, args: dict) -> dict:
        return self.service.get_agent(agent_id=args.get("agent_id", ""))

    def _tool_list_sessions(self, args: dict) -> dict:
        return self.service.list_sessions(
            status=args.get("status", ""), limit=args.get("limit", 20), cursor=args.get("cursor", 0))

    def _tool_get_session(self, args: dict) -> dict:
        return self.service.get_session(session_id=args.get("session_id", ""))

    def _tool_list_pending_approvals(self, args: dict) -> dict:
        return self.service.list_pending_approvals(limit=args.get("limit", 20), cursor=args.get("cursor", 0))

    def _tool_list_memory_suggestions(self, args: dict) -> dict:
        return self.service.list_memory_suggestions(
            status=args.get("status", ""), limit=args.get("limit", 20), cursor=args.get("cursor", 0))

    def _tool_get_knowledge_health(self, args: dict) -> dict:
        return self.service.get_knowledge_health()

    def _tool_list_review_due(self, args: dict) -> dict:
        return self.service.list_review_due(
            days=args.get("days", 30), limit=args.get("limit", 20), cursor=args.get("cursor", 0))

    def _tool_list_feedback(self, args: dict) -> dict:
        return self.service.list_feedback(
            status=args.get("status", ""), limit=args.get("limit", 20), cursor=args.get("cursor", 0))

    def _tool_get_audit_summary(self, args: dict) -> dict:
        return self.service.get_audit_summary()

    # ── Phase 9: Professional Context (read-only) ──
    # No profile-mutating tool (create/edit/switch, sync-knowledge,
    # force-refresh, approval actions) is registered here by design.

    def _tool_get_professional_profile(self, args: dict) -> dict:
        return self.service.get_professional_profile(profile_id=args.get("profile_id", ""))

    def _tool_list_expertise(self, args: dict) -> dict:
        return self.service.list_expertise(
            profile_id=args.get("profile_id", ""), limit=args.get("limit", 20), cursor=args.get("cursor", 0))

    def _tool_get_work_activity_summary(self, args: dict) -> dict:
        return self.service.get_work_activity_summary()

    # ── Resource Handlers ──

    def _resource_handlers(self) -> dict:
        return {
            "ai-os://status": self._res_status,
            "ai-os://architecture": self._res_architecture,
            "ai-os://repository-map": self._res_repository_map,
            "ai-os://skills": self._res_skills,
            "ai-os://memory-summary": self._res_memory_summary,
            "ai-os://knowledge-graph": self._res_knowledge_graph,
            "ai-os://discovery": self._res_discovery,
            "ai-os://dashboard": self._res_dashboard,
            "ai-os://validation": self._res_validation,
            "ai-os://agents": self._res_agents,
            "ai-os://workflows": self._res_workflows,
            "ai-os://knowledge-health": self._res_knowledge_health,
            "ai-os://sessions": self._res_sessions,
            "ai-os://approvals": self._res_approvals,
            "ai-os://memory-suggestions": self._res_memory_suggestions,
            "ai-os://review-due": self._res_review_due,
            "ai-os://audit-summary": self._res_audit_summary,
        }

    def _read_generated_md(self, name: str) -> tuple[str, str]:
        path = self.root / "generated" / name
        if not path.is_file():
            return f"# {name}\n\nNot available.\n", "text/markdown"
        return path.read_text(encoding="utf-8", errors="replace")[:8000], "text/markdown"

    def _res_status(self):
        import json
        return json.dumps(self.service.get_repository_status(), indent=2), "application/json"

    def _res_architecture(self):
        path = self.root / "docs" / "architecture" / "ARCHITECTURE.md"
        if not path.is_file():
            return "# Architecture\n\nNot available.\n", "text/markdown"
        return path.read_text(encoding="utf-8", errors="replace")[:8000], "text/markdown"

    def _res_repository_map(self):
        return self._read_generated_md("repository-map.md")

    def _res_skills(self):
        return self._read_generated_md("skills.md")

    def _res_memory_summary(self):
        return self._read_generated_md("memory-index.md")

    def _res_knowledge_graph(self):
        return self._read_generated_md("knowledge-graph.md")

    def _res_discovery(self):
        return self._read_generated_md("discovery-index.md")

    def _res_dashboard(self):
        import json
        return json.dumps(self.service.get_dashboard_status(), indent=2), "application/json"

    def _res_validation(self):
        import json
        return json.dumps(self.service.get_validation_status(), indent=2), "application/json"

    def _res_agents(self):
        return self._read_generated_md("agent-registry.md")

    def _res_workflows(self):
        return self._read_generated_md("workflow-registry.md")

    def _res_knowledge_health(self):
        import json
        return json.dumps(self.service.get_knowledge_health(), indent=2), "application/json"

    def _res_sessions(self):
        import json
        return json.dumps(self.service.list_sessions(limit=50), indent=2), "application/json"

    def _res_approvals(self):
        import json
        return json.dumps(self.service.list_pending_approvals(limit=50), indent=2), "application/json"

    def _res_memory_suggestions(self):
        import json
        return json.dumps(self.service.list_memory_suggestions(limit=50), indent=2), "application/json"

    def _res_review_due(self):
        import json
        return json.dumps(self.service.list_review_due(limit=50), indent=2), "application/json"

    def _res_audit_summary(self):
        import json
        return json.dumps(self.service.get_audit_summary(), indent=2), "application/json"
