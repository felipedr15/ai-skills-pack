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


memory_list = load_script("memory-list.py")


class MemoryListTests(unittest.TestCase):
    def test_type_and_project_filtering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = root / "memory"
            memory.mkdir()
            payload = {
                "schemaVersion": "1.0.0",
                "records": [
                    {"id": "lesson-a-001", "title": "A", "type": "lesson", "scope": "global", "project": None, "status": "active", "path": "memory/lessons/a.md", "tags": ["x"], "sensitivity": "internal", "retention": "permanent"},
                    {"id": "project-a-001", "title": "B", "type": "project", "scope": "project", "project": "ai-os", "status": "active", "path": "memory/projects/b.md", "tags": ["x"], "sensitivity": "internal", "retention": "project"},
                ],
            }
            (memory / "registry.json").write_text(json.dumps(payload), encoding="utf-8")
            memory_list.repo_root = lambda: root
            output = io.StringIO()
            with redirect_stdout(output):
                code = memory_list.main(["--type", "project", "--project", "ai-os"])
            self.assertEqual(code, 0)
            text = output.getvalue()
            self.assertIn("project-a-001", text)
            self.assertNotIn("lesson-a-001", text)


if __name__ == "__main__":
    unittest.main()
