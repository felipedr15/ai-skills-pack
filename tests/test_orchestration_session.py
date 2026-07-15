import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration import session
from orchestration.planner import create_plan


class SessionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _plan(self):
        return create_plan(ROOT, "Fix the login bug", no_history=True)

    def test_create_session_defaults_to_planned(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        self.assertEqual(created["status"], "planned")
        self.assertTrue(created["sessionId"].startswith("session-"))

    def test_create_session_writes_local_only(self):
        session.create_session(self.root, "Fix the login bug", plan=self._plan())
        session_dir = self.root / ".ai-os" / "sessions"
        self.assertTrue(session_dir.is_dir())
        files = list(session_dir.glob("*.json"))
        self.assertEqual(len(files), 1)

    def test_list_sessions(self):
        session.create_session(self.root, "Fix the login bug", plan=self._plan())
        session.create_session(self.root, "Add dark mode", plan=self._plan())
        sessions = session.list_sessions(self.root)
        self.assertEqual(len(sessions), 2)

    def test_show_session(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        fetched = session.get_session(self.root, created["sessionId"])
        self.assertEqual(fetched["sessionId"], created["sessionId"])

    def test_valid_transition_sequence(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        sid = created["sessionId"]
        session.transition_status(self.root, sid, "approved")
        session.transition_status(self.root, sid, "active")
        session.transition_status(self.root, sid, "validation")
        result = session.transition_status(self.root, sid, "completed")
        self.assertEqual(result["status"], "completed")

    def test_invalid_transition_rejected(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        with self.assertRaises(session.SessionError):
            session.transition_status(self.root, created["sessionId"], "completed")

    def test_archive_terminal_state_has_no_further_transitions(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        sid = created["sessionId"]
        session.transition_status(self.root, sid, "cancelled")
        session.transition_status(self.root, sid, "archived")
        with self.assertRaises(session.SessionError):
            session.transition_status(self.root, sid, "active")

    def test_advance_toward_stops_if_blocked(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        sid = created["sessionId"]
        session.transition_status(self.root, sid, "cancelled")
        result = session.advance_toward(self.root, sid, "completed")
        self.assertEqual(result["status"], "cancelled")

    def test_bounded_list_size(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        session.record_files_observed(self.root, created["sessionId"], [f"file-{i}.py" for i in range(500)])
        result = session.get_session(self.root, created["sessionId"])
        from orchestration import MAX_LIST_ITEMS
        self.assertLessEqual(len(result["filesObserved"]), MAX_LIST_ITEMS)

    def test_no_secrets_persisted_in_task_text(self):
        plan = create_plan(ROOT, "Investigate api_key=abcdefghijklmnopqrst12345 leak", no_history=True)
        created = session.create_session(self.root, "Investigate api_key=abcdefghijklmnopqrst12345 leak", plan=plan)
        self.assertNotIn("abcdefghijklmnopqrst12345", created["task"])

    def test_no_full_transcript_field(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        self.assertNotIn("transcript", created)
        self.assertNotIn("chatHistory", created)

    def test_session_path_is_local_only(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        path = self.root / ".ai-os" / "sessions" / f"{created['sessionId']}.json"
        self.assertTrue(str(path).startswith(str(self.root)))

    def test_record_validation_tracks_failures(self):
        created = session.create_session(self.root, "Fix the login bug", plan=self._plan())
        sid = created["sessionId"]
        session.advance_toward(self.root, sid, "active")
        result = session.record_validation(self.root, sid, name="unit-tests", passed=False, detail="2 tests failed")
        self.assertEqual(len(result["failures"]), 1)


if __name__ == "__main__":
    unittest.main()
