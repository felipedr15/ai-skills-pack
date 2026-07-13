import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


memory_search = load_script("memory-search.py")


class MemorySearchTests(unittest.TestCase):
    def test_keyword_tag_and_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memory" / "lessons").mkdir(parents=True)
            (root / "memory" / "registry.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": "1.0.0",
                        "records": [
                            {
                                "id": "lesson-alpha-001",
                                "title": "Refresh data before rebuild",
                                "type": "lesson",
                                "scope": "global",
                                "project": None,
                                "status": "active",
                                "path": "memory/lessons/lesson-alpha-001.md",
                                "tags": ["refresh", "search"],
                                "sensitivity": "internal",
                                "retention": "permanent",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "memory" / "lessons" / "lesson-alpha-001.md").write_text(
                "---\nid: lesson-alpha-001\ntitle: Refresh data before rebuild\ntype: lesson\nscope: global\nproject: null\nstatus: active\ncreated: 2026-07-12\nupdated: 2026-07-12\nsource: t\nsummary: Refresh source first\ntags:\n  - refresh\nrelated: []\nsensitivity: internal\nretention: permanent\ncontentPath: memory/lessons/lesson-alpha-001.md\n---\n\n# Refresh data before rebuild\n\nRefresh source first.\n",
                encoding="utf-8",
            )
            memory_search.repo_root = lambda: root
            output = io.StringIO()
            with redirect_stdout(output):
                code = memory_search.main(["refresh", "--tag", "refresh", "--max-results", "5"])
            self.assertEqual(code, 0)
            text = output.getvalue()
            self.assertIn("lesson-alpha-001", text)
            self.assertIn("Excerpt:", text)


if __name__ == "__main__":
    unittest.main()
