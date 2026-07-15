import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration import audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_and_list(self):
        audit.append_event(self.root, "workflow-selected", details={"workflowId": "workflow:bug-fix"})
        events = audit.list_events(self.root)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "workflow-selected")

    def test_chain_valid_after_multiple_appends(self):
        for event_type in ("workflow-selected", "agent-selected", "session-completed"):
            audit.append_event(self.root, event_type)
        valid, errors = audit.validate_chain(self.root)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_tamper_detected(self):
        audit.append_event(self.root, "workflow-selected", details={"workflowId": "workflow:bug-fix"})
        log_path = next((self.root / ".ai-os" / "audit").glob("*.log"))
        line = json.loads(log_path.read_text().strip())
        line["details"]["workflowId"] = "workflow:tampered"
        log_path.write_text(json.dumps(line) + "\n", encoding="utf-8")
        valid, errors = audit.validate_chain(self.root)
        self.assertFalse(valid)
        self.assertTrue(errors)

    def test_unknown_event_type_rejected(self):
        with self.assertRaises(audit.AuditError):
            audit.append_event(self.root, "not-a-real-event")

    def test_export_writes_bundle(self):
        audit.append_event(self.root, "workflow-selected")
        dest = self.root / "export.json"
        path = audit.export_events(self.root, dest)
        self.assertTrue(path.is_file())
        exported = json.loads(path.read_text())
        self.assertEqual(len(exported), 1)

    def test_rotation_creates_new_file_past_limit(self):
        from orchestration import AUDIT_MAX_ENTRIES_PER_FILE
        for _ in range(AUDIT_MAX_ENTRIES_PER_FILE + 5):
            audit.append_event(self.root, "workflow-selected")
        log_files = audit._log_files(self.root)
        self.assertGreaterEqual(len(log_files), 2)

    def test_summary_reports_counts_and_chain_validity(self):
        audit.append_event(self.root, "workflow-selected")
        audit.append_event(self.root, "workflow-selected")
        summary = audit.summary(self.root)
        self.assertEqual(summary["totalEvents"], 2)
        self.assertEqual(summary["byType"]["workflow-selected"], 2)
        self.assertTrue(summary["chainValid"])

    def test_no_secret_content_recorded(self):
        audit.append_event(self.root, "validation-run", details={"note": "password=abcdefghijklmnopqrst12345"})
        events = audit.list_events(self.root)
        self.assertNotIn("abcdefghijklmnopqrst12345", json.dumps(events))

    def test_no_raw_dict_values_recorded(self):
        # Nested dict values must be dropped, not persisted, to avoid
        # accidentally logging full file contents or memory bodies.
        audit.append_event(self.root, "validation-run", details={"nested": {"secret": "value"}})
        events = audit.list_events(self.root)
        self.assertNotIn("nested", events[0]["details"])


if __name__ == "__main__":
    unittest.main()
