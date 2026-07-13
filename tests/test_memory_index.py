import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


memory_index = load_script("generate-memory-index.py")


class MemoryIndexTests(unittest.TestCase):
    def prepare(self, root: Path):
        (root / "memory" / "lessons").mkdir(parents=True)
        (root / "memory" / "lessons" / "lesson-a-001.md").write_text(
            "---\nid: lesson-a-001\ntitle: A\ntype: lesson\nscope: global\nproject: null\nstatus: active\ncreated: 2026-07-12\nupdated: 2026-07-12\nsource: s\nsummary: sum\ntags:\n  - t\nrelated: []\nsensitivity: internal\nretention: permanent\ncontentPath: memory/lessons/lesson-a-001.md\n---\n\n# A\n",
            encoding="utf-8",
        )
        (root / "memory" / "registry.json").write_text(
            '{"schemaVersion":"1.0.0","records":[{"id":"lesson-a-001","title":"A","type":"lesson","scope":"global","project":null,"status":"active","path":"memory/lessons/lesson-a-001.md","tags":["t"],"sensitivity":"internal","retention":"permanent"}]}',
            encoding="utf-8",
        )

    def test_index_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            first = memory_index.render_json(memory_index.build_index(root))
            second = memory_index.render_json(memory_index.build_index(root))
            self.assertEqual(first, second)

    def test_stale_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            out = root / "generated" / "memory-index.json"
            with self.assertRaises(memory_index.MemoryIndexError):
                memory_index.write_or_check({out: "expected\n"}, check=True)

    def test_invalid_metadata_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memory" / "lessons").mkdir(parents=True)
            (root / "memory" / "lessons" / "lesson-a-001.md").write_text("# no metadata\n", encoding="utf-8")
            (root / "memory" / "registry.json").write_text('{"schemaVersion":"1.0.0","records":[]}', encoding="utf-8")
            with self.assertRaises(memory_index.MemoryIndexError):
                memory_index.build_index(root)


if __name__ == "__main__":
    unittest.main()
