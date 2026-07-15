import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration import approvals, memory_suggestions


def _make_repo(root: Path, memory_records=None):
    (root / "memory" / "lessons").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "registry.json").write_text(
        json.dumps({"schemaVersion": "1.0.0", "records": []}), encoding="utf-8")
    (root / "generated").mkdir(parents=True, exist_ok=True)
    (root / "generated" / "memory-index.json").write_text(
        json.dumps({"records": memory_records or []}), encoding="utf-8")


def _session(status="completed", passed=True, project=None):
    return {
        "sessionId": "session-test-001",
        "task": "Fix the login bug where sessions expire early",
        "project": project,
        "status": status,
        "failures": [] if passed else [{"reason": "validation failed"}],
        "validations": [{"name": "unit-tests", "passed": passed, "detail": "all green"}],
        "knowledgeUsed": [{"id": "doc:1"}],
    }


class MemorySuggestionGenerationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_generate_creates_pending_suggestion(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        self.assertEqual(suggestion["status"], "pending")
        self.assertTrue(suggestion["id"].startswith("memory-suggestion-"))

    def test_high_confidence_for_completed_session_with_passing_validation(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        self.assertGreaterEqual(suggestion["confidence"], 0.5)

    def test_low_confidence_warning_for_incomplete_session(self):
        session = _session(status="active", passed=False)
        suggestion = memory_suggestions.generate_suggestion(self.root, session)
        self.assertLess(suggestion["confidence"], 0.5)
        self.assertTrue(any("low-confidence" in r for r in suggestion["reasons"]))

    def test_duplicate_detection_against_existing_memory(self):
        _make_repo(self.root, memory_records=[{
            "id": "lesson-existing-001",
            "title": "Fix the login bug where sessions expire early",
            "summary": "Fix the login bug where sessions expire early",
        }])
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        self.assertTrue(suggestion["duplicates"])
        self.assertEqual(suggestion["duplicates"][0]["id"], "lesson-existing-001")

    def test_no_full_transcript_stored(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        self.assertNotIn("transcript", suggestion)
        self.assertLessEqual(len(suggestion["problem"]), 500)

    def test_no_secret_content(self):
        session = _session()
        session["task"] = "Investigate api_key=abcdefghijklmnopqrst12345 leak"
        suggestion = memory_suggestions.generate_suggestion(self.root, session)
        self.assertNotIn("abcdefghijklmnopqrst12345", json.dumps(suggestion))


class MemorySuggestionApprovalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _make_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def test_approve_requires_approval_record(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        with self.assertRaises(approvals.ApprovalError):
            memory_suggestions.approve(self.root, suggestion["id"])

    def test_approve_succeeds_after_explicit_approval(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        approval = approvals.request_approval(
            self.root, approval_type="permanent-memory", target=suggestion["id"])
        approvals.approve(self.root, approval["approvalId"])
        result = memory_suggestions.approve(self.root, suggestion["id"])
        self.assertEqual(result["status"], "approved")
        registry = json.loads((self.root / "memory" / "registry.json").read_text())
        self.assertEqual(len(registry["records"]), 1)

    def test_approved_memory_path_stays_under_memory_dir(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        self.assertTrue(suggestion["proposedPath"].startswith("memory/"))

    def test_reject_marks_status_rejected(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        result = memory_suggestions.reject(self.root, suggestion["id"], reason="not useful")
        self.assertEqual(result["status"], "rejected")

    def test_export_writes_file(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        dest = self.root / "export.json"
        path = memory_suggestions.export_suggestion(self.root, suggestion["id"], dest)
        self.assertTrue(path.is_file())
        exported = json.loads(path.read_text())
        self.assertEqual(exported["id"], suggestion["id"])

    def test_cannot_approve_twice(self):
        suggestion = memory_suggestions.generate_suggestion(self.root, _session())
        approval = approvals.request_approval(
            self.root, approval_type="permanent-memory", target=suggestion["id"])
        approvals.approve(self.root, approval["approvalId"])
        memory_suggestions.approve(self.root, suggestion["id"])
        with self.assertRaises(memory_suggestions.MemorySuggestionError):
            memory_suggestions.approve(self.root, suggestion["id"])


if __name__ == "__main__":
    unittest.main()
