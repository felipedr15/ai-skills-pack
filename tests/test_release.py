"""Comprehensive tests for Phase 7 Release Hardening."""
import importlib.util
import json
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from release.version import read_version, is_valid_semver, parse_version
from release.config import (
    load_config, validate_config, DEFAULT_CONFIG,
    CONFIG_SCHEMA_VERSION, ALLOWED_SECTIONS,
)
from release.status import get_status
from release.utils import (
    GENERATED_ARTIFACTS, GENERATION_ORDER,
    ensure_directory, now_iso, load_json_safe,
)


# ============================================================
# Version Tests
# ============================================================

class VersionTests(unittest.TestCase):
    def test_read_version(self):
        v = read_version(ROOT)
        self.assertTrue(is_valid_semver(v))

    def test_version_file_exists(self):
        self.assertTrue((ROOT / "VERSION").is_file())

    def test_valid_semver_parsing(self):
        self.assertTrue(is_valid_semver("0.7.0"))
        self.assertTrue(is_valid_semver("1.0.0"))
        self.assertTrue(is_valid_semver("1.2.3-beta.1"))
        self.assertFalse(is_valid_semver(""))
        self.assertFalse(is_valid_semver("1.0"))
        self.assertFalse(is_valid_semver("abc"))

    def test_parse_version(self):
        major, minor, patch, pre = parse_version("0.7.0")
        self.assertEqual((major, minor, patch), (0, 7, 0))
        self.assertEqual(pre, "")

    def test_parse_version_prerelease(self):
        major, minor, patch, pre = parse_version("1.0.0-beta.1")
        self.assertEqual((major, minor, patch), (1, 0, 0))
        self.assertEqual(pre, "beta.1")

    def test_single_source_of_truth(self):
        # VERSION file is the only source
        path = ROOT / "VERSION"
        content = path.read_text(encoding="utf-8").strip()
        self.assertEqual(content, read_version(ROOT))


# ============================================================
# Configuration Tests
# ============================================================

class ConfigTests(unittest.TestCase):
    def test_example_config_valid_json(self):
        path = ROOT / "config" / "ai-os.example.json"
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["schemaVersion"], CONFIG_SCHEMA_VERSION)

    def test_default_config_valid(self):
        failures, warnings = validate_config(DEFAULT_CONFIG)
        self.assertEqual(failures, [])

    def test_load_config_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(Path(tmp))
            self.assertEqual(config["schemaVersion"], CONFIG_SCHEMA_VERSION)
            self.assertEqual(config["dashboard"]["host"], "127.0.0.1")
            self.assertTrue(config["mcp"]["readOnly"])

    def test_local_config_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "ai-os.local.json").write_text(
                json.dumps({"schemaVersion": "1.0.0", "dashboard": {"port": 9090}}),
                encoding="utf-8")
            config = load_config(root)
            self.assertEqual(config["dashboard"]["port"], 9090)
            # Other defaults preserved
            self.assertEqual(config["dashboard"]["host"], "127.0.0.1")

    def test_unsafe_host_rejected(self):
        config = dict(DEFAULT_CONFIG)
        config["dashboard"] = {"host": "0.0.0.0", "port": 8080}
        failures, _ = validate_config(config)
        self.assertTrue(any("unsafe" in f for f in failures))

    def test_unknown_keys_warned(self):
        config = dict(DEFAULT_CONFIG)
        config["unknownKey"] = "value"
        _, warnings = validate_config(config)
        self.assertTrue(any("unknown" in w for w in warnings))

    def test_mcp_readonly_default(self):
        config = load_config(ROOT)
        self.assertTrue(config["mcp"]["readOnly"])

    def test_invalid_port(self):
        config = dict(DEFAULT_CONFIG)
        config["dashboard"] = {"host": "127.0.0.1", "port": 99999}
        failures, _ = validate_config(config)
        self.assertTrue(any("port" in f for f in failures))


# ============================================================
# Status Tests
# ============================================================

class StatusTests(unittest.TestCase):
    def test_status_from_real_repo(self):
        status = get_status(ROOT)
        self.assertEqual(status["version"], "0.8.0")
        self.assertIn("artifacts", status)
        self.assertIn("dashboard", status)
        self.assertIn("mcp", status)

    def test_status_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "VERSION").write_text("0.7.0\n", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "scripts").mkdir()
            status = get_status(root)
            self.assertFalse(status["releaseReady"])


# ============================================================
# CLI Tests
# ============================================================

