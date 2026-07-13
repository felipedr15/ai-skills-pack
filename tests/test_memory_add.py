import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


memory_add = load_script("memory-add.py")


class MemoryAddTests(unittest.TestCase):
    def make_root(self, root: Path):
        (root / "memory" / "lessons").mkdir(parents=True)
        (root / "memory" / "registry.json").write_text('{"schemaVersion":"1.0.0","records":[]}', encoding="utf-8")

    def test_valid_record_creation_and_registry_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            args = argparse.Namespace(
                type="lesson",
                title="Refresh before rebuild",
                scope="global",
                project=None,
                summary="Refresh source first.",
                tags="power-apps,sharepoint",
                sensitivity="internal",
                retention="permanent",
                source="unit-test",
            )
            code = memory_add.create_record(root, args)
            self.assertEqual(code, 0)

            registry = json.loads((root / "memory" / "registry.json").read_text(encoding="utf-8"))["records"]
            self.assertEqual(len(registry), 1)
            self.assertEqual(registry[0]["type"], "lesson")
            self.assertTrue((root / registry[0]["path"]).is_file())

    def test_duplicate_id_prevention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            first = {
                "id": "lesson-refresh-before-rebuild-001",
                "title": "Existing",
                "type": "lesson",
                "scope": "global",
                "project": None,
                "status": "active",
                "path": "memory/lessons/lesson-refresh-before-rebuild-001.md",
                "tags": ["x"],
                "sensitivity": "internal",
                "retention": "permanent",
            }
            (root / "memory" / "registry.json").write_text(json.dumps({"schemaVersion": "1.0.0", "records": [first]}), encoding="utf-8")
            args = argparse.Namespace(
                type="lesson",
                title="Refresh before rebuild",
                scope="global",
                project=None,
                summary="Refresh source first.",
                tags="",
                sensitivity="internal",
                retention="permanent",
                source="unit-test",
            )
            code = memory_add.create_record(root, args)
            self.assertEqual(code, 0)
            records = json.loads((root / "memory" / "registry.json").read_text(encoding="utf-8"))["records"]
            ids = [row["id"] for row in records]
            self.assertIn("lesson-refresh-before-rebuild-001", ids)
            self.assertIn("lesson-refresh-before-rebuild-002", ids)

    def test_likely_secret_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_root(root)
            args = argparse.Namespace(
                type="lesson",
                title="bad",
                scope="global",
                project=None,
                summary="api_key placeholder-like content",
                tags="",
                sensitivity="internal",
                retention="permanent",
                source="unit-test",
            )
            with self.assertRaises(ValueError):
                memory_add.create_record(root, args)


if __name__ == "__main__":
    unittest.main()
