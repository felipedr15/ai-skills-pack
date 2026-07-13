import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("create_project", ROOT / "scripts/create-project.py")
creator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(creator)


class ProjectGeneratorTests(unittest.TestCase):
    def make_starter(self, root):
        starter = root / "templates" / "project-starters" / "demo"
        starter.mkdir(parents=True)
        (starter / "README.md").write_text("# [PROJECT NAME]\n[PROJECT PURPOSE]\n[OWNER]\n[TECHNOLOGY]\n[CURRENT STATUS]\n", encoding="utf-8")
        return root / "templates" / "project-starters"

    def test_project_creation_and_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            starters = self.make_starter(root)
            destination = root / "output"
            created = creator.create_project("Sample", "demo", destination, "Owner", "Python", "active", "Purpose", starters_root=starters)
            self.assertEqual(len(created), 2)
            readme = (destination / "README.md").read_text(encoding="utf-8")
            self.assertIn("# Sample", readme)
            self.assertNotIn("[PROJECT NAME]", readme)
            self.assertIn('name: "Sample"', (destination / "project.yaml").read_text(encoding="utf-8"))

    def test_non_empty_destination_is_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            starters = self.make_starter(root)
            destination = root / "output"
            destination.mkdir()
            (destination / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                creator.create_project("Sample", "demo", destination, starters_root=starters)


if __name__ == "__main__":
    unittest.main()
