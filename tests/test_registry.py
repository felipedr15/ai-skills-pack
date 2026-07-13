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


registry = load_script("generate-skill-registry.py")


def write_skill(root, folder, skill_id="example", include_name=True, dependencies="[]"):
    path = root / ".agent" / "skills" / folder / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    name = "name: Example\n" if include_name else ""
    path.write_text(
        "---\n" + name + f"id: {skill_id}\nversion: 1.0.0\ndescription: Example skill.\n"
        f"triggers:\n  - example\ninputs:\n  - context\noutputs:\n  - result\ndependencies: {dependencies}\n"
        "status: stable\nreplaces: null\ndeprecatedBy: null\n---\n# Example\n",
        encoding="utf-8",
    )
    return path


class RegistryTests(unittest.TestCase):
    def test_skill_discovery_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "zeta", "zeta")
            write_skill(root, "alpha", "alpha")
            first = registry.render_json(registry.build_registry(root))
            second = registry.render_json(registry.build_registry(root))
            self.assertEqual(first, second)
            self.assertLess(first.index('"id": "alpha"'), first.index('"id": "zeta"'))

    def test_duplicate_ids_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "one", "duplicate")
            write_skill(root, "two", "duplicate")
            with self.assertRaisesRegex(registry.RegistryError, "duplicate skill id"):
                registry.build_registry(root)

    def test_missing_metadata_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_skill(root, "broken", include_name=False)
            with self.assertRaisesRegex(registry.RegistryError, "missing required metadata"):
                registry.build_registry(root)

    def test_stale_output_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "generated" / "skills.json"
            with self.assertRaises(registry.RegistryError):
                registry.write_or_check({output: "expected\n"}, check=True)
            output.parent.mkdir()
            output.write_text("old\n", encoding="utf-8")
            with self.assertRaises(registry.RegistryError):
                registry.write_or_check({output: "expected\n"}, check=True)


if __name__ == "__main__":
    unittest.main()
