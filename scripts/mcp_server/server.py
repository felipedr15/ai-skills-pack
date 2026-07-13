"""MCP stdio server implementing JSON-RPC 2.0 transport.

Follows the MCP specification (2024-11-05):
- Newline-delimited JSON messages on stdin/stdout
- No embedded newlines in messages
- Only valid MCP messages on stdout
- Diagnostics/logs on stderr only
- Initialize -> notifications/initialized lifecycle
- EOF on stdin signals shutdown
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import MCP_PROTOCOL_VERSION, SERVER_NAME, SERVER_VERSION
from .adapter import McpAdapter
from .schemas import RESOURCES, TOOLS


class McpStdioServer:
    """MCP server using stdio transport (JSON-RPC 2.0).

    Complies with MCP specification 2024-11-05 stdio transport:
    - Reads JSON-RPC from stdin (newline-delimited)
    - Writes JSON-RPC to stdout (newline-delimited)
    - Writes diagnostics to stderr only
    - Handles initialize/notifications/initialized lifecycle
    - Processes multiple requests per session
    - Exits cleanly on EOF (stdin close)
    """

    def __init__(self, root: Path):
        self.adapter = McpAdapter(root)
        self.initialized = False
        self._log(f"MCP server starting (root: {root})")

    def _log(self, message: str):
        """Write diagnostic messages to stderr only (never stdout)."""
        sys.stderr.write(f"[ai-os-mcp] {message}\n")
        sys.stderr.flush()

    def run(self):
        """Main server loop. Reads until EOF on stdin."""
        self._log("Waiting for messages on stdin...")
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    self._send_error(None, -32700, "Parse error")
                    continue
                self._handle_request(request)
        except (KeyboardInterrupt, EOFError):
            pass
        self._log("Server shutting down (stdin closed or interrupted)")

    def _handle_request(self, request: dict):
        """Route a JSON-RPC request or notification."""
        if not isinstance(request, dict):
            self._send_error(None, -32600, "Invalid Request")
            return

        req_id = request.get("id")  # None for notifications
        method = request.get("method", "")
        params = request.get("params", {})

        # Notifications (no id) — no response sent
        if req_id is None:
            self._handle_notification(method, params)
            return

        # Requests (have id) — response required
        if method == "initialize":
            self._handle_initialize(req_id, params)
        elif method == "ping":
            self._send_result(req_id, {})
        elif method == "tools/list":
            self._handle_tools_list(req_id, params)
        elif method == "tools/call":
            self._handle_tools_call(req_id, params)
        elif method == "resources/list":
            self._handle_resources_list(req_id, params)
        elif method == "resources/read":
            self._handle_resources_read(req_id, params)
        else:
            self._send_error(req_id, -32601, f"Method not found: {method}")

    def _handle_notification(self, method: str, params: dict):
        """Handle notifications (no response sent)."""
        if method == "notifications/initialized":
            self._log("Client sent notifications/initialized")
        elif method == "cancelled":
            self._log(f"Request cancelled: {params.get('requestId')}")
        else:
            self._log(f"Unknown notification: {method}")

    def _handle_initialize(self, req_id, params: dict):
        """Handle the initialize request (MCP lifecycle phase 1)."""
        client_version = params.get("protocolVersion", "")
        client_info = params.get("clientInfo", {})
        self._log(f"Initialize from {client_info.get('name', 'unknown')} (protocol: {client_version})")

        self.initialized = True
        self._send_result(req_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        })

    def _handle_tools_list(self, req_id, params: dict):
        """Handle tools/list request."""
        self._send_result(req_id, {"tools": TOOLS})

    def _handle_tools_call(self, req_id, params: dict):
        """Handle tools/call request. Returns MCP content blocks."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        self._log(f"Tool call: {name}")
        result = self.adapter.call_tool(name, arguments)

        if "error" in result:
            self._send_result(req_id, {
                "content": [{"type": "text", "text": json.dumps(result["error"])}],
                "isError": True,
            })
        else:
            self._send_result(req_id, {
                "content": [{"type": "text", "text": json.dumps(result["result"], indent=2)}],
            })

    def _handle_resources_list(self, req_id, params: dict):
        """Handle resources/list request."""
        self._send_result(req_id, {"resources": RESOURCES})

    def _handle_resources_read(self, req_id, params: dict):
        """Handle resources/read request. Returns MCP resource contents."""
        uri = params.get("uri", "")
        self._log(f"Resource read: {uri}")
        result = self.adapter.read_resource(uri)

        if "error" in result:
            self._send_error(req_id, -32602, result["error"].get("message", "resource error"))
        else:
            r = result["result"]
            self._send_result(req_id, {
                "contents": [{
                    "uri": r["uri"],
                    "mimeType": r["mimeType"],
                    "text": r["content"],
                }],
            })

    def _send_result(self, req_id, result: dict):
        """Send a JSON-RPC success response."""
        response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._write(response)

    def _send_error(self, req_id, code: int, message: str, data: dict | None = None):
        """Send a JSON-RPC error response."""
        error_obj: dict = {"code": code, "message": message}
        if data:
            error_obj["data"] = data
        response = {"jsonrpc": "2.0", "id": req_id, "error": error_obj}
        self._write(response)

    def _write(self, data: dict):
        """Write a single JSON-RPC message to stdout (newline-delimited, no embedded newlines)."""
        # MCP spec: messages delimited by newlines, MUST NOT contain embedded newlines
        line = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
