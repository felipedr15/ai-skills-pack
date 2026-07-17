"""Tests for scripts/profile/sanitize.py (Task 011)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from profile.sanitize import SanitizationError, assert_sanitized, find_prohibited


class CleanContentTests(unittest.TestCase):
    def test_clean_content_passes(self):
        assert_sanitized("This is a normal, safe overview about IT support work.")

    def test_placeholder_text_is_exempt(self):
        assert_sanitized("Example: <role> at example@example.com is a placeholder.")


class ProhibitedContentBlocksWriteTests(unittest.TestCase):
    def test_phone_number(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Call 555-123-4567 for details.")

    def test_personal_email(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Reach me at jane.doe@county.gov")

    def test_zip_code(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Home zip code: 90210")

    def test_street_address(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Lives at 123 Maple Street")

    def test_employee_id(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Employee ID: E-12345")

    def test_password(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("password: SuperSecret123!")

    def test_api_key(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("API_KEY: sk-abcdef1234567890abcdef")

    def test_generic_secret(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("secret: abcdef1234567890")

    def test_ssn(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("SSN 123-45-6789 on file")

    def test_internal_ip_address(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("internal server at 10.20.30.40")

    def test_reviewer_or_signature(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Reviewed by: Jane Smith")

    def test_raw_resume_marker(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("See attached curriculum vitae for details.")

    def test_raw_performance_evaluation_marker(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("Performance evaluation score attached.")

    def test_confidential_or_county_security_marker(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("This is County Security confidential information.")

    def test_private_key(self):
        with self.assertRaises(SanitizationError):
            assert_sanitized("-----BEGIN RSA PRIVATE KEY-----\nMIIEow==\n")


class NoLeakageTests(unittest.TestCase):
    """Prohibited values must never appear in findings, error messages, or
    anything a caller might log."""

    def test_error_message_never_contains_raw_value(self):
        try:
            assert_sanitized("password: SuperSecretValue123!")
            self.fail("expected SanitizationError")
        except SanitizationError as exc:
            self.assertNotIn("SuperSecretValue123", str(exc))

    def test_error_message_names_pattern_not_value(self):
        try:
            assert_sanitized("Reach me at jane.doe@county.gov")
            self.fail("expected SanitizationError")
        except SanitizationError as exc:
            self.assertIn("email-address", str(exc))
            self.assertNotIn("jane.doe", str(exc))

    def test_findings_never_expose_raw_value(self):
        findings = find_prohibited("password: SuperSecretValue123!")
        for _name, masked in findings:
            self.assertNotIn("SuperSecretValue123", masked)

    def test_findings_never_expose_raw_email(self):
        findings = find_prohibited("Contact jane.doe@county.gov now")
        for _name, masked in findings:
            self.assertNotIn("jane.doe@county.gov", masked)


if __name__ == "__main__":
    unittest.main()
