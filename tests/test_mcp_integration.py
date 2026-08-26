"""Comprehensive tests for Phase 6 MCP Integration Layer."""
import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ai_os_service import SERVICE_VERSION, MAX_TRAVERSAL_DEPTH, MAX_EXCERPT_CHARS
from ai_os_service.errors import (
    InvalidRequest, NotFound, Forbidden, PathRejected,
    LimitExceeded, MalformedArtifact, Unavailable, ServiceError,
)
from ai_os_service.pagination import clamp_limit, paginate
from ai_os_service.permissions import (
    validate_path, is_secret_like, is_text_file,
    normalize_path, redact_sensitive_content,
)
from ai_os_service.service import AiOsService
from ai_os_service.utils import artifact_status, load_json_artifact
from profile import registry as profile_registry
from mcp_server import MCP_PROTOCOL_VERSION, SERVER_NAME
from mcp_server.schemas import TOOLS, RESOURCES
from mcp_server.adapter import McpAdapter


# ============================================================
# Service Layer Tests
# ============================================================

class ServiceStatusTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_repository_status(self):
        result = self.svc.get_repository_status()
        self.assertEqual(result["serviceVersion"], SERVICE_VERSION)
        self.assertIn("artifacts", result)

    def test_validation_status(self):
        result = self.svc.get_validation_status()
        self.assertIn("allArtifactsPresent", result)
        self.assertIn("artifacts", result)

    def test_generated_artifacts_list(self):
        result = self.svc.list_generated_artifacts()
        self.assertIn("artifacts", result)
        self.assertGreater(len(result["artifacts"]), 0)
        for a in result["artifacts"]:
            self.assertIn("path", a)
            self.assertIn("exists", a)

    def test_dashboard_status(self):
        result = self.svc.get_dashboard_status()
        self.assertIn("htmlPresent", result)
        self.assertIn("dataPresent", result)


class ServiceSkillTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_list_skills(self):
        result = self.svc.list_skills()
        self.assertGreater(result["total"], 0)
        self.assertIn("items", result)

    def test_list_skills_with_path_filter(self):
        result = self.svc.list_skills(path=".agent/skills/personal/")
        for item in result["items"]:
            self.assertTrue(item["path"].startswith(".agent/skills/personal/"))

    def test_get_skill_by_id(self):
        result = self.svc.get_skill(skill_id="communication-skill")
        self.assertEqual(result["id"], "communication-skill")

    def test_get_skill_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_skill(skill_id="nonexistent-skill-xyz")

    def test_get_skill_no_input(self):
        with self.assertRaises(InvalidRequest):
            self.svc.get_skill()


class ServiceMemoryTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_list_memory_summaries(self):
        result = self.svc.list_memory_summaries()
        self.assertGreater(result["total"], 0)
        for item in result["items"]:
            self.assertIn("summary", item)
            self.assertNotIn("body", item)
            self.assertNotIn("content", item)

    def test_get_memory_summary(self):
        result = self.svc.get_memory_summary(memory_id="convention-documentation-structure-001")
        self.assertEqual(result["id"], "convention-documentation-structure-001")
        self.assertIn("summary", result)

    def test_get_memory_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_memory_summary(memory_id="nonexistent-xyz")

    def test_memory_no_full_content(self):
        result = self.svc.list_memory_summaries()
        for item in result["items"]:
            self.assertNotIn("body", item)
            self.assertNotIn("fullContent", item)


class ServiceGraphTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_get_node(self):
        result = self.svc.get_node(node_id="concept:validation")
        self.assertEqual(result["id"], "concept:validation")

    def test_get_node_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_node(node_id="nonexistent:node")

    def test_get_neighbors(self):
        result = self.svc.get_neighbors(node_id="concept:validation")
        self.assertGreater(result["total"], 0)
        self.assertIn("neighbors", result)

    def test_traverse_graph(self):
        result = self.svc.traverse_graph(node_id="concept:validation", depth=2)
        self.assertGreater(result["total"], 0)
        self.assertEqual(result["depth"], 2)

    def test_traverse_depth_exceeded(self):
        with self.assertRaises(LimitExceeded):
            self.svc.traverse_graph(node_id="concept:validation", depth=6)

    def test_find_path(self):
        result = self.svc.find_path(source_id="concept:validation", target_id="concept:workflow")
        self.assertIn("found", result)
        self.assertIn("path", result)

    def test_find_path_not_found_node(self):
        with self.assertRaises(NotFound):
            self.svc.find_path(source_id="nonexistent:a", target_id="concept:workflow")


class ServiceSearchTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_search(self):
        result = self.svc.search(query="knowledge graph")
        self.assertGreater(result["total"], 0)
        self.assertEqual(result["query"], "knowledge graph")
        for r in result["results"]:
            self.assertIn("score", r)
            self.assertIn("matchedFields", r)
            self.assertIn("reasons", r)

    def test_search_type_filter(self):
        result = self.svc.search(query="validation", type_filter="concept")
        for r in result["results"]:
            self.assertEqual(r["type"], "concept")

    def test_search_empty_query(self):
        with self.assertRaises(InvalidRequest):
            self.svc.search(query="")

    def test_explain_search(self):
        result = self.svc.explain_search(entity_id="concept:validation", query="validation")
        self.assertIn("score", result)
        self.assertIn("matchedFields", result)

    def test_deterministic_ordering(self):
        r1 = self.svc.search(query="knowledge graph")
        r2 = self.svc.search(query="knowledge graph")
        self.assertEqual([x["id"] for x in r1["results"]], [x["id"] for x in r2["results"]])


# ============================================================
# Security Tests
# ============================================================

class SecurityPathTests(unittest.TestCase):
    def test_path_traversal_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("../outside.txt", ROOT)

    def test_absolute_path_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("/etc/passwd", ROOT)

    def test_windows_absolute_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("C:\\Windows\\system32\\config", ROOT)

    def test_dot_env_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path(".env", ROOT)

    def test_env_local_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path(".env.local", ROOT)

    def test_private_key_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("keys/server.pem", ROOT)

    def test_certificate_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("certs/ca.pfx", ROOT)

    def test_git_dir_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path(".git/config", ROOT)

    def test_venv_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path(".venv/lib/site.py", ROOT)

    def test_node_modules_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("node_modules/pkg/index.js", ROOT)

    def test_pycache_rejected(self):
        with self.assertRaises(PathRejected):
            validate_path("__pycache__/mod.cpython.pyc", ROOT)

    def test_valid_path_accepted(self):
        result = validate_path("README.md", ROOT)
        self.assertTrue(result.is_absolute())

    def test_is_secret_like(self):
        self.assertTrue(is_secret_like(".env"))
        self.assertTrue(is_secret_like("keys/server.pem"))
        self.assertTrue(is_secret_like(".git/config"))
        self.assertFalse(is_secret_like("README.md"))

    def test_is_text_file(self):
        self.assertTrue(is_text_file("README.md"))
        self.assertTrue(is_text_file("config.json"))
        self.assertFalse(is_text_file("image.png"))
        self.assertFalse(is_text_file("archive.zip"))

    def test_normalize_path(self):
        self.assertEqual(normalize_path("a\\b\\c"), "a/b/c")

    def test_redact_sensitive_content(self):
        text = "api_key: sk_live_1234567890abcdef1234"
        result = redact_sensitive_content(text)
        self.assertIn("[REDACTED]", result)
        self.assertNotIn("sk_live_1234567890abcdef1234", result)


class SecurityServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_file_traversal_rejected(self):
        with self.assertRaises(PathRejected):
            self.svc.get_repository_file(source_path="../outside.txt")

    def test_secret_file_rejected(self):
        with self.assertRaises((PathRejected, Forbidden)):
            self.svc.get_repository_file(source_path=".env")

    def test_safe_file_works(self):
        result = self.svc.get_repository_file(source_path="README.md")
        self.assertTrue(result["exists"])
        self.assertIn("excerpt", result)
        self.assertLessEqual(len(result.get("excerpt", "")), MAX_EXCERPT_CHARS)

    def test_bounded_excerpt(self):
        result = self.svc.get_repository_file(source_path="README.md", max_chars=50)
        self.assertLessEqual(len(result.get("excerpt", "")), 50)

    def test_traversal_depth_enforcement(self):
        with self.assertRaises(LimitExceeded):
            self.svc.traverse_graph(node_id="concept:validation", depth=6)