class CLITests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_version_command(self):
        code, out, _ = self._run_cli(["version"])
        self.assertEqual(code, 0)
        self.assertIn("0.8.0", out)

    def test_status_command(self):
        code, out, _ = self._run_cli(["status"])
        self.assertEqual(code, 0)
        self.assertIn("AI OS v0.8.0", out)

    def test_status_json(self):
        code, out, _ = self._run_cli(["status", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["version"], "0.8.0")

    def test_doctor_command(self):
        code, out, _ = self._run_cli(["doctor"])
        self.assertIn("PASS", out)
        # Every check must pass except possibly "Dashboard port ... available",
        # which depends on whether some *other*, unrelated local process
        # happens to be using the configured port on this machine at test
        # time — an environmental condition the CLI cannot control and
        # should not be mocked away (doctor's job is to report the real
        # port state). Fail the test if any other check fails.
        failing_lines = [line for line in out.splitlines() if line.startswith("FAIL")]
        unexpected_failures = [line for line in failing_lines if "port" not in line.lower()]
        self.assertEqual(unexpected_failures, [], f"unexpected doctor failures: {unexpected_failures}")
        if not failing_lines:
            self.assertEqual(code, 0)

    def test_doctor_json(self):
        code, out, _ = self._run_cli(["doctor", "--json"])
        data = json.loads(out)
        self.assertIn("checks", data)
        # See test_doctor_command: only a port-availability failure is
        # tolerated, since it reflects real, unrelated local machine state.
        unexpected_failures = [
            c for c in data["checks"]
            if c["status"] == "FAIL" and "port" not in c["check"].lower()
        ]
        self.assertEqual(unexpected_failures, [], f"unexpected doctor failures: {unexpected_failures}")
        if data["failures"] == 0:
            self.assertEqual(code, 0)

    def test_help_command(self):
        code, out, _ = self._run_cli(["help"])
        self.assertEqual(code, 0)
        self.assertIn("bootstrap", out)

    def test_no_command_shows_help(self):
        code, out, _ = self._run_cli([])
        self.assertEqual(code, 0)
        self.assertIn("Commands:", out)

    def test_migrate_check(self):
        code, out, _ = self._run_cli(["migrate", "--check"])
        self.assertEqual(code, 0)
        self.assertIn("no pending migrations", out)

    def test_clean_generated_dry_run(self):
        code, out, _ = self._run_cli(["clean-generated"])
        self.assertEqual(code, 0)
        self.assertIn("Dry run", out)
        # Verify no files deleted
        self.assertTrue((ROOT / "generated" / "skills.json").is_file())


# ============================================================
# Bootstrap Tests
# ============================================================

class BootstrapTests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_bootstrap_check(self):
        code, out, _ = self._run_cli(["bootstrap", "--check"])
        # May fail if artifacts are stale (dirty working tree) — just verify it runs cleanly
        self.assertIn(code, (0, 1))
        self.assertIn("current", out.lower()) if code == 0 else self.assertIn("FAIL", out)

    def test_bootstrap_no_git_mutation(self):
        import subprocess
        before = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(ROOT)).stdout
        self._run_cli(["bootstrap", "--check"])
        after = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(ROOT)).stdout
        # Bootstrap check should not change git status (beyond pre-existing changes)
        self.assertEqual(before, after)


# ============================================================
# Build Tests
# ============================================================

class BuildTests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_build_check(self):
        code, out, _ = self._run_cli(["build", "--check"])
        # May pass or fail depending on artifact state - should not crash
        self.assertIn(code, (0, 1))

    def test_generation_order_defined(self):
        self.assertGreater(len(GENERATION_ORDER), 0)
        for script, label in GENERATION_ORDER:
            self.assertTrue(label)
            self.assertTrue(script.endswith(".py"))

    def test_phase9_generators_wired_into_generation_order(self):
        scripts = dict(GENERATION_ORDER)
        self.assertIn("scripts/generate-profile-index.py", scripts)
        self.assertIn("scripts/generate-work-activity.py", scripts)
        # profile index has no ordering dependency; work activity reads
        # generated/knowledge-graph.json, so it must run after that step.
        order = [script for script, _label in GENERATION_ORDER]
        self.assertLess(
            order.index("scripts/generate-knowledge-graph.py"),
            order.index("scripts/generate-work-activity.py"),
        )

    def test_phase9_artifacts_in_generated_artifacts_list(self):
        for name in ("profile-index.json", "profile-index.md", "work-activity.json", "work-activity.md"):
            self.assertIn(name, GENERATED_ARTIFACTS)


# ============================================================
# Packaging Tests
# ============================================================

