import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_all", ROOT / "scripts/validate-all.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidationTests(unittest.TestCase):
    def test_success_exit_code(self):
        results = validator.Results()
        results.pass_("ok")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(results.report(), 0)

    def test_failure_exit_code_and_warning_behavior(self):
        results = validator.Results()
        results.warning("review")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(results.report(), 0)
        results.fail("broken")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(results.report(), 1)


if __name__ == "__main__":
    unittest.main()
