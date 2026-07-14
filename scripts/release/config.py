"""Configuration management for AI OS."""
from __future__ import annotations

import json
from pathlib import Path

from .version import get_repo_root

CONFIG_SCHEMA_VERSION = "1.0.0"
EXAMPLE_CONFIG = "config/ai-os.example.json"
LOCAL_CONFIG = "config/ai-os.local.json"

DEFAULT_CONFIG = {
    "schemaVersion": CONFIG_SCHEMA_VERSION,
    "dashboard": {
        "host": "127.0.0.1",
        "port": 8080,
        "openBrowser": False,
    },
    "mcp": {
        "enabled": True,
        "readOnly": True,
        "maxSearchResults": 20,
        "maxTraversalDepth": 5,
        "maxExcerptChars": 2000,
    },
    "generation": {
        "regenerateOnBootstrap": True,
    },
    "validation": {
        "runTests": True,
    },
    "backup": {
        "directory": ".ai-os/backups",
    },
}

ALLOWED_SECTIONS = {"schemaVersion", "dashboard", "mcp", "generation", "validation", "backup"}
UNSAFE_HOSTS = {"0.0.0.0", "::"}


def load_config(root: Path | None = None) -> dict:
    """Load configuration with safe defaults, merging local overrides."""
    if root is None:
        root = get_repo_root()
    config = dict(DEFAULT_CONFIG)
    local_path = root / LOCAL_CONFIG
    if local_path.is_file():
        try:
            local = json.loads(local_path.read_text(encoding="utf-8"))
            if isinstance(local, dict):
                for key, value in local.items():
                    if key in ALLOWED_SECTIONS:
                        if isinstance(value, dict) and isinstance(config.get(key), dict):
                            config[key] = {**config[key], **value}
                        else:
                            config[key] = value
        except (OSError, json.JSONDecodeError):
            pass
    return config


def validate_config(config: dict) -> tuple[list[str], list[str]]:
    """Validate configuration. Returns (failures, warnings)."""
    failures: list[str] = []
    warnings: list[str] = []

    if config.get("schemaVersion") != CONFIG_SCHEMA_VERSION:
        failures.append(f"unsupported config schemaVersion: {config.get('schemaVersion')}")

    unknown = set(config.keys()) - ALLOWED_SECTIONS
    if unknown:
        warnings.append(f"unknown config keys: {sorted(unknown)}")

    dashboard = config.get("dashboard", {})
    if isinstance(dashboard, dict):
        host = dashboard.get("host", "127.0.0.1")
        if host in UNSAFE_HOSTS:
            failures.append(f"unsafe dashboard host: {host} (must bind to localhost)")
        port = dashboard.get("port", 8080)
        if not isinstance(port, int) or port < 1 or port > 65535:
            failures.append(f"invalid dashboard port: {port}")

    mcp = config.get("mcp", {})
    if isinstance(mcp, dict):
        if not mcp.get("readOnly", True):
            warnings.append("MCP readOnly is disabled — write tools may be exposed")

    return failures, warnings


def write_example_config(root: Path | None = None) -> None:
    """Write the example configuration file."""
    if root is None:
        root = get_repo_root()
    path = root / EXAMPLE_CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
