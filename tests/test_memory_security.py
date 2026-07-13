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


memory_security = load_script("validate-memory-security.py")


class MemorySecurityTests(unittest.TestCase):
    def test_secret_detection_and_masking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memory" / "lessons").mkdir(parents=True)
            key_name = "api" + "_key"
            token = "SECRET" + "KEYVALUE12345"
            (root / "memory" / "lessons" / "lesson-x.md").write_text(f"{key_name} = {token}\n", encoding="utf-8")
            findings = memory_security.detect(root)
            self.assertTrue(findings)
            self.assertIn("***", findings[0]["masked"])
            self.assertNotIn(token, findings[0]["masked"])

    def test_placeholder_exemption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "memory" / "lessons").mkdir(parents=True)
            key_name = "api" + "_key"
            sample = "example" + "-placeholder-token"
            (root / "memory" / "lessons" / "lesson-x.md").write_text(f"{key_name} = {sample}\n", encoding="utf-8")
            findings = memory_security.detect(root)
            self.assertFalse(findings)


if __name__ == "__main__":
    unittest.main()
