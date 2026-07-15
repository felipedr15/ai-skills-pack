"""Regression tests for repo_files: generator discovery must not pick up
arbitrary untracked local directories (e.g. IDE settings, scratch folders),
regardless of what they are named.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import repo_files
from knowledge_graph import build as kg_build
from knowledge_graph import extract as kg_extract
from knowledge_graph import utils as kg_utils
from knowledge_graph import validate as kg_validate
from semantic_discovery import build as sd_build
from semantic_discovery import extract as sd_extract
from semantic_discovery import utils as sd_utils
from semantic_discovery import validate as sd_validate


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, timeout=30,
    )


def _init_git_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "-c", "user.email=test@example.com", "-c", "user.name=test", "add", "-A")
    _git(root, "-c", "user.email=test@example.com", "-c", "user.name=test", "commit", "-q", "-m", "init")


def _write(path: Path, content: str = "# Doc\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _tracked_repo_fixture(root: Path) -> None:
    """A minimal repository with content committed to git."""
    _write(root / "README.md", "# Root\n")
    _write(
        root / "memory" / "lessons" / "lesson-a.md",
        "---\nid: lesson-a\ntitle: Lesson A\ntype: lesson\nscope: global\n"
        "project: null\nstatus: active\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
        "source: test\nsummary: test\ntags: []\nrelated: []\n"
        "sensitivity: internal\nretention: permanent\n"
        "contentPath: memory/lessons/lesson-a.md\n---\n# Lesson A\n",
    )
    _init_git_repo(root)


class GitTrackedFilesTests(unittest.TestCase):
    def test_returns_none_outside_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md")
            self.assertIsNone(repo_files.git_tracked_files(root))

    def test_lists_only_tracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            _write(root / "local-temp" / "settings.json", "{}")  # untracked, added after commit
            tracked = repo_files.git_tracked_files(root)
            self.assertIsNotNone(tracked)
            self.assertIn("README.md", tracked)
            self.assertIn("memory/lessons/lesson-a.md", tracked)
            self.assertNotIn("local-temp/settings.json", tracked)


class DiscoverableFilesTests(unittest.TestCase):
    def test_arbitrary_untracked_directory_not_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            _write(root / "local-temp" / "settings.json", "{}")
            rels = {p.relative_to(root).as_posix() for p in repo_files.discoverable_files(root)}
            self.assertNotIn("local-temp/settings.json", rels)

    def test_tracked_file_in_supported_directory_is_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            rels = {p.relative_to(root).as_posix() for p in repo_files.discoverable_files(root)}
            self.assertIn("README.md", rels)
            self.assertIn("memory/lessons/lesson-a.md", rels)

    def test_fallback_without_git_still_rejects_arbitrary_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md")
            _write(root / "memory" / "lessons" / "lesson-a.md")
            _write(root / "local-temp" / "settings.json", "{}")
            # No git init: git_tracked_files() returns None, exercising the fallback path.
            self.assertIsNone(repo_files.git_tracked_files(root))
            rels = {p.relative_to(root).as_posix() for p in repo_files.discoverable_files(root)}
            self.assertIn("README.md", rels)
            self.assertIn("memory/lessons/lesson-a.md", rels)
            self.assertNotIn("local-temp/settings.json", rels)


class KnowledgeGraphIndexingScopeTests(unittest.TestCase):
    def test_untracked_local_directory_excluded_from_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            _write(root / "local-temp" / "settings.json", "{}")
            files = kg_extract.discover_source_files(root)
            rels = {kg_utils.normalize_relpath(p, root) for p in files}
            self.assertNotIn("local-temp/settings.json", rels)
            self.assertIn("README.md", rels)

    def test_generation_identical_with_and_without_untracked_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            before = kg_build.build_graph(root)
            _write(root / "local-temp" / "settings.json", "{}")
            after = kg_build.build_graph(root)
            self.assertTrue(kg_validate.compare_graphs_ignoring_generated_at(before, after))

    def test_graph_with_untracked_folder_present_still_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            _write(root / "local-temp" / "settings.json", "{}")
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertFalse(failures)


class DiscoveryIndexIndexingScopeTests(unittest.TestCase):
    def test_untracked_local_directory_excluded_from_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            (root / "generated").mkdir(exist_ok=True)
            _write(root / "local-temp" / "settings.json", "{}")
            files = sd_extract.discover_source_files(root)
            rels = {sd_utils.normalize_path(str(p.relative_to(root))) for p in files}
            self.assertNotIn("local-temp/settings.json", rels)
            self.assertIn("README.md", rels)

    def test_generation_identical_with_and_without_untracked_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            before = sd_build.build(root)
            _write(root / "local-temp" / "settings.json", "{}")  # left untracked on purpose
            after = sd_build.build(root)
            before_docs = sorted(d["id"] for d in before["documents"])
            after_docs = sorted(d["id"] for d in after["documents"])
            self.assertEqual(before_docs, after_docs)

    def test_index_with_untracked_folder_present_still_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tracked_repo_fixture(root)
            _write(root / "local-temp" / "settings.json", "{}")
            index = sd_build.build(root)
            failures, _warnings = sd_validate.validate_index_object(index)
            self.assertFalse(failures)


if __name__ == "__main__":
    unittest.main()