# ============================================================
# Pagination Tests
# ============================================================

class PaginationTests(unittest.TestCase):
    def test_clamp_limit_default(self):
        self.assertEqual(clamp_limit(None), 20)
        self.assertEqual(clamp_limit(0), 20)
        self.assertEqual(clamp_limit(-1), 20)

    def test_clamp_limit_max(self):
        self.assertEqual(clamp_limit(200), 100)
        self.assertEqual(clamp_limit(50), 50)

    def test_paginate(self):
        items = list(range(50))
        result = paginate(items, 10, 0)
        self.assertEqual(len(result["items"]), 10)
        self.assertEqual(result["total"], 50)
        self.assertTrue(result["hasMore"])
        self.assertEqual(result["nextCursor"], 10)

    def test_paginate_last_page(self):
        items = list(range(5))
        result = paginate(items, 10, 0)
        self.assertEqual(len(result["items"]), 5)
        self.assertFalse(result["hasMore"])
        self.assertIsNone(result["nextCursor"])


# ============================================================
# MCP Registration Tests
# ============================================================

class McpRegistrationTests(unittest.TestCase):
    def test_expected_tool_count(self):
        self.assertEqual(len(TOOLS), 32)

    def test_expected_resource_count(self):
        self.assertEqual(len(RESOURCES), 17)

    def test_tools_have_schemas(self):
        for tool in TOOLS:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_resources_have_uris(self):
        for res in RESOURCES:
            self.assertIn("uri", res)
            self.assertTrue(res["uri"].startswith("ai-os://"))
            self.assertIn("name", res)
            self.assertIn("mimeType", res)

    def test_stable_tool_names(self):
        names = [t["name"] for t in TOOLS]
        self.assertEqual(names, sorted(set(names), key=names.index))  # no duplicates

    def test_stable_resource_uris(self):
        uris = [r["uri"] for r in RESOURCES]
        self.assertEqual(uris, sorted(set(uris), key=uris.index))  # no duplicates


# ============================================================
# MCP Adapter Tests
# ============================================================

class McpAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = McpAdapter(ROOT)

    def test_call_valid_tool(self):
        result = self.adapter.call_tool("ai_os_status", {})
        self.assertIn("result", result)

    def test_call_unknown_tool(self):
        result = self.adapter.call_tool("nonexistent_tool", {})
        self.assertIn("error", result)
        self.assertEqual(result["error"]["code"], "unknown_tool")

    def test_search_tool(self):
        result = self.adapter.call_tool("search_ai_os", {"query": "knowledge graph"})
        self.assertIn("result", result)
        self.assertGreater(result["result"]["total"], 0)

    def test_path_rejection_via_adapter(self):
        result = self.adapter.call_tool("get_repository_file", {"source_path": "../escape"})
        self.assertIn("error", result)
        self.assertEqual(result["error"]["error"], "path_rejected")

    def test_read_valid_resource(self):
        result = self.adapter.read_resource("ai-os://status")
        self.assertIn("result", result)
        self.assertEqual(result["result"]["uri"], "ai-os://status")

    def test_read_unknown_resource(self):
        result = self.adapter.read_resource("ai-os://nonexistent")
        self.assertIn("error", result)

    def test_deterministic_tool_output(self):
        r1 = self.adapter.call_tool("list_skills", {})
        r2 = self.adapter.call_tool("list_skills", {})
        self.assertEqual(r1, r2)


# ============================================================
# MCP Stdio Server Tests
# ============================================================

