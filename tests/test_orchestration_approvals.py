import json
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

    def test_malformed_approval_record_does_not_crash_read_operations(self):
        store_path = self.root / ".ai-os" / "approvals" / "approvals.json"
        store_path.parent.mkdir(parents=True)
        store_path.write_text(json.dumps([{"status": "approved"}, "not-a-record"]), encoding="utf-8")

        self.assertEqual(len(approvals.list_approvals(self.root)), 2)
        self.assertFalse(approvals.is_approved(self.root, approval_type="plan", target="session-1"))
        with self.assertRaises(approvals.ApprovalError):
            approvals.get_approval(self.root, "approval-missing-001")

    def test_request_approval_preserves_malformed_records_and_generates_id(self):
        store_path = self.root / ".ai-os" / "approvals" / "approvals.json"
        store_path.parent.mkdir(parents=True)
        store_path.write_text(
            json.dumps([
                {"approvalId": "approval-session-001", "status": "approved"},
                {"target": "session-2"},
            ]),
            encoding="utf-8",
        )

        approval = approvals.request_approval(self.root, approval_type="plan", target="session")
        data = json.loads(store_path.read_text(encoding="utf-8"))

        self.assertEqual(approval["approvalId"], "approval-session-002")
        self.assertEqual(len(data), 3)
        self.assertEqual(data[1], {"target": "session-2"})


class ProfileApprovalTypeTests(unittest.TestCase):
    """Task 014: profile-write, expertise-write, and profile-switch are
    recognized by the same, unmodified approval engine used by every prior
    Phase 8 approval type -- no parallel/duplicate approval mechanism.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_profile_approval_types_recognized(self):
        for approval_type in ("profile-write", "expertise-write", "profile-switch"):
            approval = approvals.request_approval(self.root, approval_type=approval_type, target="primary")
            self.assertEqual(approval["type"], approval_type)
            self.assertEqual(approval["status"], "pending")

    def test_existing_phase8_approval_types_still_recognized(self):
        for approval_type in ("plan", "permanent-memory", "source-modification"):
            approval = approvals.request_approval(self.root, approval_type=approval_type, target="x")
            self.assertEqual(approval["type"], approval_type)

    def test_matching_type_and_target_succeeds(self):
        approval = approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        approvals.approve(self.root, approval["approvalId"])
        self.assertTrue(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))

    def test_wrong_target_profile_fails(self):
        approval = approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        approvals.approve(self.root, approval["approvalId"])
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-switch", target="secondary"))

    def test_wrong_operation_type_fails(self):
        # An approval scoped to profile-switch must not authorize profile-write
        # or expertise-write for the same profile id, and vice versa.
        approval = approvals.request_approval(self.root, approval_type="profile-write", target="primary")
        approvals.approve(self.root, approval["approvalId"])
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))
        self.assertFalse(approvals.is_approved(self.root, approval_type="expertise-write", target="primary"))

    def test_expertise_write_does_not_authorize_arbitrary_profile_write(self):
        approval = approvals.request_approval(self.root, approval_type="expertise-write", target="primary")
        approvals.approve(self.root, approval["approvalId"])
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-write", target="primary"))

    def test_invalid_profile_approval_type_rejected(self):
        with self.assertRaises(approvals.ApprovalError):
            approvals.request_approval(self.root, approval_type="profile-delete", target="primary")

    def test_rejected_profile_approval_fails(self):
        approval = approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        approvals.reject(self.root, approval["approvalId"])
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))

    def test_missing_profile_approval_fails(self):
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))

    def test_non_approved_status_never_satisfies_is_approved(self):
        # No expiry-triggering mechanism exists yet anywhere in this engine
        # (Phase 8 or 9); this proves is_approved()'s status check already
        # fails closed for any status other than 'approved' -- including a
        # hypothetical future 'expired' status -- without requiring new
        # expiry-triggering code as part of this task group.
        approval = approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        store_path = self.root / ".ai-os" / "approvals" / "approvals.json"
        data = json.loads(store_path.read_text(encoding="utf-8"))
        for entry in data:
            if entry["approvalId"] == approval["approvalId"]:
                entry["status"] = "expired"
        store_path.write_text(json.dumps(data), encoding="utf-8")
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))

    def test_profile_approval_is_reusable_not_single_use(self):
        # Matches existing Phase 8 convention: the engine has no consumption
        # concept, so an approved approval remains valid across repeated
        # checks (e.g. idempotent profile switches to the same target).
        approval = approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        approvals.approve(self.root, approval["approvalId"])
        self.assertTrue(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))
        self.assertTrue(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))

    def test_cannot_approve_already_approved_profile_switch(self):
        approval = approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        approvals.approve(self.root, approval["approvalId"])
        with self.assertRaises(approvals.ApprovalError):
            approvals.approve(self.root, approval["approvalId"])

    def test_no_self_approval_request_creation_never_implies_approval(self):
        approvals.request_approval(self.root, approval_type="profile-switch", target="primary")
        self.assertFalse(approvals.is_approved(self.root, approval_type="profile-switch", target="primary"))


if __name__ == "__main__":
    unittest.main()
