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


memory_promote = load_script("memory-promote.py")


class MemoryPromoteTests(unittest.TestCase):
    def make_record(self, root: Path, status="active"):
        (root / "memory" / "sessions").mkdir(parents=True)
        source = root / "memory" / "sessions" / "session-x-001.md"
        source.write_text(
            f"---\nid: session-x-001\ntitle: Session X\ntype: session\nscope: session\nproject: ai-os\nstatus: {status}\ncreated: 2026-07-12\nupdated: 2026-07-12\nsource: t\nsummary: s\ntags:\n  - demo\nrelated: []\nsensitivity: internal\nretention: temporary\ncontentPath: memory/sessions/session-x-001.md\n---\n\n# Session X\n",
            encoding="utf-8",
        )
        (root / "memory" / "registry.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0.0",
                    "records": [
                        {
                            "id": "session-x-001",
                            "title": "Session X",
                            "type": "session",
                            "scope": "session",
                            "project": "ai-os",
                            "status": status,
                            "path": "memory/sessions/session-x-001.md",
                            "tags": ["demo"],
                            "sensitivity": "internal",
                            "retention": "temporary",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_session_to_lesson_promotion_with_traceability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_record(root)
            memory_promote.repo_root = lambda: root
            code = memory_promote.main(["--id", "session-x-001", "--target-type", "lesson", "--target-scope", "global", "--reason", "Reusable troubleshooting lesson"])
            self.assertEqual(code, 0)
            registry = json.loads((root / "memory" / "registry.json").read_text(encoding="utf-8"))["records"]
            source = [row for row in registry if row["id"] == "session-x-001"][0]
            self.assertEqual(source["status"], "superseded")
            promoted = [row for row in registry if row["id"] != "session-x-001"][0]
            self.assertEqual(promoted["type"], "lesson")
            self.assertTrue((root / promoted["path"]).is_file())

    def test_proposed_to_active_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_record(root, status="proposed")
            memory_promote.repo_root = lambda: root
            code = memory_promote.main(["--id", "session-x-001", "--reason", "Approved for active usage"])
            self.assertEqual(code, 0)
            registry = json.loads((root / "memory" / "registry.json").read_text(encoding="utf-8"))["records"][0]
            self.assertEqual(registry["status"], "active")


if __name__ == "__main__":
    unittest.main()
