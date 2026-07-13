import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("index_repository", ROOT / "scripts/index-repository.py")
indexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indexer)


class IndexingTests(unittest.TestCase):
    def test_categories_exclusions_and_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "scripts/z.py": "z", "scripts/a.py": "a", ".agent/skills/demo/SKILL.md": "skill",
                "templates/project-starters/web/README.md": "starter", "knowledge/note.md": "note",
                "scripts/__pycache__/bad.pyc": "bad", "scripts/.env": "secret", "node_modules/pkg/file.js": "dependency",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            result = indexer.build_index(root)
            paths = [item["path"] for item in result["files"]]
            self.assertIn(".agent/skills/demo/SKILL.md", paths)
            self.assertIn("templates/project-starters/web/README.md", paths)
            self.assertNotIn("scripts/.env", paths)
            self.assertNotIn("scripts/__pycache__/bad.pyc", paths)
            self.assertEqual(paths, [item["path"] for item in sorted(result["files"], key=lambda item: (item["category"], item["path"]))])

    def test_stale_index_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "generated" / "repository-index.json"
            with self.assertRaises(indexer.IndexError):
                indexer.write_or_check({output: "expected\n"}, check=True, root=root)


if __name__ == "__main__":
    unittest.main()
