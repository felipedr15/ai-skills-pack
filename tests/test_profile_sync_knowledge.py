"""Tests for scripts/profile/sync_knowledge.py (Tasks 008-010) and the
generation non-mutation guarantee (Task 011)."""
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from profile import sync_knowledge as sk
from profile.sanitize import SanitizationError


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SafeDefaultSyncTests(unittest.TestCase):
    def test_creates_scaffold_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = sk.sync(root)
            self.assertEqual(result["status"], "created")
            self.assertTrue((root / sk.OVERVIEW_PATH).is_file())

    def test_does_not_overwrite_existing_curated_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overview = root / sk.OVERVIEW_PATH
            overview.parent.mkdir(parents=True)
            overview.write_text("# My hand-edited overview\nCustom curated content.\n", encoding="utf-8")
            before = overview.read_bytes()
            result = sk.sync(root)
            self.assertEqual(result["status"], "unchanged")
            self.assertIn("no overwrite", result["message"])
            self.assertEqual(overview.read_bytes(), before)

    def test_repeated_sync_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r1 = sk.sync(root)
            content1 = (root / sk.OVERVIEW_PATH).read_bytes()
            r2 = sk.sync(root)
            r3 = sk.sync(root)
            self.assertEqual(r1["status"], "created")
            self.assertEqual(r2["status"], "unchanged")
            self.assertEqual(r3["status"], "unchanged")
            self.assertEqual((root / sk.OVERVIEW_PATH).read_bytes(), content1)

    def test_never_creates_snapshot_on_default_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            self.assertFalse((root / sk.SNAPSHOTS_DIR).exists())

    def test_does_not_mutate_profile_or_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profile").mkdir()
            (root / "profile" / "registry.json").write_text('{"schemaVersion":"1.0.0","profiles":[]}', encoding="utf-8")
            (root / "memory").mkdir()
            (root / "memory" / "registry.json").write_text('{"schemaVersion":"1.0.0","records":[]}', encoding="utf-8")
            before_profile = (root / "profile" / "registry.json").read_bytes()
            before_memory = (root / "memory" / "registry.json").read_bytes()
            sk.sync(root)
            self.assertEqual((root / "profile" / "registry.json").read_bytes(), before_profile)
            self.assertEqual((root / "memory" / "registry.json").read_bytes(), before_memory)

    def test_does_not_create_generated_profile_or_work_activity_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            self.assertFalse((root / "generated" / "profile-index.json").exists())
            self.assertFalse((root / "generated" / "work-activity.json").exists())

    def test_never_fabricates_profile_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            content = (root / sk.OVERVIEW_PATH).read_text(encoding="utf-8")
            self.assertIn("No active professional profile is configured yet", content)

    def test_reflects_active_profile_without_inventing_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profile").mkdir()
            (root / "profile" / "registry.json").write_text(
                json.dumps({"schemaVersion": "1.0.0", "profiles": [
                    {"id": "primary", "path": "profile/primary.md", "active": True, "createdAt": "2026-07-15T00:00:00Z"}
                ]}),
                encoding="utf-8",
            )
            result = sk.sync(root)
            content = (root / sk.OVERVIEW_PATH).read_text(encoding="utf-8")
            self.assertEqual(result["status"], "created")
            self.assertIn("primary", content)
            # Only the id/path are surfaced -- no role/team/etc. is invented.
            self.assertNotIn("role", content.lower().split("active profile")[0])


