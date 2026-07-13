"""Render dashboard HTML and data artifacts."""
from __future__ import annotations

import json
from pathlib import Path

from .template import DASHBOARD_HTML


def render_dashboard_html(data: dict) -> str:
    """Render the dashboard HTML with embedded data."""
    data_json = json.dumps(data, indent=None, ensure_ascii=False)
    return DASHBOARD_HTML.replace("__DASHBOARD_DATA__", data_json)


def render_dashboard_data_json(data: dict) -> str:
    """Render the dashboard data as formatted JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_dashboard(data: dict, root: Path) -> None:
    """Write dashboard artifacts to generated/."""
    out_html = root / "generated" / "dashboard.html"
    out_json = root / "generated" / "dashboard-data.json"
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_dashboard_html(data), encoding="utf-8", newline="\n")
    out_json.write_text(render_dashboard_data_json(data), encoding="utf-8", newline="\n")
