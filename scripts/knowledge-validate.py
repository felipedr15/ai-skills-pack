#!/usr/bin/env python3
"""Compatibility command for knowledge:validate equivalent."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    completed = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate-knowledge-graph.py")], cwd=ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