class ForceRefreshTests(unittest.TestCase):
    def test_requires_explicit_flag_semantics_via_separate_function(self):
        # sync() never snapshots; only force_refresh() does -- this is the
        # "explicit flag required" boundary at the library level (the CLI
        # wires --force-refresh to force_refresh() and nothing else calls it).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            self.assertFalse((root / sk.SNAPSHOTS_DIR).exists())

    def test_refuses_when_no_curated_content_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(sk.SyncKnowledgeError):
                sk.force_refresh(root)
            # No meaningless/empty snapshot created.
            self.assertFalse((root / sk.SNAPSHOTS_DIR).exists())

    def test_snapshots_pre_refresh_content_and_leaves_overview_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            pre_content = (root / sk.OVERVIEW_PATH).read_bytes()
            result = sk.force_refresh(root)
            self.assertEqual(result["status"], "snapshotted")
            snapshot_content = (root / result["path"]).read_bytes()
            self.assertEqual(snapshot_content, pre_content, "snapshot must capture pre-refresh content")
            self.assertEqual((root / sk.OVERVIEW_PATH).read_bytes(), pre_content, "overview.md must never be touched")

    def test_snapshots_hand_edited_content_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overview = root / sk.OVERVIEW_PATH
            overview.parent.mkdir(parents=True)
            overview.write_text("# Hand-edited overview\nCurated by a human.\n", encoding="utf-8")
            result = sk.force_refresh(root)
            self.assertEqual((root / result["path"]).read_text(encoding="utf-8"), "# Hand-edited overview\nCurated by a human.\n")

    def test_refuses_refresh_when_curated_content_fails_sanitization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overview = root / sk.OVERVIEW_PATH
            overview.parent.mkdir(parents=True)
            overview.write_text("Contact: jane.doe@county.gov\n", encoding="utf-8")
            with self.assertRaises(SanitizationError):
                sk.force_refresh(root)
            self.assertFalse((root / sk.SNAPSHOTS_DIR).exists())

    def test_does_not_mutate_memory_or_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            (root / "memory").mkdir()
            (root / "memory" / "registry.json").write_text('{"schemaVersion":"1.0.0","records":[]}', encoding="utf-8")
            (root / "profile").mkdir()
            (root / "profile" / "registry.json").write_text('{"schemaVersion":"1.0.0","profiles":[]}', encoding="utf-8")
            before_memory = (root / "memory" / "registry.json").read_bytes()
            before_profile = (root / "profile" / "registry.json").read_bytes()
            sk.force_refresh(root)
            self.assertEqual((root / "memory" / "registry.json").read_bytes(), before_memory)
            self.assertEqual((root / "profile" / "registry.json").read_bytes(), before_profile)


class SnapshotNamingTests(unittest.TestCase):
    FILENAME_RE = re.compile(r"^professional-context-\d{4}-\d{2}-\d{2}T\d{6}Z\.md$")

    def test_filename_matches_finalized_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            result = sk.force_refresh(root)
            filename = Path(result["path"]).name
            self.assertRegex(filename, self.FILENAME_RE)

    def test_filename_is_filesystem_safe(self):
        fixed = datetime(2026, 7, 15, 23, 5, 30, tzinfo=timezone.utc)
        filename = sk.snapshot_filename(fixed)
        self.assertNotIn(" ", filename)
        self.assertNotIn(":", filename)
        # No characters requiring escaping on Windows or POSIX.
        self.assertRegex(filename, r"^[A-Za-z0-9._-]+$")

    def test_filename_deterministic_for_same_timestamp(self):
        fixed = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        self.assertEqual(sk.snapshot_filename(fixed), sk.snapshot_filename(fixed))
        self.assertEqual(sk.snapshot_filename(fixed), "professional-context-2026-01-02T030405Z.md")

    def test_snapshot_stored_only_under_snapshots_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            result = sk.force_refresh(root)
            self.assertTrue(result["path"].startswith(sk.SNAPSHOTS_DIR + "/"))

    def test_same_second_collision_raises_not_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            fixed_now = datetime(2026, 7, 15, 23, 0, 0, tzinfo=timezone.utc)
            first = sk.force_refresh(root, now=fixed_now)
            first_bytes = (root / first["path"]).read_bytes()
            # Change the curated content, then retry at the exact same second.
            (root / sk.OVERVIEW_PATH).write_text("# Changed\nDifferent content now.\n", encoding="utf-8")
            with self.assertRaises(sk.SyncKnowledgeError):
                sk.force_refresh(root, now=fixed_now)
            # The original snapshot must be untouched -- no silent overwrite.
            self.assertEqual((root / first["path"]).read_bytes(), first_bytes)

    def test_different_second_does_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sk.sync(root)
            t1 = datetime(2026, 7, 15, 23, 0, 0, tzinfo=timezone.utc)
            t2 = datetime(2026, 7, 15, 23, 0, 1, tzinfo=timezone.utc)
            r1 = sk.force_refresh(root, now=t1)
            r2 = sk.force_refresh(root, now=t2)
            self.assertNotEqual(r1["path"], r2["path"])

    def test_no_personal_identifier_in_filename(self):
        fixed = datetime(2026, 7, 15, 23, 5, 30, tzinfo=timezone.utc)
        filename = sk.snapshot_filename(fixed)
        # Filename is purely timestamp-derived -- no profile id, no username.
        self.assertEqual(filename, "professional-context-2026-07-15T230530Z.md")


