#!/usr/bin/env python3
"""Create an AI OS project from a starter without installing or committing."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTERS = ROOT / "templates/project-starters"
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".js", ".ts", ".tsx", ".html", ".css", ".ps1", ".sh"}


def available_starters(root=STARTERS):
    return sorted(path.name for path in root.iterdir() if path.is_dir()) if root.is_dir() else []


def project_yaml(name, project_type, owner, technology, status):
    def quote(value):
        return json.dumps(str(value), ensure_ascii=False)
    return "\n".join((
        "schemaVersion: 1.0.0", f"name: {quote(name)}", f"type: {quote(project_type)}",
        f"owner: {quote(owner)}", f"technology: {quote(technology)}", f"status: {quote(status)}", "",
    ))


def create_project(name, project_type, destination, owner="[OWNER]", technology="[TECHNOLOGY]", status="planning", purpose="[PROJECT PURPOSE]", force=False, init_git=False, starters_root=STARTERS):
    source = starters_root / project_type
    if not source.is_dir():
        raise ValueError(f"unknown project type '{project_type}'; available: {', '.join(available_starters(starters_root))}")
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()) and not force:
        raise ValueError("destination is non-empty; use --force to overwrite starter-owned files")
    destination.mkdir(parents=True, exist_ok=True)
    replacements = {"[PROJECT NAME]": name, "[PROJECT PURPOSE]": purpose, "[OWNER]": owner, "[TECHNOLOGY]": technology, "[CURRENT STATUS]": status}
    created = []
    for source_path in sorted(source.rglob("*"), key=lambda path: path.relative_to(source).as_posix()):
        if not source_path.is_file():
            continue
        target = destination / source_path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            raise ValueError(f"would overwrite existing file: {target}")
        if source_path.suffix.lower() in TEXT_SUFFIXES or source_path.name in {"Dockerfile", "Makefile"}:
            text = source_path.read_text(encoding="utf-8")
            for placeholder, value in replacements.items():
                text = text.replace(placeholder, value)
            target.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copy2(source_path, target)
        created.append(target)
    manifest = destination / "project.yaml"
    if manifest.exists() and not force:
        raise ValueError(f"would overwrite existing file: {manifest}")
    manifest.write_text(project_yaml(name, project_type, owner, technology, status), encoding="utf-8", newline="\n")
    created.append(manifest)
    if init_git:
        if (destination / ".git").exists():
            raise ValueError("destination already contains a Git repository")
        try:
            subprocess.run(["git", "init"], cwd=destination, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"git initialization failed: {exc}") from exc
    return created


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="project name")
    parser.add_argument("--type", dest="project_type", help="project starter type")
    parser.add_argument("--destination", help="project destination directory")
    parser.add_argument("--list-types", action="store_true", help="list available project starters and exit")
    parser.add_argument("--owner", default="[OWNER]", help="project owner placeholder value")
    parser.add_argument("--technology", default="[TECHNOLOGY]", help="technology placeholder value")
    parser.add_argument("--status", default="planning", help="initial project status")
    parser.add_argument("--purpose", default="[PROJECT PURPOSE]", help="project purpose placeholder value")
    parser.add_argument("--force", action="store_true", help="overwrite starter-owned files in a non-empty destination")
    parser.add_argument("--init-git", action="store_true", help="initialize Git without creating a commit")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_types:
        print("\n".join(available_starters()))
        return 0
    missing = [flag for flag, value in (("--name", args.name), ("--type", args.project_type), ("--destination", args.destination)) if not value]
    if missing:
        parser.error("required unless --list-types: " + ", ".join(missing))
    try:
        created = create_project(args.name, args.project_type, args.destination, args.owner, args.technology, args.status, args.purpose, args.force, args.init_git)
    except ValueError as exc:
        parser.error(str(exc))
    for path in created:
        print(path)
    print(f"Created {len(created)} files in {Path(args.destination).expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
