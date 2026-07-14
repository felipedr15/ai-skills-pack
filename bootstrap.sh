#!/usr/bin/env bash
# AI OS Bootstrap - macOS/Linux wrapper
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Install Python 3.10+ first." >&2
    exit 1
fi

exec python3 "$ROOT/scripts/ai-os.py" bootstrap "$@"
