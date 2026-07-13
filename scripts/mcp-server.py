#!/usr/bin/env python3
"""Start the AI OS MCP server over stdio transport."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

ROOT = Path(__file__).resolve().parents[1]

from mcp_server.server import McpStdioServer


def main() -> int:
    server = McpStdioServer(ROOT)
    try:
        server.run()
    except (KeyboardInterrupt, EOFError):
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
