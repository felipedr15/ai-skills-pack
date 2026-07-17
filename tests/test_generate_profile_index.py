"""Tests for scripts/generate-profile-index.py (Task 005)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


profile_index = load_script("generate-profile-index.py")


def _write_profile(root: Path, profile_id: str, active: bool, role: str = "Senior IT Technical Support Analyst"):
    (root / "profile").mkdir(parents=True, exist_ok=True)
    (root / "profile" / f"{profile_id}.md").write_text(
        "---\n"
        f"id: {profile_id}\n"
        'schemaVersion: "1.0.0"\n'
        f"role: {role}\n"
        "team: IT Support\n"
        "responsibilities:\n  - Tier 2/3 support\n"
        "reportingTo: it-manager\n"
        "sensitivity: high\n"
        "createdAt: 2026-07-15\n"
        "updatedAt: 2026-07-15\n"
        "---\n# Profile\n",
        encoding="utf-8",
    )
    return {"id": profile_id, "path": f"profile/{profile_id}.md", "active": active, "createdAt": "2026-07-15T00:00:00Z"}


def _write_registry(root: Path, entries: list):
    (root / "profile").mkdir(parents=True, exist_ok=True)
    (root / "profile" / "registry.json").write_text(
        json.dumps({"schemaVersion": "1.0.0", "profiles": entries}), encoding="utf-8"
    )


class EmptyRegistryTests(unittest.TestCase):
    def test_no_profile_directory_produces_empty_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = profile_index.build_index(root)
            self.assertEqual(index["recordCount"], 0)
            self.assertEqual(index["records"], [])

    def test_empty_registry_file_produces_empty_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_registry(root, [])
            index = profile_index.build_index(root)
            self.assertEqual(index["recordCount"], 0)


class SingleProfileTests(unittest.TestCase):
    def test_valid_single_active_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _write_profile(root, "primary", active=True)
            _write_registry(root, [entry])
            index = profile_index.build_index(root)
            self.assertEqual(index["recordCount"], 1)
            record = index["records"][0]
            self.assertEqual(record["id"], "primary")
            self.assertEqual(record["role"], "Senior IT Technical Support Analyst")
            self.assertEqual(record["team"], "IT Support")
            self.assertTrue(record["active"])
            # Summary shape only -- responsibilities/reportingTo/prose never surface.
            self.assertNotIn("responsibilities", record)
            self.assertNotIn("reportingTo", record)

    def test_zero_active_with_profile_present_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _write_profile(root, "primary", active=False)
            _write_registry(root, [entry])
            with self.assertRaises(profile_index.ProfileIndexError):
                profile_index.build_index(root)

    def test_multiple_active_profiles_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            e1 = _write_profile(root, "primary", active=True)
            e2 = _write_profile(root, "secondary", active=True)
            _write_registry(root, [e1, e2])
            with self.assertRaises(profile_index.ProfileIndexError):
                profile_index.build_index(root)

    def test_orphaned_registry_entry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_registry(root, [{"id": "ghost", "path": "profile/ghost.md", "active": True, "createdAt": "2026-07-15T00:00:00Z"}])
            with self.assertRaises(profile_index.ProfileIndexError):
                profile_index.build_index(root)

    def test_file_not_in_registry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_profile(root, "primary", active=True)
            _write_registry(root, [])  # file exists but registry doesn't mention it
            with self.assertRaises(profile_index.ProfileIndexError):
                profile_index.build_index(root)

    def test_duplicate_profile_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _write_profile(root, "primary", active=True)
            _write_registry(root, [entry, dict(entry)])
            with self.assertRaises(profile_index.ProfileIndexError):
                profile_index.build_index(root)


class DeterminismAndStalenessTests(unittest.TestCase):
    def test_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _write_profile(root, "primary", active=True)
            _write_registry(root, [entry])
            first = profile_index.render_json(profile_index.build_index(root))
            second = profile_index.render_json(profile_index.build_index(root))
            self.assertEqual(first, second)

    def test_stale_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "generated" / "profile-index.json"
            with self.assertRaises(profile_index.ProfileIndexError):
                profile_index.write_or_check({out: "expected\n"}, check=True)

    def test_check_mode_performs_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "generated" / "profile-index.json"
            try:
                profile_index.write_or_check({out: "expected\n"}, check=True)
            except profile_index.ProfileIndexError:
                pass
            self.assertFalse(out.exists())

    def test_path_uses_forward_slashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _write_profile(root, "primary", active=True)
            _write_registry(root, [entry])
            index = profile_index.build_index(root)
            self.assertNotIn("\\", index["records"][0]["path"])


class RenderTests(unittest.TestCase):
    def test_markdown_render_reflects_active_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _write_profile(root, "primary", active=True)
            _write_registry(root, [entry])
            index = profile_index.build_index(root)
            md = profile_index.render_markdown(index)
            self.assertIn("primary", md)
            self.assertIn("true", md)


if __name__ == "__main__":
    unittest.main()