class McpStdioTests(unittest.TestCase):
    """Test actual stdio communication with the MCP server."""

    def _start_server(self):
        return subprocess.Popen(
            [sys.executable, str(ROOT / "scripts" / "mcp-server.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=str(ROOT),
        )

    def _send(self, proc, method, params=None, req_id=1):
        request = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params:
            request["params"] = params
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        return json.loads(line) if line else None

    def test_initialize_handshake(self):
        proc = self._start_server()
        try:
            resp = self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            self.assertIn("result", resp)
            self.assertEqual(resp["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
            self.assertEqual(resp["result"]["serverInfo"]["name"], SERVER_NAME)
        finally:
            proc.kill()

    def test_tools_list(self):
        proc = self._start_server()
        try:
            self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            resp = self._send(proc, "tools/list", {}, 2)
            tools = resp["result"]["tools"]
            self.assertEqual(len(tools), 32)
        finally:
            proc.kill()

    def test_resources_list(self):
        proc = self._start_server()
        try:
            self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            resp = self._send(proc, "resources/list", {}, 2)
            resources = resp["result"]["resources"]
            self.assertEqual(len(resources), 17)
        finally:
            proc.kill()

    def test_tool_call_success(self):
        proc = self._start_server()
        try:
            self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            resp = self._send(proc, "tools/call", {"name": "ai_os_status", "arguments": {}}, 2)
            self.assertIn("result", resp)
            self.assertNotIn("isError", resp.get("result", {}))
        finally:
            proc.kill()

    def test_unknown_method(self):
        proc = self._start_server()
        try:
            resp = self._send(proc, "nonexistent/method", {})
            self.assertIn("error", resp)
        finally:
            proc.kill()

    def test_malformed_request(self):
        proc = self._start_server()
        try:
            proc.stdin.write("{invalid json\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            resp = json.loads(line)
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], -32700)
        finally:
            proc.kill()

    def test_clean_shutdown(self):
        proc = self._start_server()
        try:
            self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            # MCP stdio shutdown: close stdin
            proc.stdin.close()
            proc.wait(timeout=5)
            self.assertEqual(proc.returncode, 0)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.fail("Server did not shut down cleanly after stdin close")

    def test_notifications_initialized(self):
        proc = self._start_server()
        try:
            self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            # Send notifications/initialized (notification, no id, no response)
            notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            proc.stdin.write(json.dumps(notification) + "\n")
            proc.stdin.flush()
            # Verify server is still alive by sending another request
            resp = self._send(proc, "ping", {}, 3)
            self.assertIn("result", resp)
        finally:
            proc.kill()

    def test_multiple_requests_per_session(self):
        proc = self._start_server()
        try:
            self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            resp1 = self._send(proc, "tools/list", {}, 2)
            resp2 = self._send(proc, "resources/list", {}, 3)
            resp3 = self._send(proc, "tools/call", {"name": "ai_os_status", "arguments": {}}, 4)
            self.assertIn("result", resp1)
            self.assertIn("result", resp2)
            self.assertIn("result", resp3)
        finally:
            proc.kill()

    def test_stdout_contains_only_protocol_messages(self):
        proc = self._start_server()
        try:
            resp = self._send(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
            # Every line on stdout must be valid JSON-RPC
            self.assertIn("jsonrpc", resp)
            self.assertEqual(resp["jsonrpc"], "2.0")
        finally:
            proc.kill()


class McpLauncherTests(unittest.TestCase):
    def test_resolve_root_falls_back_when_ai_os_home_invalid(self):
        spec = importlib.util.spec_from_file_location("mcp_server_entry", SCRIPTS / "mcp-server.py")
        mod = importlib.util.module_from_spec(spec)
        original = os.environ.get("AI_OS_HOME")
        os.environ["AI_OS_HOME"] = str(ROOT / "does-not-exist")
        try:
            spec.loader.exec_module(mod)
            self.assertEqual(mod.resolve_root(), ROOT)
        finally:
            if original is None:
                os.environ.pop("AI_OS_HOME", None)
            else:
                os.environ["AI_OS_HOME"] = original

    def test_ai_os_mcp_check_command(self):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(["mcp", "check"])

        self.assertEqual(code, 0)
        self.assertIn("Smoke test complete", stdout.getvalue())


# ============================================================
# Error Handling Tests
# ============================================================

class ErrorHandlingTests(unittest.TestCase):
    def test_service_error_to_dict(self):
        err = ServiceError("test_code", "test message", {"key": "val"})
        d = err.to_dict()
        self.assertEqual(d["error"], "test_code")
        self.assertEqual(d["message"], "test message")
        self.assertEqual(d["details"]["key"], "val")

    def test_malformed_artifact_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generated").mkdir()
            (root / "generated" / "skills.json").write_text("{broken", encoding="utf-8")
            svc = AiOsService(root)
            with self.assertRaises(Unavailable):
                svc.list_skills()

    def test_missing_artifact_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generated").mkdir()
            svc = AiOsService(root)
            with self.assertRaises(Unavailable):
                svc.list_skills()


# ============================================================
# Phase 8: Continuous Learning and Agent Orchestration
# ============================================================

class Phase8ToolRegistrationTests(unittest.TestCase):
    def test_new_tools_registered(self):
        names = {t["name"] for t in TOOLS}
        for expected in (
            "plan_task", "classify_task", "list_workflows", "get_workflow",
            "list_agents", "get_agent", "list_sessions", "get_session",
            "list_pending_approvals", "list_memory_suggestions",
            "get_knowledge_health", "list_review_due", "list_feedback",
            "get_audit_summary",
        ):
            self.assertIn(expected, names)

    def test_new_resources_registered(self):
        uris = {r["uri"] for r in RESOURCES}
        for expected in (
            "ai-os://agents", "ai-os://workflows", "ai-os://knowledge-health",
            "ai-os://sessions", "ai-os://approvals", "ai-os://memory-suggestions",
            "ai-os://review-due", "ai-os://audit-summary",
        ):
            self.assertIn(expected, uris)

    def test_every_new_tool_has_adapter_handler(self):
        adapter = McpAdapter(ROOT)
        for tool in TOOLS:
            self.assertTrue(hasattr(adapter, f"_tool_{tool['name']}"), tool["name"])

    def test_no_approval_mutating_tool_exposed(self):
        names = {t["name"] for t in TOOLS}
        for forbidden in ("approve_memory_suggestion", "reject_memory_suggestion",
                          "approve_approval", "reject_approval"):
            self.assertNotIn(forbidden, names)


class Phase8ServiceReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_plan_task_requires_task(self):
        with self.assertRaises(InvalidRequest):
            self.svc.plan_task(task="")

    def test_classify_task_is_deterministic(self):
        first = self.svc.classify_task(task="Fix the login bug")
        second = self.svc.classify_task(task="Fix the login bug")
        self.assertEqual(first, second)

    def test_list_agents_read_only(self):
        result = self.svc.list_agents()
        self.assertIn("agents", result)

    def test_get_agent_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_agent(agent_id="agent:does-not-exist")

    def test_list_workflows_read_only(self):
        result = self.svc.list_workflows()
        self.assertIn("workflows", result)

    def test_get_workflow_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_workflow(workflow_id="workflow:does-not-exist")

    def test_list_sessions_paginated_and_limited(self):
        result = self.svc.list_sessions(limit=1000)
        self.assertLessEqual(result["limit"], 100)

    def test_get_session_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_session(session_id="session-does-not-exist-001")

    def test_get_knowledge_health_read_only(self):
        result = self.svc.get_knowledge_health()
        self.assertIn("overallScore", result)

    def test_list_feedback_result_limit_enforced(self):
        result = self.svc.list_feedback(limit=99999)
        self.assertLessEqual(result["limit"], 100)

    def test_get_audit_summary_read_only(self):
        result = self.svc.get_audit_summary()
        self.assertIn("totalEvents", result)


class Phase8SessionRedactionTests(unittest.TestCase):
    def test_session_summary_has_no_transcript_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sys.path.insert(0, str(SCRIPTS))
            from orchestration.session import create_session
            create_session(root, "Investigate api_key=abcdefghijklmnopqrst12345 leak", plan={})
            svc = AiOsService(root)
            result = svc.list_sessions()
            self.assertEqual(len(result["items"]), 1)
            session = result["items"][0]
            self.assertNotIn("transcript", session)
            self.assertNotIn("abcdefghijklmnopqrst12345", json.dumps(session))


# ============================================================
# Phase 9: Professional Context and Work Intelligence (read-only)
# ============================================================

class Phase9ToolRegistrationTests(unittest.TestCase):
    def test_new_tools_registered(self):
        names = {t["name"] for t in TOOLS}
        for expected in ("get_professional_profile", "list_expertise", "get_work_activity_summary"):
            self.assertIn(expected, names)

    def test_every_new_tool_has_adapter_handler(self):
        adapter = McpAdapter(ROOT)
        for name in ("get_professional_profile", "list_expertise", "get_work_activity_summary"):
            self.assertTrue(hasattr(adapter, f"_tool_{name}"), name)

    def test_no_profile_mutating_tool_exposed(self):
        names = {t["name"] for t in TOOLS}
        for forbidden in ("switch_profile", "write_profile", "edit_profile", "sync_knowledge",
                           "create_profile", "approve_profile_switch", "force_refresh_profile"):
            self.assertNotIn(forbidden, names)

    def test_no_new_resources_registered_this_task_group(self):
        # design.md's Interfaces section lists Phase 9 MCP tools only, no
        # new resource URIs.
        self.assertEqual(len(RESOURCES), 17)

    def test_new_tool_schemas_well_formed(self):
        by_name = {t["name"]: t for t in TOOLS}
        for name in ("get_professional_profile", "list_expertise", "get_work_activity_summary"):
            tool = by_name[name]
            self.assertIn("description", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertEqual(tool["inputSchema"]["required"], [])


class Phase9ServiceRealRepoTests(unittest.TestCase):
    """Against the real repository's live profile/ state, whatever it
    currently is (empty or populated). Never mutates the real registry --
    these are read-only calls asserted against whichever state is actually
    present."""

    def setUp(self):
        self.svc = AiOsService(ROOT)

    def test_get_professional_profile_reflects_real_registry_state(self):
        result = self.svc.get_professional_profile()
        registry = profile_registry.load_registry(ROOT)
        active = profile_registry.active_profile(registry)
        if active is None:
            self.assertFalse(result["configured"])
            self.assertIsNone(result["profile"])
        else:
            self.assertTrue(result["configured"])
            self.assertEqual(result["profile"]["id"], active["id"])
            self.assertTrue(result["profile"]["active"])

    def test_list_expertise_reflects_real_registry_state(self):
        result = self.svc.list_expertise()
        registry = profile_registry.load_registry(ROOT)
        active = profile_registry.active_profile(registry)
        if active is None:
            self.assertFalse(result["configured"])
            self.assertEqual(result["expertise"]["items"], [])
        else:
            self.assertTrue(result["configured"])
            self.assertEqual(result["profileId"], active["id"])

    def test_get_work_activity_summary_structure(self):
        result = self.svc.get_work_activity_summary()
        self.assertIn("projects", result)
        self.assertIn("focusAreas", result)
        self.assertIn("activitySummary", result)

    def test_invalid_profile_id_rejected(self):
        with self.assertRaises(InvalidRequest):
            self.svc.get_professional_profile(profile_id="Not Valid!")

    def test_unknown_profile_id_not_found(self):
        with self.assertRaises(NotFound):
            self.svc.get_professional_profile(profile_id="does-not-exist")

    def test_deterministic_output(self):
        r1 = self.svc.get_work_activity_summary()
        r2 = self.svc.get_work_activity_summary()
        self.assertEqual(r1, r2)


class Phase9SyntheticFixtureTests(unittest.TestCase):
    """Synthetic temp-dir fixtures only -- never populates the real registry."""

    def _seed(self, root, records, expertise=None):
        gen = root / "generated"
        gen.mkdir(parents=True, exist_ok=True)
        (gen / "profile-index.json").write_text(json.dumps({
            "schemaVersion": "1.0.0", "recordCount": len(records), "records": records,
        }), encoding="utf-8")
        if expertise is not None:
            (root / "profile").mkdir(parents=True, exist_ok=True)
            for profile_id, data in expertise.items():
                (root / "profile" / f"{profile_id}.expertise.json").write_text(json.dumps(data), encoding="utf-8")

    def _record(self, profile_id, role="Senior IT Technical Support Analyst", team="IT Support", active=True):
        return {"id": profile_id, "path": f"profile/{profile_id}.md", "role": role, "team": team, "active": active}

    def _expertise_entry(self, entry_id="expertise-windows-11", name="Windows 11 Deployment", level="advanced"):
        return {
            "id": entry_id, "name": name, "level": level,
            "evidence": [{"type": "project", "ref": "windows-11-autopilot-deployment"}],
            "source": "user", "status": "approved",
            "createdAt": "2026-07-15T00:00:00Z", "updatedAt": "2026-07-15T00:00:00Z",
        }

    def test_active_profile_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary", active=True)])
            svc = AiOsService(root)
            result = svc.get_professional_profile()
            self.assertTrue(result["configured"])
            self.assertEqual(result["profile"]["id"], "primary")
            self.assertEqual(result["profile"]["role"], "Senior IT Technical Support Analyst")
            self.assertTrue(result["profile"]["active"])

    def test_specific_profile_id_returned_regardless_of_active_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary", active=True), self._record("secondary", role="Contractor", active=False)])
            svc = AiOsService(root)
            result = svc.get_professional_profile(profile_id="secondary")
            self.assertTrue(result["configured"])
            self.assertEqual(result["profile"]["id"], "secondary")
            self.assertFalse(result["profile"]["active"])

    def test_multiple_profiles_one_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary", active=True), self._record("secondary", active=False)])
            svc = AiOsService(root)
            result = svc.get_professional_profile()
            self.assertEqual(result["profile"]["id"], "primary")

    def test_expertise_entries_returned_for_active_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expertise_file = {
                "schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z",
                "entries": [self._expertise_entry()],
            }
            self._seed(root, [self._record("primary")], expertise={"primary": expertise_file})
            svc = AiOsService(root)
            result = svc.list_expertise()
            self.assertTrue(result["configured"])
            self.assertEqual(result["profileId"], "primary")
            items = result["expertise"]["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["name"], "Windows 11 Deployment")
            self.assertEqual(items[0]["level"], "advanced")
            self.assertEqual(items[0]["evidence"], [{"type": "project", "ref": "windows-11-autopilot-deployment"}])

    def test_expertise_level_restricted_to_fixed_enum(self):
        # Structural proof: the fixed enum is enforced by
        # scripts/profile/validate.py (Task 003), which this service method
        # reuses via validate_expertise_file -- not re-implemented here.
        from profile.schema import PROFICIENCY_LEVELS
        self.assertEqual(
            PROFICIENCY_LEVELS,
            ["foundational", "working", "proficient", "advanced", "lead"])

    def test_no_expertise_entries_returns_valid_empty_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary")])  # no expertise file at all
            svc = AiOsService(root)
            result = svc.list_expertise()
            self.assertTrue(result["configured"])
            self.assertEqual(result["expertise"]["items"], [])

    def test_missing_profile_index_raises_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generated").mkdir()
            svc = AiOsService(root)
            with self.assertRaises(Unavailable):
                svc.get_professional_profile()

    def test_invalid_profile_index_raises_malformed_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen = root / "generated"
            gen.mkdir()
            (gen / "profile-index.json").write_text(json.dumps({"schemaVersion": "1.0.0"}), encoding="utf-8")  # no "records"
            svc = AiOsService(root)
            with self.assertRaises(MalformedArtifact):
                svc.get_professional_profile()

    def test_malformed_expertise_file_raises_malformed_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary")])
            (root / "profile").mkdir(exist_ok=True)
            (root / "profile" / "primary.expertise.json").write_text("{not valid json", encoding="utf-8")
            svc = AiOsService(root)
            with self.assertRaises(MalformedArtifact):
                svc.list_expertise()

    def test_invalid_expertise_entry_raises_malformed_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_entry = self._expertise_entry(level="expert")  # not in the fixed enum
            expertise_file = {"schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z", "entries": [bad_entry]}
            self._seed(root, [self._record("primary")], expertise={"primary": expertise_file})
            svc = AiOsService(root)
            with self.assertRaises(MalformedArtifact):
                svc.list_expertise()

    def test_unresolved_evidence_never_drops_the_claim(self):
        # Phase 9 does not require evidence refs to resolve (design.md); this
        # service never dereferences or filters by resolution -- the claim
        # is always returned as authored.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = self._expertise_entry()
            entry["evidence"] = [{"type": "project", "ref": "some-project-that-does-not-exist-anywhere"}]
            expertise_file = {"schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z", "entries": [entry]}
            self._seed(root, [self._record("primary")], expertise={"primary": expertise_file})
            svc = AiOsService(root)
            result = svc.list_expertise()
            self.assertEqual(len(result["expertise"]["items"]), 1)

    def test_no_evidence_dereferencing_only_type_and_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expertise_file = {
                "schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z",
                "entries": [self._expertise_entry()],
            }
            self._seed(root, [self._record("primary")], expertise={"primary": expertise_file})
            svc = AiOsService(root)
            result = svc.list_expertise()
            evidence_entry = result["expertise"]["items"][0]["evidence"][0]
            self.assertEqual(set(evidence_entry), {"type", "ref"})

    def test_no_raw_prose_or_unrestricted_front_matter_in_profile_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary")])
            svc = AiOsService(root)
            result = svc.get_professional_profile()
            self.assertEqual(set(result["profile"]), {"id", "role", "team", "active"})

    def test_no_arbitrary_path_access(self):
        # profile_id is validated as a normalized identifier -- it cannot
        # contain '/', '..', or whitespace, so it can never be used to read
        # outside profile/<id>.expertise.json.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root, [self._record("primary")])
            svc = AiOsService(root)
            with self.assertRaises(InvalidRequest):
                svc.get_professional_profile(profile_id="../../etc/passwd")

    def test_deterministic_repeated_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expertise_file = {
                "schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z",
                "entries": [self._expertise_entry()],
            }
            self._seed(root, [self._record("primary")], expertise={"primary": expertise_file})
            svc = AiOsService(root)
            self.assertEqual(svc.get_professional_profile(), svc.get_professional_profile())
            self.assertEqual(svc.list_expertise(), svc.list_expertise())

    def test_no_prohibited_fixture_values_in_error_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_marker = "SECRET_PROHIBITED_VALUE_MARKER"
            bad_entry = self._expertise_entry(name=secret_marker, level="expert")  # invalid level
            expertise_file = {"schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z", "entries": [bad_entry]}
            self._seed(root, [self._record("primary")], expertise={"primary": expertise_file})
            svc = AiOsService(root)
            try:
                svc.list_expertise()
                self.fail("expected MalformedArtifact")
            except MalformedArtifact as exc:
                self.assertNotIn(secret_marker, str(exc))


class Phase9McpAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = McpAdapter(ROOT)

    def test_get_professional_profile_via_adapter(self):
        result = self.adapter.call_tool("get_professional_profile", {})
        self.assertIn("result", result)

    def test_list_expertise_via_adapter(self):
        result = self.adapter.call_tool("list_expertise", {})
        self.assertIn("result", result)

    def test_get_work_activity_summary_via_adapter(self):
        result = self.adapter.call_tool("get_work_activity_summary", {})
        self.assertIn("result", result)
        self.assertIn("projects", result["result"])

    def test_invalid_profile_id_via_adapter_fails_safely(self):
        result = self.adapter.call_tool("get_professional_profile", {"profile_id": "not valid"})
        self.assertIn("error", result)
        self.assertEqual(result["error"]["error"], "invalid_request")

    def test_deterministic_tool_output(self):
        r1 = self.adapter.call_tool("get_work_activity_summary", {})
        r2 = self.adapter.call_tool("get_work_activity_summary", {})
        self.assertEqual(r1, r2)


if __name__ == "__main__":
    unittest.main()
