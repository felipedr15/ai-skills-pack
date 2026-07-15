import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration import feedback


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_feedback(self):
        entry = feedback.add_feedback(
            self.root, feedback_type="outdated", target_type="document",
            target_id="knowledge/sharepoint/README.md", comment="This is stale.")
        self.assertEqual(entry["status"], "open")
        self.assertTrue(entry["feedbackId"].startswith("feedback-"))

    def test_list_feedback(self):
        feedback.add_feedback(self.root, feedback_type="helpful", target_type="skill", target_id="analytical")
        feedback.add_feedback(self.root, feedback_type="incorrect", target_type="skill", target_id="testing")
        entries = feedback.list_feedback(self.root)
        self.assertEqual(len(entries), 2)

    def test_resolve_feedback(self):
        entry = feedback.add_feedback(self.root, feedback_type="helpful", target_type="skill", target_id="analytical")
        resolved = feedback.resolve_feedback(self.root, entry["feedbackId"])
        self.assertEqual(resolved["status"], "resolved")

    def test_stats(self):
        feedback.add_feedback(self.root, feedback_type="helpful", target_type="skill", target_id="a")
        feedback.add_feedback(self.root, feedback_type="incorrect", target_type="skill", target_id="b")
        stats = feedback.feedback_stats(self.root)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["open"], 2)
        self.assertEqual(stats["byType"]["helpful"], 1)

    def test_invalid_type_rejected(self):
        with self.assertRaises(feedback.FeedbackError):
            feedback.add_feedback(self.root, feedback_type="not-a-type", target_type="skill", target_id="a")

    def test_comment_sanitized_of_control_characters(self):
        entry = feedback.add_feedback(
            self.root, feedback_type="helpful", target_type="skill", target_id="a",
            comment="line1\x00\x07line2")
        self.assertNotIn("\x00", entry["comment"])
        self.assertNotIn("\x07", entry["comment"])

    def test_comment_secret_redacted(self):
        entry = feedback.add_feedback(
            self.root, feedback_type="helpful", target_type="skill", target_id="a",
            comment="password=abcdefghijklmnopqrst12345")
        self.assertNotIn("abcdefghijklmnopqrst12345", entry["comment"])

    def test_no_telemetry_network_calls(self):
        # add_feedback must be a pure local file operation; verify the module
        # has no networking imports.
        import inspect
        source = inspect.getsource(feedback)
        for banned in ("requests", "urllib.request", "http.client", "socket"):
            self.assertNotIn(banned, source)

    def test_get_unknown_feedback_raises(self):
        with self.assertRaises(feedback.FeedbackError):
            feedback.get_feedback(self.root, "feedback-does-not-exist-001")


if __name__ == "__main__":
    unittest.main()
