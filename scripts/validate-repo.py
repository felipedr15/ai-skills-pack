#!/usr/bin/env python3
"""Validate AI OS repository structure and metadata."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_indexer_spec = importlib.util.spec_from_file_location("index_repository", ROOT / "scripts/index-repository.py")
if _indexer_spec is None or _indexer_spec.loader is None:
    raise RuntimeError("unable to load scripts/index-repository.py")
_indexer = importlib.util.module_from_spec(_indexer_spec)
_indexer_spec.loader.exec_module(_indexer)

failures = []
warnings = []
passes = []


def is_excluded_path(path: Path) -> bool:
    return _indexer.is_excluded(path)


def fail(message):
    failures.append(message)


def warn(message):
    warnings.append(message)


def ok(message):
    passes.append(message)


def parse_front_matter(path: Path):
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text:
        return {}
    block = text.split("\n---\n", 1)[0].splitlines()[1:]
    result = {}
    current = None
    for line in block:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            item = line.strip()
            if current and isinstance(result.get(current), list) and item.startswith("- "):
                result[current].append(item[2:].strip().strip('"').strip("'"))
            continue
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        value = raw.strip()
        if value == "":
            result[key] = []
        elif value in {"null", "~"}:
            result[key] = None
        elif value == "[]":
            result[key] = []
        else:
            result[key] = value.strip('"').strip("'")
        current = key
    return result


def validate_base_structure():
    roots = [
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "WORKFLOW.md",
        "ARCHITECTURE.md",
        "ROADMAP.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "SECURITY.md",
        "GOVERNANCE.md",
        "skills.json",
        "agents.json",
        "prompts.json",
        ".gitignore",
    ]
    dirs = [
        ".github",
        ".kiro",
        ".agent/skills",
        "agents",
        "prompts",
        "templates",
        "standards",
        "knowledge",
        "references",
        "scripts",
        "memory",
    ]
    for value in roots + dirs:
        (ok if (ROOT / value).exists() else fail)(f"exists: {value}")


def validate_registries():
    registries = {}
    for name in ["skills", "agents", "prompts"]:
        try:
            registries[name] = json.loads((ROOT / f"{name}.json").read_text(encoding="utf-8"))[name]
            ok(f"valid {name}.json")
        except Exception as exc:  # noqa: BLE001
            fail(f"invalid {name}.json: {exc}")
            registries[name] = []

    allowed_status = {"draft", "experimental", "stable", "deprecated", "archived"}
    required_skill_fields = {"id", "name", "path", "version", "status", "description", "triggers", "dependencies"}
    skill_ids = set()
    for skill in registries["skills"]:
        missing = sorted(required_skill_fields - set(skill))
        if missing:
            fail(f"skill {skill.get('id', '?')} missing {missing}")
            continue
        if skill["id"] in skill_ids:
            fail(f"duplicate skill id: {skill['id']}")
        skill_ids.add(skill["id"])
        if not re.fullmatch(r"\d+\.\d+\.\d+", str(skill["version"])):
            fail(f"invalid version: {skill['id']}")
        if skill["status"] not in allowed_status:
            fail(f"invalid status: {skill['id']}")
        path = ROOT / skill["path"]
        if not path.is_file():
            fail(f"missing skill path: {skill['path']}")
            continue
        metadata = parse_front_matter(path)
        required_meta = {
            "name",
            "id",
            "version",
            "description",
            "triggers",
            "inputs",
            "outputs",
            "dependencies",
            "status",
            "replaces",
            "deprecatedBy",
        }
        missing_meta = sorted(required_meta - set(metadata))
        if missing_meta:
            fail(f"skill metadata missing in {skill['id']}: {missing_meta}")
        for key in ("id", "name", "version", "status", "description"):
            if str(skill[key]) != metadata.get(key):
                fail(f"skill registry mismatch for {skill['id']}: {key}")
        if not (path.parent / "README.md").is_file():
            fail(f"missing skill README: {path.parent.relative_to(ROOT)}")

    for skill in registries["skills"]:
        for dependency in skill.get("dependencies", []):
            if dependency not in skill_ids:
                fail(f"invalid dependency {dependency} in {skill['id']}")

    required_agents = {
        "planner",
        "architect",
        "researcher",
        "builder",
        "reviewer",
        "qa",
        "documentation-writer",
        "security-reviewer",
        "deployment-manager",
        "project-manager",
    }
    required_prompts = {
        "plan",
        "specify",
        "design",
        "execute",
        "debug",
        "review",
        "qa",
        "research",
        "document",
        "deploy",
        "create-skill",
    }
    for kind, required in [("agents", required_agents), ("prompts", required_prompts)]:
        got = {row.get("id") for row in registries[kind]}
        for missing in sorted(required - got):
            fail(f"missing {kind[:-1]}: {missing}")
        for row in registries[kind]:
            if not (ROOT / row.get("path", "")).is_file():
                fail(f"missing registered path: {row.get('path')}")


def validate_templates_and_required_files():
    memory_contract = {
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        "ARCHITECTURE.md",
        "REQUIREMENTS.md",
        "DESIGN.md",
        "TASKS.md",
        "decisions.md",
        "HANDOFF.md",
        "SESSION.md",
        "TESTING.md",
        "KNOWN_ISSUES.md",
        "CHANGELOG.md",
        "ROADMAP.md",
        "RELEASE_NOTES.md",
        "RETROSPECTIVE.md",
    }
    for base in [ROOT / "templates/project-memory"] + list((ROOT / "templates/project-starters").iterdir()):
        if base.is_dir():
            for name in memory_contract:
                if not (base / name).is_file():
                    fail(f"missing project-memory file: {base.relative_to(ROOT)}/{name}")

    required_specs = {
        "README.md",
        "requirements.md",
        "design.md",
        "tasks.md",
        "testing-plan.md",
        "deployment-plan.md",
        "retrospective.md",
    }
    for name in required_specs:
        if not (ROOT / "templates/specifications" / name).is_file():
            fail(f"missing specification template: {name}")

    required_files = [
        ".kiro/steering/product.md",
        ".kiro/steering/structure.md",
        ".kiro/steering/technology.md",
        ".kiro/steering/workflow.md",
        ".kiro/specs/README.md",
        ".github/copilot-instructions.md",
        ".github/workflows/validate.yml",
        ".github/instructions/markdown.instructions.md",
        ".github/instructions/skills.instructions.md",
        ".github/instructions/prompts.instructions.md",
        ".github/instructions/specifications.instructions.md",
        ".github/instructions/templates.instructions.md",
        "standards/documentation.md",
        "standards/naming.md",
        "standards/git.md",
        "standards/testing.md",
        "standards/security.md",
        "standards/accessibility.md",
        "standards/code-review.md",
        "standards/release-management.md",
        "references/chatgpt.md",
        "references/claude.md",
        "references/codex.md",
        "references/copilot.md",
        "references/kiro.md",
        "references/v0.md",
        "references/vercel.md",
        "references/canva.md",
        "references/mcp.md",
        "references/workflow-examples.md",
        "scripts/validate-repo.py",
        "scripts/validate-markdown.ps1",
        "scripts/create-project.py",
        "scripts/list-skills.py",
        "scripts/generate-memory-index.py",
        "scripts/generate-knowledge-graph.py",
        "scripts/validate-knowledge-graph.py",
        "scripts/knowledge-build.py",
        "scripts/knowledge-validate.py",
        "scripts/knowledge-check.py",
        "scripts/memory-add.py",
        "scripts/memory-list.py",
        "scripts/memory-search.py",
        "scripts/memory-archive.py",
        "scripts/memory-promote.py",
        "scripts/validate-memory-security.py",
        "schemas/memory.schema.json",
        "generated/knowledge-graph.json",
        "generated/knowledge-graph.md",
    ]
    for path in required_files:
        if not (ROOT / path).is_file():
            fail(f"missing required file: {path}")


def validate_skills_registered_vs_actual():
    try:
        registry = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))["skills"]
    except Exception:  # noqa: BLE001
        return
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.glob(".agent/skills/**/SKILL.md")}
    registered = {row.get("path") for row in registry}
    for path in sorted(actual - registered):
        fail(f"unregistered skill: {path}")
    for path in sorted(registered - actual):
        fail(f"registered non-skill path: {path}")


def validate_markdown_and_links():
    for md in ROOT.rglob("*.md"):
        rel_path = md.relative_to(ROOT)
        if is_excluded_path(rel_path):
            continue
        data = md.read_bytes()
        rel = rel_path.as_posix()
        if not data.strip():
            fail(f"empty Markdown: {rel}")
        if data and not data.endswith(b"\n"):
            warn(f"missing final newline: {rel}")
        text = data.decode("utf-8", errors="replace")
        headings = [line.strip() for line in text.splitlines() if line.startswith("#")]
        for first, second in zip(headings, headings[1:]):
            if first == second:
                warn(f"duplicate adjacent heading: {rel}: {first}")
        pattern = r"\[[^]]*\]\((?!https?://|mailto:|#)([^)]+)\)"
        for target in re.findall(pattern, text):
            clean = target.split("#", 1)[0].replace("%20", " ")
            if clean and not (md.parent / clean).resolve().exists():
                warn(f"broken relative link: {rel} -> {target}")


def validate_secret_patterns():
    secret = re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{16,}")
    text_suffixes = {".md", ".json", ".yml", ".yaml", ".py", ".ps1", ".txt"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        rel_path = path.relative_to(ROOT)
        if is_excluded_path(rel_path):
            continue
        if secret.search(path.read_text(encoding="utf-8", errors="ignore")):
            fail(f"possible secret: {rel_path}")


def validate_folder_readmes():
    major = [
        "agents",
        "prompts",
        "templates",
        "templates/project-memory",
        "templates/specifications",
        "templates/project-starters",
        "templates/memory",
        "standards",
        "knowledge",
        "references",
        "scripts",
        "scripts/knowledge_graph",
        ".kiro",
        ".kiro/steering",
        ".kiro/specs",
        ".github",
        ".github/instructions",
        ".github/workflows",
        "memory",
        "memory/permanent",
        "memory/permanent/conventions",
        "memory/permanent/preferences",
        "memory/permanent/principles",
        "memory/projects",
        "memory/sessions",
        "memory/decisions",
        "memory/lessons",
        "memory/archive",
    ]
    for folder in major:
        if not (ROOT / folder / "README.md").is_file():
            fail(f"missing major folder README: {folder}")


def validate_memory_engine():
    schema_path = ROOT / "schemas/memory.schema.json"
    if schema_path.is_file():
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
            ok("valid schemas/memory.schema.json")
        except Exception as exc:  # noqa: BLE001
            fail(f"invalid schemas/memory.schema.json: {exc}")

    registry_path = ROOT / "memory/registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        fail(f"invalid memory/registry.json: {exc}")
        return

    records = registry.get("records")
    if not isinstance(records, list):
        fail("memory/registry.json: records must be a list")
        return

    allowed_types = {"convention", "preference", "principle", "project", "session", "decision", "lesson"}
    allowed_scopes = {"global", "project", "session"}
    allowed_status = {"active", "proposed", "archived", "superseded"}
    allowed_sensitivity = {"public", "internal", "restricted"}
    allowed_retention = {"permanent", "project", "temporary", "archive"}

    required_registry_fields = {
        "id",
        "title",
        "type",
        "scope",
        "project",
        "status",
        "path",
        "tags",
        "sensitivity",
        "retention",
    }

    ids = set()
    source_ids = set()
    memory_files = [
        path for path in (ROOT / "memory").rglob("*.md") if path.name.lower() != "readme.md"
    ]

    for row in records:
        missing = sorted(required_registry_fields - set(row))
        if missing:
            fail(f"memory/registry.json: record {row.get('id', '?')} missing {missing}")
            continue
        if row["id"] in ids:
            fail(f"memory/registry.json: duplicate id {row['id']}")
        ids.add(row["id"])
        if row["type"] not in allowed_types:
            fail(f"memory/registry.json: invalid type for {row['id']}")
        if row["scope"] not in allowed_scopes:
            fail(f"memory/registry.json: invalid scope for {row['id']}")
        if row["status"] not in allowed_status:
            fail(f"memory/registry.json: invalid status for {row['id']}")
        if row["sensitivity"] not in allowed_sensitivity:
            fail(f"memory/registry.json: invalid sensitivity for {row['id']}")
        if row["retention"] not in allowed_retention:
            fail(f"memory/registry.json: invalid retention for {row['id']}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(row["id"])):
            fail(f"memory/registry.json: invalid id format for {row['id']}")
        path = ROOT / row["path"]
        if not path.is_file():
            fail(f"memory/registry.json: missing content path {row['path']}")
        if row["status"] == "archived" and not row["path"].startswith("memory/archive/"):
            fail(f"memory/registry.json: archived record not in archive folder {row['id']}")

    metadata_by_id = {}
    for path in sorted(memory_files, key=lambda item: item.relative_to(ROOT).as_posix()):
        rel = path.relative_to(ROOT).as_posix()
        metadata = parse_front_matter(path)
        required_fields = {
            "id",
            "title",
            "type",
            "scope",
            "project",
            "status",
            "created",
            "updated",
            "source",
            "summary",
            "tags",
            "related",
            "sensitivity",
            "retention",
            "contentPath",
        }
        missing = sorted(required_fields - set(metadata))
        if missing:
            fail(f"{rel}: missing memory metadata fields {missing}")
            continue
        if metadata["type"] not in allowed_types:
            fail(f"{rel}: invalid type {metadata['type']}")
        if metadata["scope"] not in allowed_scopes:
            fail(f"{rel}: invalid scope {metadata['scope']}")
        if metadata["status"] not in allowed_status:
            fail(f"{rel}: invalid status {metadata['status']}")
        if metadata["sensitivity"] not in allowed_sensitivity:
            fail(f"{rel}: invalid sensitivity {metadata['sensitivity']}")
        if metadata["retention"] not in allowed_retention:
            fail(f"{rel}: invalid retention {metadata['retention']}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(metadata["created"])):
            fail(f"{rel}: invalid created date")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(metadata["updated"])):
            fail(f"{rel}: invalid updated date")
        if not isinstance(metadata.get("tags"), list):
            fail(f"{rel}: tags must be a list")
        if not isinstance(metadata.get("related"), list):
            fail(f"{rel}: related must be a list")
        content_path = str(metadata["contentPath"])
        if content_path != rel:
            fail(f"{rel}: contentPath mismatch ({content_path})")
        source_ids.add(metadata["id"])
        metadata_by_id[metadata["id"]] = metadata
        if metadata["status"] == "archived" and not rel.startswith("memory/archive/"):
            fail(f"{rel}: archived records must be stored in memory/archive/")

    for row in records:
        if row["id"] not in source_ids:
            fail(f"memory/registry.json: id missing source record {row['id']}")

    for source_id in source_ids:
        if source_id not in ids:
            fail(f"memory source missing registry entry: {source_id}")

    for metadata in metadata_by_id.values():
        for related in metadata.get("related", []):
            if related not in source_ids:
                fail(f"{metadata['contentPath']}: broken related-memory reference: {related}")


def main():
    validate_base_structure()
    validate_registries()
    validate_templates_and_required_files()
    validate_skills_registered_vs_actual()
    validate_markdown_and_links()
    validate_secret_patterns()
    validate_folder_readmes()
    validate_memory_engine()

    for message in passes:
        print("PASS", message)
    for message in warnings:
        print("WARNING", message)
    for message in failures:
        print("FAIL", message)
    print(f"\nSummary: {len(passes)} PASS, {len(warnings)} WARNING, {len(failures)} FAIL")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
