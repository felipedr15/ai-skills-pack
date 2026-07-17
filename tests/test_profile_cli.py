"""CLI dispatch tests for `ai-os.py profile {list,show,switch}` (Task 012,
Task 013) and their approval-gated integration (Task 014).

Mutating scenarios never run against the real repository: `_run_cli_at`
loads a fresh copy of scripts/ai-os.py and monkeypatches its module-level
`ROOT` constant to an isolated temporary directory before calling `main()`,
so `profile switch` and approval requests never touch this repo's real
profile/registry.json or .ai-os/ state. Read-only smoke tests against the
real repository (`_run_cli`) are restricted to paths that are safe given
the real registry is currently empty (no profile has been authored).
"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from profile import SCHEMA_VERSION  # noqa: E402


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("ai_os_cli_phase9_profile", SCRIPTS / "ai-os.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_cli(args):
    """Run against the REAL repository root. Only ever use with commands
    that are safe given the real profile/registry.json is currently empty."""
    mod = _load_cli_module()
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = mod.main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def _run_cli_at(root, args):
    """Run against an isolated temporary root -- never the real repository."""
    mod = _load_cli_module()
    mod.ROOT = root
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = mod.main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def _valid_registry_entry(profile_id="primary", active=True):
    return {"id": profile_id, "path": f"profile/{profile_id}.md", "active": active, "createdAt": "2026-07-15T00:00:00Z"}


def _valid_profile_metadata(profile_id="primary"):
    return {
        "id": profile_id,
        "schemaVersion": "1.0.0",
        "role": "Senior IT Technical Support Analyst",
        "team": "IT Support",
        "responsibilities": ["Tier 2/3 support", "Windows 11 deployment"],
        "reportingTo": "it-manager",
        "sensitivity": "high",
        "createdAt": "2026-07-15",
        "updatedAt": "2026-07-15",
    }


def _write_profile_record_file(root: Path, metadata: dict, body: str = "# Primary Professional Profile\n") -> Path:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
            if not value:
                lines[-1] = f"{key}: []"
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    text = "\n".join(lines) + "\n" + body
    path = root / "profile" / f"{metadata['id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _seed_registry(root, entries):
    from profile import registry as profile_registry
    profile_registry.save_registry(root, {"schemaVersion": SCHEMA_VERSION, "profiles": entries})


def _snapshot_files(root: Path):
    if not root.exists():
        return set()
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


class RealRepoSafeSmokeTests(unittest.TestCase):
    """Runs against the real repository. Every case here must remain safe
    with an empty (not-yet-authored) profile/registry.json."""

    def test_help_lists_profile_command(self):
        code, out, _ = _run_cli(["help"])
        self.assertEqual(code, 0)
        self.assertIn("profile", out)

    def test_list_on_empty_real_registry_is_safe(self):
        before = _snapshot_files(ROOT / "profile")
        code, out, _ = _run_cli(["profile", "list"])
        after = _snapshot_files(ROOT / "profile")
        self.assertEqual(code, 0)
        self.assertIn("No professional profiles configured yet", out)
        self.assertEqual(before, after)

    def test_show_on_empty_real_registry_is_safe(self):
        before = _snapshot_files(ROOT / "profile")
        code, out, _ = _run_cli(["profile", "show"])
        after = _snapshot_files(ROOT / "profile")
        self.assertEqual(code, 0)
        self.assertIn("No active professional profile", out)
        self.assertEqual(before, after)

    def test_switch_on_empty_real_registry_fails_without_mutation(self):
        before = _snapshot_files(ROOT / "profile")
        code, _out, err = _run_cli(["profile", "switch", "primary"])
        after = _snapshot_files(ROOT / "profile")
        self.assertEqual(code, 1)
        self.assertIn("no profiles registered", err)
        self.assertEqual(before, after)

    def test_unknown_profile_subcommand_shows_usage(self):
        code, _out, err = _run_cli(["profile"])
        self.assertEqual(code, 1)
        self.assertIn("Usage: ai-os.py profile", err)


class ReadOnlyCliTests(unittest.TestCase):
    """Task 012, isolated temp root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_list_multiple_synthetic_profiles(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True), _valid_registry_entry("secondary", False)])
        code, out, _ = _run_cli_at(self.root, ["profile", "list"])
        self.assertEqual(code, 0)
        self.assertIn("primary: [active]", out)
        self.assertIn("secondary: [inactive]", out)

    def test_list_json(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        code, out, _ = _run_cli_at(self.root, ["profile", "list", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data[0]["id"], "primary")

    def test_show_explicit_profile_id(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        _write_profile_record_file(self.root, _valid_profile_metadata("primary"))
        code, out, _ = _run_cli_at(self.root, ["profile", "show", "primary"])
        self.assertEqual(code, 0)
        self.assertIn("role: Senior IT Technical Support Analyst", out)

    def test_show_active_profile_with_no_id_argument(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        _write_profile_record_file(self.root, _valid_profile_metadata("primary"))
        code, out, _ = _run_cli_at(self.root, ["profile", "show"])
        self.assertEqual(code, 0)
        self.assertIn("id: primary", out)

    def test_show_missing_active_profile_is_safe_success(self):
        code, out, _ = _run_cli_at(self.root, ["profile", "show"])
        self.assertEqual(code, 0)
        self.assertIn("No active professional profile", out)

    def test_show_unknown_profile_id_fails_safely(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        code, _out, err = _run_cli_at(self.root, ["profile", "show", "does-not-exist"])
        self.assertEqual(code, 1)
        self.assertIn("unknown profile id", err)

    def test_show_invalid_registry_fails_safely(self):
        registry_path = self.root / "profile" / "registry.json"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(json.dumps({
            "schemaVersion": SCHEMA_VERSION,
            "profiles": [_valid_registry_entry("primary", True), _valid_registry_entry("secondary", True)],
        }), encoding="utf-8")
        code, _out, err = _run_cli_at(self.root, ["profile", "show"])
        self.assertEqual(code, 1)
        self.assertIn("invalid profile registry", err)

    def test_output_is_deterministic(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        _write_profile_record_file(self.root, _valid_profile_metadata("primary"))
        _, out1, _ = _run_cli_at(self.root, ["profile", "show", "primary"])
        _, out2, _ = _run_cli_at(self.root, ["profile", "show", "primary"])
        self.assertEqual(out1, out2)

    def test_list_and_show_perform_no_writes(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        _write_profile_record_file(self.root, _valid_profile_metadata("primary"))
        before = _snapshot_files(self.root)
        _run_cli_at(self.root, ["profile", "list"])
        _run_cli_at(self.root, ["profile", "show", "primary"])
        _run_cli_at(self.root, ["profile", "show"])
        after = _snapshot_files(self.root)
        self.assertEqual(before, after)

    def test_prose_body_never_exposed_via_show(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        _write_profile_record_file(
            self.root, _valid_profile_metadata("primary"),
            body="# Notes\nSECRET_PROSE_MARKER must never reach CLI output.\n")
        code, out, _ = _run_cli_at(self.root, ["profile", "show", "primary"])
        self.assertEqual(code, 0)
        self.assertNotIn("SECRET_PROSE_MARKER", out)


class SwitchingCliTests(unittest.TestCase):
    """Task 013 + Task 014, isolated temp root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _approve(self, target_id):
        from orchestration import approvals as orch_approvals
        pending = [a for a in orch_approvals.list_approvals(self.root, status="pending")
                   if a["type"] == "profile-switch" and a["target"] == target_id]
        self.assertTrue(pending, f"expected a pending profile-switch approval for {target_id!r}")
        orch_approvals.approve(self.root, pending[0]["approvalId"])

    def test_switch_without_approval_fails_and_requests_one(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True), _valid_registry_entry("secondary", False)])
        before = (self.root / "profile" / "registry.json").read_bytes()
        code, _out, err = _run_cli_at(self.root, ["profile", "switch", "secondary"])
        after = (self.root / "profile" / "registry.json").read_bytes()
        self.assertEqual(code, 1)
        self.assertIn("requires approval", err)
        self.assertEqual(before, after)

        from orchestration import approvals as orch_approvals
        pending = orch_approvals.list_approvals(self.root, status="pending")
        self.assertTrue(any(a["type"] == "profile-switch" and a["target"] == "secondary" for a in pending))

    def test_switch_succeeds_after_explicit_approval(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True), _valid_registry_entry("secondary", False)])
        _run_cli_at(self.root, ["profile", "switch", "secondary"])  # creates the pending approval
        self._approve("secondary")

        code, out, _ = _run_cli_at(self.root, ["profile", "switch", "secondary"])
        self.assertEqual(code, 0)
        self.assertIn("secondary", out)

        from profile import registry as profile_registry
        data = profile_registry.load_registry(self.root)
        active_ids = [p["id"] for p in data["profiles"] if p["active"]]
        self.assertEqual(active_ids, ["secondary"])

    def test_switch_to_already_active_profile_is_idempotent(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        _run_cli_at(self.root, ["profile", "switch", "primary"])
        self._approve("primary")

        code1, _out1, _ = _run_cli_at(self.root, ["profile", "switch", "primary"])
        content1 = (self.root / "profile" / "registry.json").read_bytes()
        code2, _out2, _ = _run_cli_at(self.root, ["profile", "switch", "primary"])
        content2 = (self.root / "profile" / "registry.json").read_bytes()

        self.assertEqual(code1, 0)
        self.assertEqual(code2, 0)
        self.assertEqual(content1, content2)

    def test_unknown_target_fails_before_requesting_approval(self):
        _seed_registry(self.root, [_valid_registry_entry("primary", True)])
        code, _out, err = _run_cli_at(self.root, ["profile", "switch", "does-not-exist"])
        self.assertEqual(code, 1)
        self.assertIn("unknown profile id", err)

        from orchestration import approvals as orch_approvals
        pending = orch_approvals.list_approvals(self.root, status="pending")
        self.assertFalse(any(a["target"] == "does-not-exist" for a in pending))

    def test_empty_registry_fails_without_mutation_or_approval_request(self):
        code, _out, err = _run_cli_at(self.root, ["profile", "switch", "primary"])
        self.assertEqual(code, 1)
        self.assertIn("no profiles registered", err)
        self.assertFalse((self.root / "profile" / "registry.json").is_file())

    def test_approval_for_one_profile_does_not_authorize_switching_to_another(self):
        _seed_registry(self.root, [
            _valid_registry_entry("primary", True),
            _valid_registry_entry("secondary", False),
            _valid_registry_entry("tertiary", False),
        ])
        _run_cli_at(self.root, ["profile", "switch", "secondary"])  # requests approval for 'secondary'
        self._approve("secondary")

        # An approval scoped to 'secondary' must not authorize switching to 'tertiary'.
        code, _out, err = _run_cli_at(self.root, ["profile", "switch", "tertiary"])
        self.assertEqual(code, 1)
        self.assertIn("requires approval", err)

        from profile import registry as profile_registry
        data = profile_registry.load_registry(self.root)
        active_ids = [p["id"] for p in data["profiles"] if p["active"]]
        self.assertEqual(active_ids, ["primary"])  # unchanged


if __name__ == "__main__":
    unittest.main()
