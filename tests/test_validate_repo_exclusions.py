import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_repo", ROOT / "scripts/validate-repo.py")
validate_repo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_repo)


class ValidateRepoExclusionTests(unittest.TestCase):
    def test_secret_scan_excludes_venv_but_scans_repo_files(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".venv" / "Lib" / "site-packages" / "pkg").mkdir(parents=True)
            (root / ".venv" / "Lib" / "site-packages" / "pkg" / "module.py").write_text(
                'api_key = "0123456789ABCDEF0123"\n',
                encoding="utf-8",
            )
            (root / "scripts").mkdir(parents=True)
            (root / "scripts" / "app.py").write_text(
                'client_secret = "ABCDEFGHIJKLMNOPQRSTUV"\n',
                encoding="utf-8",
            )

            old_root = validate_repo.ROOT
            old_failures = validate_repo.failures
            old_warnings = validate_repo.warnings
            old_passes = validate_repo.passes
            try:
                validate_repo.ROOT = root
                validate_repo.failures = []
                validate_repo.warnings = []
                validate_repo.passes = []
                validate_repo.validate_secret_patterns()
                self.assertEqual(len(validate_repo.failures), 1)
                self.assertIn("scripts/app.py", validate_repo.failures[0].replace("\\", "/"))
                self.assertNotIn(".venv", validate_repo.failures[0])
            finally:
                validate_repo.ROOT = old_root
                validate_repo.failures = old_failures
                validate_repo.warnings = old_warnings
                validate_repo.passes = old_passes


if __name__ == "__main__":
    unittest.main()
