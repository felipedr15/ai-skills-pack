#!/usr/bin/env python3
"""Start the AI OS MCP server over stdio transport."""
from __future__ import annotations

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

def resolve_root() -> Path:
    env_root = os.environ.get("AI_OS_HOME", "").strip()
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if (candidate / "VERSION").is_file() and (candidate / "scripts" / "mcp-server.py").is_file():
            return candidate
    return Path(__file__).resolve().parents[1]


ROOT = resolve_root()

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
