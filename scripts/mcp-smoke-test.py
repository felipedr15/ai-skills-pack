#!/usr/bin/env python3
"""Smoke test for the AI OS MCP server over stdio."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "scripts" / "mcp-server.py"


def send_request(proc, method: str, params: dict = None, req_id: int = 1) -> dict:
    """Send a JSON-RPC request and read the response."""
    request = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params:
        request["params"] = params
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        return {"error": "no response"}
    return json.loads(line)


def send_notification(proc, method: str, params: dict = None):
    """Send a JSON-RPC notification (no id, no response expected)."""
    notification = {"jsonrpc": "2.0", "method": method}
    if params:
        notification["params"] = params
    proc.stdin.write(json.dumps(notification) + "\n")
    proc.stdin.flush()


def main() -> int:
    print("Starting MCP smoke test...")
    proc = subprocess.Popen(
        [sys.executable, str(SERVER_SCRIPT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(ROOT),
    )

    failures = []
    req_id = 0

    def check(label: str, response: dict, condition=None):
        nonlocal failures
        if "error" in response and "result" not in response:
            failures.append(f"FAIL {label}: {response.get('error')}")
            return False
        if condition and not condition(response):
            failures.append(f"FAIL {label}: unexpected response")
            return False
        print(f"  PASS {label}")
        return True

    try:
        # 1. Initialize
        req_id += 1
        resp = send_request(proc, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke-test", "version": "1.0.0"}}, req_id)
        check("initialize", resp, lambda r: "protocolVersion" in r.get("result", {}))

        # 1b. Send notifications/initialized (MCP lifecycle requirement)
        send_notification(proc, "notifications/initialized")
        # 2. Tool list
        req_id += 1
        resp = send_request(proc, "tools/list", {}, req_id)
        check("tools/list", resp, lambda r: len(r.get("result", {}).get("tools", [])) == 29)

        # 3. Resource list
        req_id += 1
        resp = send_request(proc, "resources/list", {}, req_id)
        check("resources/list", resp, lambda r: len(r.get("result", {}).get("resources", [])) == 17)

        # 4. ai_os_status
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "ai_os_status", "arguments": {}}, req_id)
        check("ai_os_status", resp)

        # 5. Semantic search
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "search_ai_os", "arguments": {"query": "knowledge graph"}}, req_id)
        check("search 'knowledge graph'", resp)

        # 6. Search with type filter
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "search_ai_os", "arguments": {"query": "validation", "type": "skill"}}, req_id)
        check("search type=skill", resp)

        # 7. Get entity
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_entity", "arguments": {"entity_id": "concept:validation"}}, req_id)
        check("get_entity", resp)

        # 8. Get related
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_related_entities", "arguments": {"entity_id": "concept:validation"}}, req_id)
        check("get_related_entities", resp)

        # 9. Traverse
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "traverse_knowledge_graph", "arguments": {"entity_id": "concept:validation", "depth": 2}}, req_id)
        check("traverse depth=2", resp)

        # 10. Shortest path
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "find_knowledge_path", "arguments": {"source_id": "concept:validation", "target_id": "concept:workflow"}}, req_id)
        check("find_knowledge_path", resp)

        # 11. List skills
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "list_skills", "arguments": {}}, req_id)
        check("list_skills", resp)

        # 12. List memory
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "list_memory_summaries", "arguments": {}}, req_id)
        check("list_memory_summaries", resp)

        # 13. Safe file lookup
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_repository_file", "arguments": {"source_path": "README.md"}}, req_id)
        check("get_repository_file (safe)", resp)

        # 14. Path traversal rejection
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_repository_file", "arguments": {"source_path": "../outside.txt"}}, req_id)
        content = json.loads(resp.get("result", {}).get("content", [{}])[0].get("text", "{}"))
        if content.get("error") == "path_rejected":
            print("  PASS path traversal rejected")
        else:
            failures.append("FAIL path traversal NOT rejected")

        # 15. Secret file rejection
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_repository_file", "arguments": {"source_path": ".env"}}, req_id)
        content = json.loads(resp.get("result", {}).get("content", [{}])[0].get("text", "{}"))
        if content.get("error") in ("path_rejected", "forbidden"):
            print("  PASS secret file rejected")
        else:
            failures.append("FAIL secret file NOT rejected")

        # 16. Depth > 5 rejection
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "traverse_knowledge_graph", "arguments": {"entity_id": "concept:validation", "depth": 6}}, req_id)
        content = json.loads(resp.get("result", {}).get("content", [{}])[0].get("text", "{}"))
        if content.get("error") == "limit_exceeded":
            print("  PASS depth > 5 rejected")
        else:
            failures.append("FAIL depth > 5 NOT rejected")

        # 17. Memory returns summaries only
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_memory_summary", "arguments": {"memory_id": "convention-documentation-structure-001"}}, req_id)
        content_text = resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
        mem_data = json.loads(content_text)
        if "body" not in mem_data and "content" not in mem_data and "summary" in mem_data:
            print("  PASS memory returns summary only")
        else:
            failures.append("FAIL memory exposes full content")

        # 17b. Phase 8: classify_task
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "classify_task", "arguments": {"task": "Fix the login bug"}}, req_id)
        check("classify_task", resp)

        # 17c. Phase 8: list_agents
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "list_agents", "arguments": {}}, req_id)
        check("list_agents", resp)

        # 17d. Phase 8: get_knowledge_health
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "get_knowledge_health", "arguments": {}}, req_id)
        check("get_knowledge_health", resp)

        # 17e. Phase 8: no approval-mutating tool is registered
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "approve_memory_suggestion", "arguments": {}}, req_id)
        content = json.loads(resp.get("result", {}).get("content", [{}])[0].get("text", "{}"))
        if content.get("code") == "unknown_tool":
            print("  PASS no approval-mutating tool exposed")
        else:
            failures.append("FAIL an approval-mutating tool appears to be exposed")

        # 17f. Phase 8: read ai-os://agents resource
        req_id += 1
        resp = send_request(proc, "resources/read", {"uri": "ai-os://agents"}, req_id)
        check("read ai-os://agents", resp)

        # 18. Unknown tool
        req_id += 1
        resp = send_request(proc, "tools/call", {"name": "nonexistent_tool", "arguments": {}}, req_id)
        content = json.loads(resp.get("result", {}).get("content", [{}])[0].get("text", "{}"))
        if content.get("code") == "unknown_tool" or resp.get("result", {}).get("isError"):
            print("  PASS unknown tool handled")
        else:
            failures.append("FAIL unknown tool not handled cleanly")

        # 19. Shutdown (MCP stdio: close stdin)
        proc.stdin.close()
        proc.wait(timeout=5)
        print("  PASS server shutdown (stdin closed)")

    except Exception as exc:
        failures.append(f"FAIL unexpected error: {exc}")
        proc.kill()

    print(f"\nSmoke test complete: {24 - len(failures)} PASS, {len(failures)} FAIL")
    for f in failures:
        print(f"  {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
