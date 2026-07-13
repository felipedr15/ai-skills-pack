#!/usr/bin/env python3
"""Run all AI OS validation without modifying repository files."""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".py", ".ps1", ".txt"}
SECRET = re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{16,}")

_indexer_spec = importlib.util.spec_from_file_location("index_repository", ROOT / "scripts/index-repository.py")
if _indexer_spec is None or _indexer_spec.loader is None:
    raise RuntimeError("unable to load scripts/index-repository.py")
_indexer = importlib.util.module_from_spec(_indexer_spec)
_indexer_spec.loader.exec_module(_indexer)


def is_excluded_path(path: Path) -> bool:
    return _indexer.is_excluded(path)


class Results:
    def __init__(self):
        self.passes = []
        self.warnings = []
        self.failures = []

    def pass_(self, message): self.passes.append(message)
    def warning(self, message): self.warnings.append(message)
    def fail(self, message): self.failures.append(message)

    def report(self):
        for message in self.passes: print("PASS", message)
        for message in self.warnings: print("WARNING", message)
        for message in self.failures: print("FAIL", message)
        print(f"\nSummary: {len(self.passes)} PASS, {len(self.warnings)} WARNING, {len(self.failures)} FAIL")
        return 1 if self.failures else 0


def run_command(results, label, command, env=None):
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, env=env)
    output = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    if completed.returncode:
        results.fail(f"{label} (exit {completed.returncode})" + (f"\n{output}" if output else ""))
    else:
        results.pass_(label)


def validate_json(results):
    files = sorted(path for path in ROOT.rglob("*.json") if not is_excluded_path(path.relative_to(ROOT)))
    for path in files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            results.fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
    if not any(message.startswith("invalid JSON") for message in results.failures):
        results.pass_(f"JSON validation ({len(files)} files)")


def validate_links(results):
    broken = []
    pattern = re.compile(r"\[[^]]*\]\((?!https?://|mailto:|#)([^)]+)\)")
    for path in sorted(ROOT.rglob("*.md")):
        if is_excluded_path(path.relative_to(ROOT)):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in pattern.findall(text):
            clean = target.split("#", 1)[0].replace("%20", " ")
            if clean and not (path.parent / clean).resolve().exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    if broken:
        for item in broken: results.fail(f"broken relative link: {item}")
    else:
        results.pass_("relative-link validation")


def validate_secrets(results):
    matches = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if is_excluded_path(path.relative_to(ROOT)):
            continue
        if SECRET.search(path.read_text(encoding="utf-8", errors="ignore")):
            matches.append(path.relative_to(ROOT))
    if matches:
        for path in matches: results.fail(f"possible secret pattern: {path}")
    else:
        results.pass_("secret-pattern validation")


def validate_templates(results):
    required = {"README.md", "AGENTS.md", "CLAUDE.md", "ARCHITECTURE.md", "REQUIREMENTS.md", "DESIGN.md", "TASKS.md", "HANDOFF.md", "TESTING.md"}
    failures = []
    for starter in sorted((ROOT / "templates/project-starters").iterdir()):
        if starter.is_dir():
            failures.extend(f"{starter.relative_to(ROOT)}/{name}" for name in sorted(required) if not (starter / name).is_file())
    if failures:
        for item in failures: results.fail(f"missing required template: {item}")
    else:
        results.pass_("required-template validation")


def main():
    results = Results()
    python = sys.executable
    run_command(results, "existing repository validation", [python, "scripts/validate-repo.py"])
    run_command(results, "skill registry and metadata/dependency/duplicate-ID validation", [python, "scripts/generate-skill-registry.py", "--check"])
    run_command(results, "memory index metadata/duplicate-ID/path/reference validation", [python, "scripts/generate-memory-index.py", "--check"])
    run_command(results, "knowledge graph generation/staleness validation", [python, "scripts/generate-knowledge-graph.py", "--check"])
    run_command(results, "knowledge graph structure validation", [python, "scripts/validate-knowledge-graph.py"])
    run_command(results, "memory security secret-pattern validation", [python, "scripts/validate-memory-security.py"])
    run_command(results, "repository index validation", [python, "scripts/index-repository.py", "--check"])
    run_command(results, "discovery index staleness validation", [python, "scripts/discovery-check.py"])
    run_command(results, "discovery index structure validation", [python, "scripts/discovery-validate.py"])
    run_command(results, "dashboard staleness validation", [python, "scripts/dashboard-check.py"])
    run_command(results, "dashboard structure validation", [python, "scripts/dashboard-validate.py"])
    run_command(results, "MCP smoke test", [python, "scripts/mcp-smoke-test.py"])
    validate_json(results)
    validate_links(results)
    validate_secrets(results)
    validate_templates(results)
    if os.environ.get("AI_OS_SKIP_TESTS") == "1":
        results.warning("unit tests skipped by AI_OS_SKIP_TESTS")
    else:
        env = dict(os.environ, AI_OS_SKIP_TESTS="1")
        run_command(results, "unit tests", [python, "-m", "unittest", "discover", "-s", "tests", "-v"], env=env)
    return results.report()


if __name__ == "__main__":
    raise SystemExit(main())