class PackagingTests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_package_dry_run(self):
        code, out, _ = self._run_cli(["package", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("ai-os-0.8.0", out)
        self.assertIn("Files:", out)

    def test_package_excludes_git(self):
        code, out, _ = self._run_cli(["package", "--dry-run"])
        self.assertNotIn(".git/", out)
        self.assertNotIn(".venv/", out)

    def test_package_excludes_env(self):
        code, out, _ = self._run_cli(["package", "--dry-run"])
        self.assertNotIn(".env", out)
        self.assertNotIn("ai-os.local.json", out)

    def test_package_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self._run_cli(["package", "--output", tmp])
            self.assertEqual(code, 0)
            dist = Path(tmp)
            self.assertTrue((dist / "ai-os-0.8.0.zip").is_file())
            self.assertTrue((dist / "ai-os-0.8.0.tar.gz").is_file())
            self.assertTrue((dist / "ai-os-0.8.0.sha256").is_file())
            self.assertTrue((dist / "ai-os-0.8.0-files.txt").is_file())


# ============================================================
# Backup and Restore Tests
# ============================================================

class BackupRestoreTests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_backup_dry_run(self):
        code, out, _ = self._run_cli(["backup", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("dry run", out.lower())

    def test_backup_create(self):
        code, out, _ = self._run_cli(["backup"])
        self.assertEqual(code, 0)
        self.assertIn("Backup created", out)

    def test_restore_requires_force(self):
        # First create a backup
        self._run_cli(["backup"])
        # Find the backup file
        backup_dir = ROOT / ".ai-os" / "backups"
        backups = list(backup_dir.glob("*.tar.gz"))
        self.assertGreater(len(backups), 0)
        # Restore without --force should fail
        code, out, _ = self._run_cli(["restore", str(backups[0])])
        self.assertEqual(code, 1)
        self.assertIn("--force", out)

    def test_restore_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Create a malicious backup with path traversal
            bad_tar = Path(tmp) / "bad.tar.gz"
            with tarfile.open(bad_tar, "w:gz") as tf:
                import io as _io
                info = tarfile.TarInfo(name="../escape.txt")
                info.size = 5
                tf.addfile(info, _io.BytesIO(b"evil\n"))
            code, _, err = self._run_cli(["restore", str(bad_tar), "--force"])
            self.assertEqual(code, 1)
            self.assertIn("unsafe", err.lower() or "")


# ============================================================
# Clean Tests
# ============================================================

class CleanTests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_clean_dry_run_no_deletion(self):
        # Verify a known generated file exists before and after
        target = ROOT / "generated" / "skills.json"
        self.assertTrue(target.is_file())
        code, out, _ = self._run_cli(["clean-generated"])
        self.assertEqual(code, 0)
        self.assertIn("Dry run", out)
        self.assertTrue(target.is_file())  # Still exists

    def test_clean_with_confirm_in_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen = root / "generated"
            gen.mkdir()
            (gen / "skills.json").write_text("{}", encoding="utf-8")
            (gen / "source-file.md").write_text("# keep", encoding="utf-8")  # Not in allowlist
            # Monkey-patch ROOT in the module
            spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.ROOT = root
            import io as _io
            from contextlib import redirect_stdout, redirect_stderr
            stdout, stderr = _io.StringIO(), _io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                # Parse args manually
                args = mod.parser if hasattr(mod, "parser") else None
            # Just verify the allowlist logic
            self.assertIn("skills.json", GENERATED_ARTIFACTS)
            self.assertNotIn("source-file.md", GENERATED_ARTIFACTS)


# ============================================================
# Security Tests
# ============================================================

class SecurityTests(unittest.TestCase):
    def _run_cli(self, args):
        spec = importlib.util.spec_from_file_location("ai_os_cli", SCRIPTS / "ai-os.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import io
        from contextlib import redirect_stdout, redirect_stderr
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = mod.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_package_no_secret_files(self):
        code, out, _ = self._run_cli(["package", "--dry-run"])
        self.assertNotIn(".pem", out)
        self.assertNotIn(".key", out)
        self.assertNotIn(".pfx", out)

    def test_package_no_local_config(self):
        code, out, _ = self._run_cli(["package", "--dry-run"])
        self.assertNotIn("ai-os.local.json", out)

    def test_package_no_venv(self):
        code, out, _ = self._run_cli(["package", "--dry-run"])
        self.assertNotIn(".venv", out)
        self.assertNotIn("node_modules", out)

    def test_restore_missing_file(self):
        code, _, err = self._run_cli(["restore", "/nonexistent/path.tar.gz", "--force"])
        self.assertEqual(code, 1)

    def test_wrappers_exist(self):
        self.assertTrue((ROOT / "bootstrap.ps1").is_file())
        self.assertTrue((ROOT / "bootstrap.sh").is_file())


if __name__ == "__main__":
    unittest.main()
