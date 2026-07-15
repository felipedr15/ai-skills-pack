import importlib.util
import io
import json
import subprocess
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _run_cli(args):
    spec = importlib.util.spec_from_file_location("ai_os_cli_phase8", SCRIPTS / "ai-os.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = mod.main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def _snapshot_runtime_files():
    runtime = ROOT / ".ai-os"
    if not runtime.is_dir():
        return set()
    return set(runtime.rglob("*"))


class RuntimeStateCleanupMixin:
    """Snapshot/restore .ai-os/ so tests never leave local runtime state behind.

    `knowledge-gaps` intentionally records a 'knowledge-gap-detected' audit
    event even though it's otherwise a read command — so every test class
    here uses this cleanup, not just the ones that obviously mutate state.
    """

    def setUp(self):
        self._before = _snapshot_runtime_files()

    def tearDown(self):
        after = _snapshot_runtime_files()
        for path in sorted(after - self._before, key=lambda p: -len(str(p))):
            # Best-effort cleanup: on Windows, a file handle can transiently
            # linger just after a write (antivirus/indexing), racing an
            # immediate unlink/rmdir. Retry briefly rather than failing the
            # test on cleanup (the assertions above already ran).
            for attempt in range(5):
                try:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir() and not any(path.iterdir()):
                        path.rmdir()
                    break
                except OSError:
                    if attempt == 4:
                        break
                    time.sleep(0.05)


class ReadOnlyCommandTests(RuntimeStateCleanupMixin, unittest.TestCase):
    """These commands never modify generated/ or source documents."""

    def test_classify_command(self):
        code, out, _ = _run_cli(["classify", "Fix the login bug"])
        self.assertEqual(code, 0)
        self.assertIn("bug-fix", out)

    def test_classify_json(self):
        code, out, _ = _run_cli(["classify", "Fix the login bug", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["intent"], "bug-fix")

    def test_plan_command(self):
        code, out, _ = _run_cli(["plan", "Fix the login bug", "--no-history"])
        self.assertEqual(code, 0)
        self.assertIn("Workflow: workflow:bug-fix", out)

    def test_plan_json(self):
        code, out, _ = _run_cli(["plan", "Fix the login bug", "--no-history", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["selectedWorkflow"]["id"], "workflow:bug-fix")

    def test_workflow_list(self):
        code, out, _ = _run_cli(["workflow", "list"])
        self.assertEqual(code, 0)
        self.assertIn("workflow:bug-fix", out)

    def test_workflow_show_unknown_errors_cleanly(self):
        code, _out, err = _run_cli(["workflow", "show", "workflow:does-not-exist"])
        self.assertEqual(code, 1)
        self.assertIn("not found", err)

    def test_knowledge_health_command(self):
        code, out, _ = _run_cli(["knowledge-health"])
        self.assertEqual(code, 0)
        self.assertIn("Overall knowledge health score", out)

    def test_knowledge_gaps_command(self):
        code, out, _ = _run_cli(["knowledge-gaps"])
        self.assertEqual(code, 0)
        self.assertIn("Overall score", out)

    def test_review_due_command(self):
        code, out, _ = _run_cli(["review-due"])
        self.assertEqual(code, 0)

    def test_help_lists_phase8_commands(self):
        code, out, _ = _run_cli(["help"])
        self.assertEqual(code, 0)
        self.assertIn("plan", out)
        self.assertIn("session", out)
        self.assertIn("audit", out)

    def test_no_git_mutation_from_read_only_commands(self):
        before = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(ROOT)).stdout
        _run_cli(["plan", "Fix the login bug", "--no-history"])
        _run_cli(["knowledge-health"])
        after = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=str(ROOT)).stdout
        self.assertEqual(before, after)


class MutatingCommandTests(RuntimeStateCleanupMixin, unittest.TestCase):
    """These commands write to the local, git-ignored .ai-os/ directory.

    RuntimeStateCleanupMixin snapshots and restores that directory so the
    real repo's runtime state is left exactly as found.
    """

    def test_session_lifecycle_via_cli(self):
        code, out, _ = _run_cli(["session", "start", "Fix the CLI test login bug", "--json"])
        self.assertEqual(code, 0)
        session = json.loads(out)
        session_id = session["sessionId"]

        code, out, _ = _run_cli(["session", "list", "--json"])
        self.assertEqual(code, 0)
        sessions = json.loads(out)
        self.assertTrue(any(s["sessionId"] == session_id for s in sessions))

        code, out, _ = _run_cli(["session", "validate", session_id, "--name", "unit-tests", "--status", "pass"])
        self.assertEqual(code, 0)

        code, out, _ = _run_cli(["session", "complete", session_id])
        self.assertEqual(code, 0)
        self.assertIn("Session completed", out)

        code, out, _ = _run_cli(["session", "archive", session_id])
        self.assertEqual(code, 0)

    def test_approval_workflow_via_cli(self):
        code, out, _ = _run_cli(["session", "start", "Fix the CLI approval test bug", "--json"])
        self.assertEqual(code, 0)

        code, out, _ = _run_cli(["approval", "list", "--status", "pending", "--json"])
        self.assertEqual(code, 0)
        pending = json.loads(out)
        self.assertTrue(pending)
        approval_id = pending[0]["approvalId"]

        code, out, _ = _run_cli(["approval", "approve", approval_id])
        self.assertEqual(code, 0)
        self.assertIn("Approved", out)

    def test_feedback_cli(self):
        code, out, _ = _run_cli([
            "feedback", "add", "--type", "helpful", "--target-type", "skill", "--target-id", "analytical",
        ])
        self.assertEqual(code, 0)
        self.assertIn("Feedback recorded", out)

        code, out, _ = _run_cli(["feedback", "stats", "--json"])
        self.assertEqual(code, 0)
        stats = json.loads(out)
        self.assertGreaterEqual(stats["total"], 1)

    def test_audit_validate_cli(self):
        _run_cli(["feedback", "add", "--type", "helpful", "--target-type", "skill", "--target-id", "analytical"])
        code, out, _ = _run_cli(["audit", "list"])
        self.assertEqual(code, 0)

    def test_session_complete_blocked_without_validation(self):
        code, out, _ = _run_cli(["session", "start", "Fix the CLI blocked test bug", "--json"])
        session = json.loads(out)
        code, _out, err = _run_cli(["session", "complete", session["sessionId"]])
        self.assertEqual(code, 1)
        self.assertIn("must be in 'validation' status", err)

    def test_no_arbitrary_command_execution(self):
        # Feedback/session commands must not accept or execute shell strings.
        code, out, _ = _run_cli([
            "feedback", "add", "--type", "helpful", "--target-type", "skill",
            "--target-id", "analytical", "--comment", "; rm -rf / #",
        ])
        self.assertEqual(code, 0)
        # The comment is stored as inert text, never executed.
        marker = ROOT / "PWNED_MARKER_SHOULD_NOT_EXIST"
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
