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


memory_archive = load_script("memory-archive.py")


class MemoryArchiveTests(unittest.TestCase):
    def test_archive_moves_record_and_updates_registry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memory" / "lessons").mkdir(parents=True)
            source = root / "memory" / "lessons" / "lesson-x-001.md"
            source.write_text(
                "---\nid: lesson-x-001\ntitle: X\ntype: lesson\nscope: global\nproject: null\nstatus: active\ncreated: 2026-07-12\nupdated: 2026-07-12\nsource: t\nsummary: s\ntags: []\nrelated: []\nsensitivity: internal\nretention: permanent\ncontentPath: memory/lessons/lesson-x-001.md\n---\n\n# X\n",
                encoding="utf-8",
            )
            (root / "memory" / "registry.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "1.0.0",
                        "records": [
                            {
                                "id": "lesson-x-001",
                                "title": "X",
                                "type": "lesson",
                                "scope": "global",
                                "project": None,
                                "status": "active",
                                "path": "memory/lessons/lesson-x-001.md",
                                "tags": [],
                                "sensitivity": "internal",
                                "retention": "permanent",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            memory_archive.repo_root = lambda: root
            code = memory_archive.main(["--id", "lesson-x-001"])
            self.assertEqual(code, 0)
            self.assertFalse(source.exists())
            self.assertTrue((root / "memory" / "archive" / "lesson-x-001.md").is_file())
            registry = json.loads((root / "memory" / "registry.json").read_text(encoding="utf-8"))["records"][0]
            self.assertEqual(registry["status"], "archived")

    def test_missing_record_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memory").mkdir(parents=True)
            (root / "memory" / "registry.json").write_text('{"schemaVersion":"1.0.0","records":[]}', encoding="utf-8")
            memory_archive.repo_root = lambda: root
            code = memory_archive.main(["--id", "missing-id"])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