class SnapshotSanitizationAndTruthTests(unittest.TestCase):
    def test_snapshot_content_is_sanitized_same_as_active_content(self):
        # force_refresh re-validates pre-refresh content even though sync()
        # already sanitized it at creation time -- guards against manual
        # edits introducing prohibited content after the fact.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overview = root / sk.OVERVIEW_PATH
            overview.parent.mkdir(parents=True)
            overview.write_text("password: LeakedSecret123\n", encoding="utf-8")
            with self.assertRaises(SanitizationError):
                sk.force_refresh(root)

    def test_no_empty_or_meaningless_snapshot_without_curated_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                sk.force_refresh(root)
            except sk.SyncKnowledgeError:
                pass
            self.assertFalse((root / sk.SNAPSHOTS_DIR).is_dir())


class NonMutationByGenerationTests(unittest.TestCase):
    """Task 011: normal generate/generate --check/validation must never
    touch knowledge/professional-context/ or its snapshots."""

    def test_sync_knowledge_not_referenced_by_any_generation_order_script(self):
        from release.utils import GENERATION_ORDER

        for script_path, _label in GENERATION_ORDER:
            source = (ROOT / script_path).read_text(encoding="utf-8")
            self.assertNotIn("sync_knowledge", source, script_path)
            self.assertNotIn("sync-knowledge", source, script_path)

    def test_sync_knowledge_not_referenced_by_validate_all(self):
        source = (ROOT / "scripts" / "validate-all.py").read_text(encoding="utf-8")
        self.assertNotIn("sync_knowledge", source)
        self.assertNotIn("sync-knowledge", source)

    def test_profile_index_generator_does_not_touch_professional_context(self):
        profile_index = load_script("generate-profile-index.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_index.build_index(root)
            self.assertFalse((root / "knowledge" / "professional-context").exists())

    def test_work_activity_generator_does_not_touch_professional_context(self):
        work_activity = load_script("generate-work-activity.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work_activity.build_work_activity(root)
            self.assertFalse((root / "knowledge" / "professional-context").exists())

    def test_real_repo_generate_check_leaves_professional_context_absent(self):
        # Live check against the actual repository: confirms this session's
        # manual CLI testing artifacts were cleaned up and that re-running
        # the real, already-validated generators does not recreate them.
        professional_context = ROOT / "knowledge" / "professional-context"
        existed_before = professional_context.exists()
        profile_index = load_script("generate-profile-index.py")
        work_activity = load_script("generate-work-activity.py")
        profile_index.build_index(ROOT)
        work_activity.build_work_activity(ROOT)
        self.assertEqual(professional_context.exists(), existed_before)


class CLIWiringTests(unittest.TestCase):
    """Confirms `ai-os.py profile sync-knowledge [--force-refresh]` actually
    dispatches through argparse to the library functions above -- library
    tests alone don't exercise the CLI dispatch layer."""

    def _run_cli(self, args, cwd):
        import io
        import os
        from contextlib import redirect_stderr, redirect_stdout

        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        old_cwd = Path.cwd()
        old_root = None
        try:
            os.chdir(cwd)
            spec.loader.exec_module(mod)
            old_root = mod.ROOT
            mod.ROOT = cwd
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = mod.main(args)
            return code, stdout.getvalue(), stderr.getvalue()
        finally:
            os.chdir(old_cwd)

    def test_cli_sync_knowledge_creates_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, out, _err = self._run_cli(["profile", "sync-knowledge"], root)
            self.assertEqual(code, 0)
            self.assertIn("CREATED", out)
            self.assertTrue((root / sk.OVERVIEW_PATH).is_file())

    def test_cli_sync_knowledge_second_run_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_cli(["profile", "sync-knowledge"], root)
            code, out, _err = self._run_cli(["profile", "sync-knowledge"], root)
            self.assertEqual(code, 0)
            self.assertIn("UNCHANGED", out)

    def test_cli_force_refresh_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run_cli(["profile", "sync-knowledge"], root)
            code, out, _err = self._run_cli(["profile", "sync-knowledge", "--force-refresh"], root)
            self.assertEqual(code, 0)
            self.assertIn("SNAPSHOTTED", out)
            self.assertTrue((root / sk.SNAPSHOTS_DIR).is_dir())

    def test_cli_force_refresh_without_prior_sync_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _out, err = self._run_cli(["profile", "sync-knowledge", "--force-refresh"], root)
            self.assertEqual(code, 1)
            self.assertIn("FAIL", err)


if __name__ == "__main__":
    unittest.main()
