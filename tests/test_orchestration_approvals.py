import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration import approvals


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_approval_is_pending(self):
        approval = approvals.request_approval(self.root, approval_type="plan", target="session-1", reason="test")
        self.assertEqual(approval["status"], "pending")
        self.assertIsNone(approval["approvedAt"])
        self.assertIsNone(approval["approvedBy"])

    def test_approve_pending(self):
        approval = approvals.request_approval(self.root, approval_type="plan", target="session-1")
        approved = approvals.approve(self.root, approval["approvalId"])
        self.assertEqual(approved["status"], "approved")
        self.assertIsNotNone(approved["approvedAt"])

    def test_reject_pending(self):
        approval = approvals.request_approval(self.root, approval_type="plan", target="session-1")
        rejected = approvals.reject(self.root, approval["approvalId"], reason="not needed")
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["reason"], "not needed")

    def test_no_implicit_approval_on_creation(self):
        approvals.request_approval(self.root, approval_type="permanent-memory", target="suggestion-1")
        self.assertFalse(approvals.is_approved(self.root, approval_type="permanent-memory", target="suggestion-1"))

    def test_cannot_approve_already_approved(self):
        approval = approvals.request_approval(self.root, approval_type="plan", target="session-1")
        approvals.approve(self.root, approval["approvalId"])
        with self.assertRaises(approvals.ApprovalError):
            approvals.approve(self.root, approval["approvalId"])

    def test_history_preserved_after_decision(self):
        approval = approvals.request_approval(self.root, approval_type="plan", target="session-1")
        approvals.reject(self.root, approval["approvalId"])
        all_approvals = approvals.list_approvals(self.root)
        self.assertEqual(len(all_approvals), 1)
        self.assertEqual(all_approvals[0]["status"], "rejected")

    def test_invalid_type_rejected(self):
        with self.assertRaises(approvals.ApprovalError):
            approvals.request_approval(self.root, approval_type="not-a-real-type", target="x")

    def test_get_unknown_approval_raises(self):
        with self.assertRaises(approvals.ApprovalError):
            approvals.get_approval(self.root, "approval-does-not-exist-001")

    def test_list_filters_by_status(self):
        a1 = approvals.request_approval(self.root, approval_type="plan", target="s1")
        approvals.request_approval(self.root, approval_type="plan", target="s2")
        approvals.approve(self.root, a1["approvalId"])
        pending = approvals.list_approvals(self.root, status="pending")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["target"], "s2")

    def test_is_approved_true_only_after_explicit_approve(self):
        approval = approvals.request_approval(self.root, approval_type="permanent-memory", target="suggestion-1")
        self.assertFalse(approvals.is_approved(self.root, approval_type="permanent-memory", target="suggestion-1"))
        approvals.approve(self.root, approval["approvalId"])
        self.assertTrue(approvals.is_approved(self.root, approval_type="permanent-memory", target="suggestion-1"))


if __name__ == "__main__":
    unittest.main()
