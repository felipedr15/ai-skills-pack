# GitHub Workflows

`validate.yml` defines **AI OS CI**. It runs on pushes to `main`, pull requests into `main`, and manual `workflow_dispatch` runs.

The workflow uses read-only repository permissions and does not deploy, publish, tag, or create releases.

Jobs:

- Repository Validation: runs `python scripts/validate-all.py`.
- Unit Tests: runs `python -m unittest discover -s tests -v`.
- MCP Smoke Tests: runs `python scripts/ai-os.py mcp check`.
- Release Readiness: runs `python scripts/ai-os.py release-check`.
- Diff Hygiene: runs `git diff --check`.

Python is pinned to 3.12 for v1.0 CI so interpreter upgrades are intentional.

[Back to AI OS](../../README.md)
