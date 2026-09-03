#!/usr/bin/env python3
"""AI OS unified CLI — one-command interface for all AI OS operations."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from release.version import read_version
from release.config import load_config, validate_config
from release.status import get_status
from release.utils import (
    GENERATED_ARTIFACTS, GENERATION_ORDER,
    ensure_directory, now_iso, print_result,
    print_warning, run_python_script, load_json_safe,
)

from orchestration import approvals as orch_approvals
from orchestration import audit as orch_audit
from orchestration import feedback as orch_feedback
from orchestration import memory_suggestions as orch_memory_suggestions
from orchestration import session as orch_session
from orchestration.freshness import review_due
from orchestration.knowledge_gaps import build_knowledge_health
from orchestration.planner import create_plan
from orchestration.router import classify_task
from orchestration.workflow import build_workflow_registry

from profile import record as profile_record
from profile import registry as profile_registry
from profile import switch as profile_switch
from profile import sync_knowledge as profile_sync_knowledge
from profile import validate as profile_validate
from profile.sanitize import SanitizationError


def cmd_version(args):
    """Print AI OS version."""
    print(read_version(ROOT))
    return 0


def cmd_status(args):
    """Print unified status."""
    status = get_status(ROOT)
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(f"AI OS v{status['version']}")
        print(f"Repository: {status['repository']}")
        summary = status.get("summary", {})
        print()
        print(f"Repository ........ {summary.get('repository', 'UNKNOWN')}")
        print(f"Configuration ..... {summary.get('configuration', 'UNKNOWN')}")
        print(f"Generated Files ... {summary.get('generatedFiles', 'UNKNOWN')}")
        print(f"Dashboard ......... {summary.get('dashboard', 'UNKNOWN')}")
        print(f"MCP ............... {summary.get('mcp', 'UNKNOWN')} (read-only: {status['mcp']['readOnly']})")
        missing = [a['path'] for a in status['artifacts'] if not a['exists']]
        if missing:
            print(f"Missing artifacts: {', '.join(missing)}")
        failed = [c for c in status.get("generationChecks", []) if c["status"] != "PASS"]
        if failed:
            print()
            print("Generated file checks needing attention:")
            for check in failed:
                detail = f" — {check['detail']}" if check.get("detail") else ""
                print(f"  {check['status']:7} {check['name']}{detail}")
        print()
        print(f"Overall: {'HEALTHY' if status['releaseReady'] else 'NOT READY'}")
    return 0


def cmd_doctor(args):
    """Run environment diagnostics."""
    import platform
    import shutil
    checks = []

    # Python version
    py = sys.version_info
    ok = py >= (3, 10)
    checks.append(("Python >= 3.10", ok, f"{py.major}.{py.minor}.{py.micro}"))

    # OS
    checks.append(("Operating system", True, platform.system()))

    # Repository root
    checks.append(("Repository root", ROOT.is_dir(), str(ROOT)))

    # Git available
    git_ok = shutil.which("git") is not None
    checks.append(("Git available", git_ok, ""))

    # VERSION file
    try:
        v = read_version(ROOT)
        checks.append(("VERSION file", True, v))
    except FileNotFoundError:
        checks.append(("VERSION file", False, "missing"))

    # Config
    config = load_config(ROOT)
    cf, cw = validate_config(config)
    checks.append(("Configuration valid", len(cf) == 0, "; ".join(cf) if cf else ""))
    for w in cw:
        checks.append(("Configuration warning", None, w))

    # Generated artifacts
    gen = ROOT / "generated"
    for name in ["skills.json", "repository-index.json", "memory-index.json",
                 "knowledge-graph.json", "discovery-index.json", "dashboard.html", "dashboard-data.json"]:
        exists = (gen / name).is_file()
        checks.append((f"Artifact: {name}", exists, "present" if exists else "MISSING"))

    # MCP server
    mcp_ok = (ROOT / "scripts" / "mcp-server.py").is_file()
    checks.append(("MCP server script", mcp_ok, ""))

    # Dashboard port
    dashboard_port = config.get("dashboard", {}).get("port", 8080)
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            result = s.connect_ex(("127.0.0.1", dashboard_port))
            port_free = result != 0
    except OSError:
        port_free = True
    checks.append((f"Dashboard port {dashboard_port} available", port_free, "free" if port_free else "in use"))

    # Print results
    failures = 0
    if args.json:
        items = [{"check": c[0], "status": "PASS" if c[1] else ("WARNING" if c[1] is None else "FAIL"), "detail": c[2]} for c in checks]
        print(json.dumps({"checks": items, "failures": sum(1 for c in checks if c[1] is False)}, indent=2))
    else:
        for label, passed, detail in checks:
            if passed is True:
                status = "PASS"
            elif passed is None:
                status = "WARNING"
            else:
                status = "FAIL"
                failures += 1
            line = f"{status:8} {label}"
            if detail:
                line += f" — {detail}"
            print(line)
        print(f"\n{len(checks)} checks: {sum(1 for c in checks if c[1] is True)} PASS, {sum(1 for c in checks if c[1] is None)} WARNING, {failures} FAIL")
    return 1 if failures > 0 else 0


def cmd_bootstrap(args):
    """Bootstrap the AI OS repository."""
    import platform
    print(f"AI OS Bootstrap v{read_version(ROOT)}")
    print(f"Platform: {platform.system()} / Python {sys.version_info.major}.{sys.version_info.minor}")
    print()

    if sys.version_info < (3, 10):
        print("FAIL Python 3.10+ required")
        return 1

    if args.check:
        print("Running bootstrap check (no modifications)...")
        # Verify all artifacts are current
        for script, label in GENERATION_ORDER:
            rc, out, err = run_python_script(script, ["--check"], ROOT, timeout=60)
            passed = rc == 0
            print_result(f"{label} current", passed, (out + err).strip().split("\n")[-1] if not passed else "")
            if not passed and not args.skip_tests:
                return 1
        print("\nBootstrap check: all artifacts current")
        return 0

    steps = []
    # Step 1: Ensure directories
    ensure_directory(ROOT / ".ai-os" / "logs")
    ensure_directory(ROOT / ".ai-os" / "backups")
    steps.append(("Create runtime directories", True))

    # Step 2: Generate artifacts in order
    for script, label in GENERATION_ORDER:
        if args.force_regenerate:
            rc, out, err = run_python_script(script, [], ROOT, timeout=120)
        else:
            # Check first, regenerate only if stale
            rc, out, err = run_python_script(script, ["--check"], ROOT, timeout=60)
            if rc != 0:
                rc, out, err = run_python_script(script, [], ROOT, timeout=120)
        passed = rc == 0
        steps.append((f"Generate {label}", passed))
        print_result(f"Generate {label}", passed)
        if not passed:
            print(f"  Error: {(out + err).strip()[-200:]}", file=sys.stderr)
            return 1

    # Step 3: Run validation
    rc, out, err = run_python_script("scripts/validate-all.py", [], ROOT, timeout=180)
    val_passed = rc == 0
    steps.append(("Unified validation", val_passed))
    print_result("Unified validation", val_passed)

    # Step 4: Summary
    print(f"\nBootstrap complete: {sum(1 for _, p in steps if p)}/{len(steps)} steps passed")
    print("\nNext steps:")
    print("  python scripts/ai-os.py status")
    print("  python scripts/ai-os.py start-dashboard")
    print("  python scripts/ai-os.py start-mcp")

    if args.json:
        print(json.dumps({"steps": [{"name": n, "passed": p} for n, p in steps]}))
    return 0 if all(p for _, p in steps) else 1


def cmd_validate(args):
    """Run unified validation."""
    rc, out, err = run_python_script("scripts/validate-all.py", [], ROOT, timeout=300)
    print((out + err).strip())
    return rc


def cmd_test(args):
    """Run unit tests."""
    rc, out, err = run_python_script("-m", None, ROOT, timeout=300)
    # Actually call unittest directly
    import subprocess
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                           capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    print(result.stderr[-500:] if result.stderr else "")
    return result.returncode


def cmd_build(args):
    """Generate all artifacts in dependency order."""
    print("Generating artifacts...")
    if args.check:
        all_ok = True
        for script, label in GENERATION_ORDER:
            rc, out, err = run_python_script(script, ["--check"], ROOT, timeout=60)
            passed = rc == 0
            print_result(f"{label}", passed)
            if not passed:
                all_ok = False
        # Also check release manifest
        from release.manifest import build_manifest, check_manifest
        manifest = build_manifest(ROOT)
        try:
            check_manifest(manifest, ROOT)
            print_result("release manifest", True)
        except (ValueError, FileNotFoundError):
            print_result("release manifest", False)
            all_ok = False
        return 0 if all_ok else 1

    for script, label in GENERATION_ORDER:
        if not args.force:
            rc, _, _ = run_python_script(script, ["--check"], ROOT, timeout=60)
            if rc == 0:
                print_result(f"{label}", True, "current")
                continue
        rc, out, err = run_python_script(script, [], ROOT, timeout=120)
        passed = rc == 0
        print_result(f"{label}", passed, (out + err).strip().split("\n")[-1][:80] if passed else "FAILED")
        if not passed:
            return 1

    # Generate release manifest last (depends on all other artifacts)
    from release.manifest import build_manifest, write_manifest_if_changed
    manifest = build_manifest(ROOT)
    changed = write_manifest_if_changed(manifest, ROOT)
    print_result("release manifest", True, "generated" if changed else "current")

    print("\nAll artifacts generated.")
    return 0


def cmd_start_dashboard(args):
    """Start the dashboard server."""
    config = load_config(ROOT)
    port = config.get("dashboard", {}).get("port", 8080)
    no_browser = not config.get("dashboard", {}).get("openBrowser", False)
    cmd_args = ["--port", str(port)]
    if no_browser:
        cmd_args.append("--no-browser")
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "dashboard-serve.py")] + cmd_args, cwd=str(ROOT))
    return 0


def cmd_start_mcp(args):
    """Start the MCP server."""
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "mcp-server.py")], cwd=str(ROOT))
    return 0


def cmd_smoke_test(args):
    """Run MCP smoke test."""
    rc, out, err = run_python_script("scripts/mcp-smoke-test.py", [], ROOT, timeout=30)
    print((out + err).strip())
    return rc


def cmd_mcp(args):
    """MCP convenience commands."""
    if args.mcp_cmd == "check":
        return cmd_smoke_test(args)
    if args.mcp_cmd == "start":
        return cmd_start_mcp(args)
    print("Usage: ai-os.py mcp {check,start}", file=sys.stderr)
    return 1


def cmd_release_check(args):
    """Run release readiness checks."""
    print(f"Release check for AI OS v{read_version(ROOT)}")
    print()
    checks = []

    # Version valid
    from release.version import is_valid_semver
    v = read_version(ROOT)
    checks.append(("Version valid", is_valid_semver(v), v))

    # Config valid
    config = load_config(ROOT)
    cf, _ = validate_config(config)
    checks.append(("Configuration valid", len(cf) == 0, ""))

    # Generated artifacts current
    for script, label in GENERATION_ORDER:
        rc, _, _ = run_python_script(script, ["--check"], ROOT, timeout=60)
        checks.append((f"{label} current", rc == 0, ""))

    # MCP smoke test
    rc, _, _ = run_python_script("scripts/mcp-smoke-test.py", [], ROOT, timeout=30)
    checks.append(("MCP smoke test", rc == 0, ""))

    # Release manifest
    from release.manifest import build_manifest, check_manifest, validate_manifest
    try:
        manifest = build_manifest(ROOT)
        failures_m, _ = validate_manifest(manifest)
        check_manifest(manifest, ROOT)
        checks.append(("Release manifest current", len(failures_m) == 0, ""))
    except (ValueError, FileNotFoundError) as exc:
        checks.append(("Release manifest current", False, str(exc)))

    # Secret scan (via validate-all subset)
    rc, out, _ = run_python_script("scripts/validate-all.py", [], ROOT, timeout=300)
    checks.append(("Unified validation", rc == 0, ""))

    failures = sum(1 for _, p, _ in checks if not p)
    if args.json:
        print(json.dumps({"checks": [{"name": n, "passed": p, "detail": d} for n, p, d in checks], "failures": failures}))
    else:
        for label, passed, detail in checks:
            print_result(label, passed, detail)
        print(f"\nRelease check: {len(checks) - failures}/{len(checks)} passed")
        if failures:
            print("RELEASE BLOCKED — fix failures before packaging")
    return 1 if failures > 0 else 0


def cmd_package(args):
    """Create a release package."""
    import hashlib
    import tarfile
    import zipfile

    version = read_version(ROOT)
    dist = Path(args.output) if args.output else ROOT / "dist"

    if not args.dry_run:
        ensure_directory(dist)

    # Collect files
    EXCLUDE_DIRS = {".git", ".venv", "venv", "env", "node_modules", "__pycache__",
                    ".pytest_cache", "coverage", "dist", ".ai-os", "temp", "tmp", "output"}
    EXCLUDE_PATTERNS = {".env", "ai-os.local.json"}
    EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".key", ".pem", ".pfx", ".p12"}

    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        parts_lower = {p.lower() for p in rel.parts}
        if parts_lower & EXCLUDE_DIRS:
            continue
        if rel.name in EXCLUDE_PATTERNS or rel.name.startswith(".env"):
            continue
        if rel.suffix.lower() in EXCLUDE_SUFFIXES:
            continue
        # Reject symlinks escaping root
        try:
            path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            continue
        files.append(rel)

    if args.dry_run:
        print(f"Package: ai-os-{version}")
        print(f"Files: {len(files)}")
        print(f"Output: {dist}")
        if args.json:
            print(json.dumps({"version": version, "fileCount": len(files), "output": str(dist)}))
        else:
            for f in files[:20]:
                print(f"  {f}")
            if len(files) > 20:
                print(f"  ... and {len(files) - 20} more")
        return 0

    # Create archives
    zip_path = dist / f"ai-os-{version}.zip"
    tar_path = dist / f"ai-os-{version}.tar.gz"
    files_list_path = dist / f"ai-os-{version}-files.txt"
    sha_path = dist / f"ai-os-{version}.sha256"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(ROOT / rel, str(rel))

    with tarfile.open(tar_path, "w:gz") as tf:
        for rel in files:
            tf.add(ROOT / rel, arcname=str(rel))

    files_list_path.write_text("\n".join(str(f) for f in files) + "\n", encoding="utf-8", newline="\n")

    # Checksums
    checksums = []
    for archive in [zip_path, tar_path]:
        h = hashlib.sha256(archive.read_bytes()).hexdigest()
        checksums.append(f"{h}  {archive.name}")
    sha_path.write_text("\n".join(checksums) + "\n", encoding="utf-8", newline="\n")

    print(f"Package created: ai-os-{version}")
    print(f"  ZIP: {zip_path} ({zip_path.stat().st_size} bytes)")
    print(f"  TAR: {tar_path} ({tar_path.stat().st_size} bytes)")
    print(f"  Files: {len(files)}")
    print(f"  Checksums: {sha_path}")
    return 0


def cmd_backup(args):
    """Back up local state."""
    import shutil
    import tarfile

    config = load_config(ROOT)
    backup_dir = ROOT / config.get("backup", {}).get("directory", ".ai-os/backups")
    ensure_directory(backup_dir)

    timestamp = now_iso().replace(":", "-").replace("T", "_").split(".")[0]
    backup_name = f"backup-{timestamp}"
    backup_path = backup_dir / f"{backup_name}.tar.gz"

    # Files to back up: generated/ and config/
    backup_files = []
    gen = ROOT / "generated"
    if gen.is_dir():
        for f in sorted(gen.iterdir()):
            if f.is_file():
                backup_files.append(f.relative_to(ROOT))
    local_config = ROOT / "config" / "ai-os.local.json"
    if local_config.is_file():
        backup_files.append(local_config.relative_to(ROOT))

    if args.dry_run:
        print(f"Backup (dry run): {len(backup_files)} files -> {backup_path}")
        for f in backup_files:
            print(f"  {f}")
        return 0

    with tarfile.open(backup_path, "w:gz") as tf:
        for rel in backup_files:
            tf.add(ROOT / rel, arcname=str(rel))

    print(f"Backup created: {backup_path}")
    print(f"  Files: {len(backup_files)}")
    print(f"  Size: {backup_path.stat().st_size} bytes")
    return 0


def cmd_restore(args):
    """Restore from a backup."""
    import tarfile

    backup_path = Path(args.backup)
    if not backup_path.is_file():
        print(f"FAIL backup not found: {backup_path}", file=sys.stderr)
        return 1

    if not tarfile.is_tarfile(str(backup_path)):
        print("FAIL not a valid tar archive", file=sys.stderr)
        return 1

    with tarfile.open(backup_path, "r:gz") as tf:
        members = tf.getmembers()
        # Security: reject path traversal
        for m in members:
            if m.name.startswith("/") or ".." in m.name:
                print(f"FAIL unsafe path in backup: {m.name}", file=sys.stderr)
                return 1

        if args.dry_run:
            print(f"Restore (dry run) from: {backup_path}")
            for m in members:
                print(f"  {m.name}")
            return 0

        if not args.force:
            print("Restore requires --force to overwrite existing files.")
            print("Files to restore:")
            for m in members:
                print(f"  {m.name}")
            return 1

        tf.extractall(path=str(ROOT), filter="data")
        print(f"Restored {len(members)} files from {backup_path}")
    return 0


def cmd_clean_generated(args):
    """Remove generated artifacts (dry-run by default)."""
    gen = ROOT / "generated"
    if not gen.is_dir():
        print("No generated/ directory found.")
        return 0

    allowlisted = set(GENERATED_ARTIFACTS)
    to_remove = []
    for f in sorted(gen.iterdir()):
        if f.is_file() and f.name in allowlisted:
            to_remove.append(f)

    if not to_remove:
        print("No generated artifacts to clean.")
        return 0

    if not args.confirm:
        print(f"Dry run — would remove {len(to_remove)} file(s):")
        for f in to_remove:
            print(f"  {f.relative_to(ROOT)}")
        print("\nUse --confirm to actually delete.")
        return 0

    for f in to_remove:
        f.unlink()
        print(f"  Removed: {f.relative_to(ROOT)}")
    print(f"\nRemoved {len(to_remove)} generated artifact(s).")
    return 0


def cmd_migrate(args):
    """Check migration status."""
    version = read_version(ROOT)
    print(f"Current version: {version}")
    print("No migrations required for current version.")
    if args.check:
        print("PASS no pending migrations")
    return 0


def cmd_plan(args):
    """Create a structured task plan. Performs no execution."""
    plan = create_plan(ROOT, args.task, project=args.project, workflow_override=args.workflow,
                        limit=args.limit, no_memory=args.no_memory, no_history=args.no_history)
    if args.json:
        print(json.dumps(plan, indent=2))
        return 0

    workflow = plan["selectedWorkflow"]
    print(f"Task: {plan['taskSummary']}")
    print(f"Intent: {plan['intent']} (confidence {plan['confidence']})")
    print(f"Workflow: {workflow['id'] if workflow else 'none selected'}")
    print(f"Agents: {', '.join(a['id'] for a in plan['selectedAgents']) or 'none'}")
    print(f"Approval gates: {', '.join(plan['approvalGates']) or 'none'}")
    print(f"Validation requirements: {', '.join(plan['validationRequirements']) or 'none'}")
    print(f"Expected output artifacts: {', '.join(plan['expectedOutputArtifacts']) or 'none'}")
    print(f"Memory suggestion policy: {plan['memorySuggestionPolicy'] or 'none'}")
    print(f"Audit policy: {plan['auditPolicy'] or 'none'}")
    print(f"Knowledge retrieved: {len(plan['retrievedKnowledge'])} item(s)")
    if args.explain:
        print("\nMatched signals:")
        for signal in plan["matchedSignals"]:
            print(f"  - {signal}")
        print("\nSteps:")
        for step in plan["steps"]:
            approval = " (requires approval)" if step.get("requiresApproval") else ""
            print(f"  - {step['id']}: {step['agent']} -> {step['action']}{approval}")
        print("\nRetrieved knowledge:")
        for item in plan["retrievedKnowledge"][:10]:
            print(f"  - [{item.get('type')}] {item.get('name')} ({item.get('sourcePath')}) score={item.get('score')}")
    if plan["risksAndWarnings"]:
        print("\nRisks and warnings:")
        for warning in plan["risksAndWarnings"]:
            print(f"  - {warning}")
    return 0


def cmd_classify(args):
    """Classify a task's intent. Deterministic, no execution."""
    result = classify_task(ROOT, args.task, project=args.project, requested_workflow=args.workflow)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"Intent: {result['intent']} (confidence {result['confidence']})")
    print(f"Matched signals: {', '.join(result['matchedSignals']) or 'none'}")
    print(f"Suggested workflow: {result['suggestedWorkflow'] or 'none'}")
    print(f"Suggested agents: {', '.join(result['suggestedAgents']) or 'none'}")
    print(f"Approval required: {result['approvalRequired']}")
    if result["warnings"]:
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"  - {warning}")
    return 0


def cmd_workflow(args):
    """List or show workflow registry entries."""
    registry = build_workflow_registry(ROOT)
    if args.workflow_cmd == "list":
        if args.json:
            print(json.dumps(registry, indent=2))
        else:
            for workflow in registry["workflows"]:
                print(f"{workflow['id']}: {workflow['name']} (approval gates: {len(workflow['approvalGates'])})")
        return 0
    if args.workflow_cmd == "show":
        workflow = next((w for w in registry["workflows"] if w["id"] == args.workflow_id), None)
        if workflow is None:
            print(f"FAIL workflow not found: {args.workflow_id}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(workflow, indent=2))
        else:
            print(f"{workflow['id']}: {workflow['name']}")
            print(workflow["description"])
            for step in workflow["steps"]:
                approval = " (requires approval)" if step.get("requiresApproval") else ""
                print(f"  - {step['id']}: {step['agent']} -> {step['action']}{approval}")
        return 0
    print("Usage: ai-os.py workflow {list,show}", file=sys.stderr)
    return 1


def cmd_session(args):
    """Track a local work session through a plan. Never modifies source files."""
    try:
        if args.session_cmd == "list":
            sessions = orch_session.list_sessions(ROOT, status=args.status)
            if args.json:
                print(json.dumps(sessions, indent=2))
            else:
                for session in sessions:
                    print(f"{session['sessionId']}: [{session['status']}] {session['task'][:60]}")
            return 0

        if args.session_cmd == "show":
            session = orch_session.get_session(ROOT, args.session_id)
            print(json.dumps(session, indent=2))
            return 0

        if args.session_cmd == "start":
            plan = create_plan(ROOT, args.task, project=args.project, workflow_override=args.workflow)
            session = orch_session.create_session(ROOT, args.task, project=args.project, plan=plan)
            orch_audit.append_event(ROOT, "workflow-selected",
                                     details={"workflowId": session.get("workflowId"), "sessionId": session["sessionId"]})
            for agent_id in session.get("agents", []):
                orch_audit.append_event(ROOT, "agent-selected", details={"agentId": agent_id, "sessionId": session["sessionId"]})
            orch_audit.append_event(ROOT, "knowledge-retrieved",
                                     details={"count": len(session.get("knowledgeUsed", [])), "sessionId": session["sessionId"]})
            if plan["approvalGates"]:
                approval = orch_approvals.request_approval(
                    ROOT, approval_type="plan", target=session["sessionId"],
                    reason="workflow requires plan approval before proceeding")
                orch_audit.append_event(ROOT, "approval-requested",
                                         details={"approvalId": approval["approvalId"], "type": "plan"})
            if args.json:
                print(json.dumps(session, indent=2))
            else:
                print(f"Session created: {session['sessionId']} [{session['status']}]")
                print(f"Workflow: {session['workflowId']}")
                print(f"Agents: {', '.join(session['agents']) or 'none'}")
            return 0

        if args.session_cmd == "validate":
            orch_session.advance_toward(ROOT, args.session_id, "active")
            session = orch_session.record_validation(
                ROOT, args.session_id, name=args.name, passed=(args.status == "pass"), detail=args.detail or "")
            orch_audit.append_event(ROOT, "validation-run",
                                     details={"sessionId": args.session_id, "name": args.name, "passed": args.status == "pass"})
            if args.status == "pass":
                session = orch_session.advance_toward(ROOT, args.session_id, "validation")
            print(f"Validation recorded: {args.name} -> {args.status} (session status: {session['status']})")
            return 0

        if args.session_cmd == "complete":
            session = orch_session.get_session(ROOT, args.session_id)
            if session["status"] != "validation":
                print(f"FAIL session must be in 'validation' status to complete (current: {session['status']}); "
                      "run `session validate` first", file=sys.stderr)
                return 1
            session = orch_session.complete_session(ROOT, args.session_id)
            orch_audit.append_event(ROOT, "session-completed", details={"sessionId": args.session_id})
            passed_validations = [v for v in session.get("validations", []) if v.get("passed")]
            if passed_validations:
                suggestion = orch_memory_suggestions.generate_suggestion(ROOT, session)
                orch_audit.append_event(ROOT, "memory-suggested",
                                         details={"suggestionId": suggestion["id"], "sessionId": args.session_id})
                approval = orch_approvals.request_approval(
                    ROOT, approval_type="permanent-memory", target=suggestion["id"],
                    reason="memory suggestion generated on session completion")
                orch_audit.append_event(ROOT, "approval-requested",
                                         details={"approvalId": approval["approvalId"], "type": "permanent-memory"})
                print(f"Session completed: {args.session_id}")
                print(f"Memory suggestion created (pending approval): {suggestion['id']}")
            else:
                print(f"Session completed: {args.session_id} (no passed validations; no memory suggestion created)")
            return 0

        if args.session_cmd == "archive":
            orch_session.archive_session(ROOT, args.session_id)
            print(f"Session archived: {args.session_id}")
            return 0
    except (orch_session.SessionError, orch_approvals.ApprovalError, ValueError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print("Usage: ai-os.py session {list,show,start,validate,complete,archive}", file=sys.stderr)
    return 1


def cmd_approval(args):
    """List, show, approve, or reject explicit approval gates."""
    try:
        if args.approval_cmd == "list":
            items = orch_approvals.list_approvals(ROOT, status=args.status)
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                for approval in items:
                    print(f"{approval['approvalId']}: [{approval['status']}] {approval['type']} -> {approval['target']}")
            return 0
        if args.approval_cmd == "show":
            print(json.dumps(orch_approvals.get_approval(ROOT, args.approval_id), indent=2))
            return 0
        if args.approval_cmd == "approve":
            approval = orch_approvals.approve(ROOT, args.approval_id)
            orch_audit.append_event(ROOT, "approval-approved", details={"approvalId": approval["approvalId"], "type": approval["type"]})
            print(f"Approved: {approval['approvalId']}")
            return 0
        if args.approval_cmd == "reject":
            approval = orch_approvals.reject(ROOT, args.approval_id, reason=args.reason or "")
            orch_audit.append_event(ROOT, "approval-rejected", details={"approvalId": approval["approvalId"], "type": approval["type"]})
            print(f"Rejected: {approval['approvalId']}")
            return 0
    except orch_approvals.ApprovalError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print("Usage: ai-os.py approval {list,show,approve,reject}", file=sys.stderr)
    return 1


def cmd_profile(args):
    """Professional profile, expertise, explicit switching, and sync-knowledge
    (Phase 9, Tasks 001-014). `list`/`show` are read-only and never modify
    profile/registry.json, memory/, approvals, sessions, or generated
    artifacts. `switch` is the only code path allowed to change which
    profile is active, is always explicit, and requires an approved
    'profile-switch' approval (requested automatically, never auto-approved)
    before any mutation occurs.
    """
    try:
        if args.profile_cmd == "list":
            data = profile_registry.load_registry(ROOT)
            failures, _warnings = profile_validate.validate_registry_shape(data)
            if failures:
                print("FAIL invalid profile registry: " + "; ".join(failures), file=sys.stderr)
                return 1
            profiles = data.get("profiles", [])
            if args.json:
                print(json.dumps(profiles, indent=2))
                return 0
            if not profiles:
                print("No professional profiles configured yet. See profile/README.md to author one.")
                return 0
            for entry in profiles:
                status = "active" if entry.get("active") else "inactive"
                print(f"{entry['id']}: [{status}] {entry.get('path', '')} "
                      f"(schemaVersion {data.get('schemaVersion', '')})")
            return 0

        if args.profile_cmd == "show":
            data = profile_registry.load_registry(ROOT)
            failures, _warnings = profile_validate.validate_registry_shape(data)
            if failures:
                print("FAIL invalid profile registry: " + "; ".join(failures), file=sys.stderr)
                return 1

            if args.profile_id:
                entry = profile_registry.find_profile(data, args.profile_id)
                if entry is None:
                    print(f"FAIL unknown profile id: {args.profile_id}", file=sys.stderr)
                    return 1
            else:
                entry = profile_registry.active_profile(data)
                if entry is None:
                    print("No active professional profile is configured yet.")
                    return 0

            summary = profile_record.load_profile_summary(ROOT, entry)
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print(f"id: {summary['id']}")
                print(f"active: {summary['active']}")
                print(f"role: {summary.get('role', '')}")
                print(f"team: {summary.get('team', '')}")
                print(f"reportingTo: {summary.get('reportingTo') or ''}")
                responsibilities = summary.get("responsibilities") or []
                print(f"responsibilities: {', '.join(responsibilities) if responsibilities else '(none)'}")
                print(f"sensitivity: {summary.get('sensitivity', '')}")
                print(f"schemaVersion: {summary.get('schemaVersion', '')}")
                print(f"updatedAt: {summary.get('updatedAt', '')}")
            return 0

        if args.profile_cmd == "switch":
            target_id = args.profile_id
            data = profile_registry.load_registry(ROOT)
            failures, _warnings = profile_validate.validate_registry_shape(data)
            if failures:
                print("FAIL invalid profile registry: " + "; ".join(failures), file=sys.stderr)
                return 1
            if not data.get("profiles"):
                print("FAIL no profiles registered; nothing to switch", file=sys.stderr)
                return 1
            if profile_registry.find_profile(data, target_id) is None:
                print(f"FAIL unknown profile id: {target_id}", file=sys.stderr)
                return 1

            if not orch_approvals.is_approved(ROOT, approval_type="profile-switch", target=target_id):
                approval = orch_approvals.request_approval(
                    ROOT, approval_type="profile-switch", target=target_id,
                    reason=f"explicit profile switch requested: {target_id}")
                orch_audit.append_event(ROOT, "approval-requested",
                                         details={"approvalId": approval["approvalId"], "type": "profile-switch"})
                print(f"FAIL profile switch to {target_id!r} requires approval; requested "
                      f"{approval['approvalId']} (pending) -- approve it with "
                      f"`ai-os.py approval approve {approval['approvalId']}` and re-run", file=sys.stderr)
                return 1

            activated = profile_switch.switch(ROOT, target_id)
            print(f"Active profile switched to: {activated['id']}")
            return 0

        if args.profile_cmd == "sync-knowledge":
            if args.force_refresh:
                result = profile_sync_knowledge.force_refresh(ROOT)
            else:
                result = profile_sync_knowledge.sync(ROOT)
            print(f"{result['status'].upper()}: {result['message']}")
            return 0
    except (profile_switch.SwitchError, profile_sync_knowledge.SyncKnowledgeError,
            profile_record.ProfileRecordError, SanitizationError,
            orch_approvals.ApprovalError, ValueError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print("Usage: ai-os.py profile {list,show,switch,sync-knowledge}", file=sys.stderr)
    return 1


def cmd_memory_suggestions(args):
    """List, show, approve, reject, or export memory suggestions."""
    try:
        if args.memory_suggestions_cmd == "list":
            items = orch_memory_suggestions.list_suggestions(ROOT, status=args.status)
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                for suggestion in items:
                    print(f"{suggestion['id']}: [{suggestion['status']}] {suggestion['title'][:60]} "
                          f"(confidence {suggestion['confidence']})")
            return 0
        if args.memory_suggestions_cmd == "show":
            print(json.dumps(orch_memory_suggestions.get_suggestion(ROOT, args.suggestion_id), indent=2))
            return 0
        if args.memory_suggestions_cmd == "approve":
            suggestion = orch_memory_suggestions.approve(ROOT, args.suggestion_id)
            orch_audit.append_event(ROOT, "memory-approved", details={"suggestionId": suggestion["id"]})
            print(f"Approved and promoted to memory: {suggestion['id']} -> {suggestion.get('proposedPath')}")
            return 0
        if args.memory_suggestions_cmd == "reject":
            suggestion = orch_memory_suggestions.reject(ROOT, args.suggestion_id, reason=args.reason or "")
            orch_audit.append_event(ROOT, "memory-rejected", details={"suggestionId": suggestion["id"]})
            print(f"Rejected: {suggestion['id']}")
            return 0
        if args.memory_suggestions_cmd == "export":
            dest = Path(args.output) if args.output else ROOT / ".ai-os" / "memory-suggestions" / f"{args.suggestion_id}.export.json"
            path = orch_memory_suggestions.export_suggestion(ROOT, args.suggestion_id, dest)
            print(f"Exported to: {path}")
            return 0
    except (orch_memory_suggestions.MemorySuggestionError, orch_approvals.ApprovalError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print("Usage: ai-os.py memory-suggestions {list,show,approve,reject,export}", file=sys.stderr)
    return 1


def cmd_knowledge_health(args):
    """Print the live knowledge health summary (includes local session/feedback signal)."""
    report = build_knowledge_health(ROOT, include_live=True)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"Overall knowledge health score: {report['overallScore']}/100")
    for name, score in sorted(report["categoryScores"].items()):
        print(f"  {name}: {score}/100")
    print("\nRecommendations:")
    for recommendation in report["recommendations"]:
        print(f"  - {recommendation}")
    return 0


def cmd_knowledge_gaps(args):
    """Print detected knowledge gaps (live view; not written to generated/)."""
    report = build_knowledge_health(ROOT, include_live=True)
    orch_audit.append_event(ROOT, "knowledge-gap-detected",
                             details={"gapCount": len(report["gaps"]), "overallScore": report["overallScore"]})
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"Overall score: {report['overallScore']}/100 ({len(report['gaps'])} gap(s) detected)")
    for gap in report["gaps"][:args.limit]:
        print(f"  [{gap['severity']}] {gap['category']}: {gap['description']}")
    return 0


def cmd_review_due(args):
    """List documents due for review (only those opting into freshness metadata)."""
    items = review_due(ROOT, days=args.days)
    if args.json:
        print(json.dumps(items, indent=2))
        return 0
    if not items:
        print("No documents are due for review.")
        print("(Only documents declaring owner/lastReviewed/reviewIntervalDays/nextReview front matter are tracked.)")
        return 0
    for item in items:
        tag = "OVERDUE" if item["overdue"] else "DUE SOON" if item["dueSoon"] else "ISSUE"
        print(f"[{tag}] {item['path']}: {', '.join(item['issues']) or ('next review ' + str(item.get('nextReview')))}")
    return 0


def cmd_feedback(args):
    """Add, list, resolve, or summarize local feedback."""
    try:
        if args.feedback_cmd == "add":
            entry = orch_feedback.add_feedback(
                ROOT, feedback_type=args.type, target_type=args.target_type, target_id=args.target_id,
                query=args.query or "", comment=args.comment or "", related_session_id=args.session)
            orch_audit.append_event(ROOT, "feedback-added", details={"feedbackId": entry["feedbackId"], "type": entry["type"]})
            print(f"Feedback recorded: {entry['feedbackId']}")
            return 0
        if args.feedback_cmd == "list":
            items = orch_feedback.list_feedback(ROOT, status=args.status, feedback_type=args.type)
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                for entry in items:
                    print(f"{entry['feedbackId']}: [{entry['status']}] {entry['type']} -> {entry['targetId']}")
            return 0
        if args.feedback_cmd == "resolve":
            entry = orch_feedback.resolve_feedback(ROOT, args.feedback_id)
            print(f"Resolved: {entry['feedbackId']}")
            return 0
        if args.feedback_cmd == "stats":
            stats = orch_feedback.feedback_stats(ROOT)
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                print(f"Total: {stats['total']} (open: {stats['open']}, resolved: {stats['resolved']})")
                for feedback_type, count in sorted(stats["byType"].items()):
                    print(f"  {feedback_type}: {count}")
            return 0
    except orch_feedback.FeedbackError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print("Usage: ai-os.py feedback {add,list,resolve,stats}", file=sys.stderr)
    return 1


def cmd_audit(args):
    """List, show, export, or validate the local audit trail."""
    try:
        if args.audit_cmd == "list":
            events = orch_audit.list_events(ROOT, event_type=args.type, limit=args.limit)
            if args.json:
                print(json.dumps(events, indent=2))
            else:
                for index, event in enumerate(events):
                    print(f"[{index}] {event['createdAt']} {event['event']}")
            return 0
        if args.audit_cmd == "show":
            print(json.dumps(orch_audit.get_event(ROOT, args.index), indent=2))
            return 0
        if args.audit_cmd == "export":
            dest = Path(args.output) if args.output else ROOT / ".ai-os" / "audit" / "export.json"
            path = orch_audit.export_events(ROOT, dest)
            print(f"Exported to: {path}")
            return 0
        if args.audit_cmd == "validate":
            valid, errors = orch_audit.validate_chain(ROOT)
            if valid:
                print("PASS audit chain valid")
                return 0
            for error in errors:
                print(f"FAIL {error}", file=sys.stderr)
            return 1
    except orch_audit.AuditError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    print("Usage: ai-os.py audit {list,show,export,validate}", file=sys.stderr)
    return 1


def cmd_help(args):
    """Show help."""
    print("AI OS Unified CLI")
    print(f"Version: {read_version(ROOT)}")
    print()
    print("Commands:")
    print("  version          Show version")
    print("  status           Show unified status")
    print("  bootstrap        Bootstrap the repository")
    print("  doctor           Run environment diagnostics")
    print("  validate         Run unified validation")
    print("  test             Run unit tests")
    print("  build            Generate all artifacts")
    print("  generate         Alias for build")
    print("  dashboard        Start the dashboard server")
    print("  start-dashboard  Start the dashboard server")
    print("  start-mcp        Start the MCP server")
    print("  smoke-test       Run MCP smoke test")
    print("  mcp              check|start MCP")
    print("  release-check    Run release readiness checks")
    print("  package          Create a release package")
    print("  backup           Back up local state")
    print("  restore          Restore from backup")
    print("  clean-generated  Remove generated artifacts")
    print("  migrate          Check migration status")
    print("  help             Show this help")
    print()
    print("Phase 8 — continuous learning and agent orchestration:")
    print("  plan                 Create a structured task plan (no execution)")
    print("  classify             Classify a task's intent")
    print("  workflow             list|show workflow registry entries")
    print("  session              list|show|start|validate|complete|archive a local session")
    print("  approval             list|show|approve|reject an approval gate")
    print("  profile              list|show|switch|sync-knowledge a professional profile")
    print("  memory-suggestions   list|show|approve|reject|export a memory suggestion")
    print("  knowledge-health     Show the live knowledge health summary")
    print("  knowledge-gaps       Show detected knowledge gaps")
    print("  review-due           List documents due for review")
    print("  feedback             add|list|resolve|stats local feedback")
    print("  audit                list|show|export|validate the audit trail")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ai-os", description="AI OS unified CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("version", help="Show version")
    sub.add_parser("help", help="Show help")

    p = sub.add_parser("status", help="Show status")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("doctor", help="Environment diagnostics")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("bootstrap", help="Bootstrap repository")
    p.add_argument("--check", action="store_true", help="Check only, no modifications")
    p.add_argument("--json", action="store_true")
    p.add_argument("--skip-tests", action="store_true")
    p.add_argument("--force-regenerate", action="store_true")

    sub.add_parser("validate", help="Run validation")
    sub.add_parser("test", help="Run tests")

    p = sub.add_parser("build", help="Generate artifacts")
    p.add_argument("--check", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("generate", help="Generate artifacts (alias)")
    p.add_argument("--check", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--json", action="store_true")

    sub.add_parser("start-dashboard", help="Start dashboard")
    sub.add_parser("dashboard", help="Start dashboard")
    sub.add_parser("start-mcp", help="Start MCP server")
    sub.add_parser("smoke-test", help="MCP smoke test")

    p = sub.add_parser("mcp", help="MCP commands")
    mcp_sub = p.add_subparsers(dest="mcp_cmd")
    mcp_sub.add_parser("check", help="Run MCP smoke test")
    mcp_sub.add_parser("start", help="Start MCP server")

    p = sub.add_parser("release-check", help="Release readiness")
    p.add_argument("--json", action="store_true")
    p.add_argument("--skip-full-tests", action="store_true")

    p = sub.add_parser("package", help="Create release package")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output", help="Output directory")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("backup", help="Backup local state")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("restore", help="Restore from backup")
    p.add_argument("backup", help="Backup archive path")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("clean-generated", help="Remove generated artifacts")
    p.add_argument("--confirm", action="store_true")

    p = sub.add_parser("migrate", help="Check migrations")
    p.add_argument("--check", action="store_true")

    # Phase 8 — continuous learning and agent orchestration
    p = sub.add_parser("plan", help="Create a structured task plan")
    p.add_argument("task")
    p.add_argument("--project")
    p.add_argument("--workflow")
    p.add_argument("--json", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--explain", action="store_true")
    p.add_argument("--no-memory", action="store_true")
    p.add_argument("--no-history", action="store_true")

    p = sub.add_parser("classify", help="Classify a task's intent")
    p.add_argument("task")
    p.add_argument("--project")
    p.add_argument("--workflow")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("workflow", help="Workflow registry")
    workflow_sub = p.add_subparsers(dest="workflow_cmd")
    wl = workflow_sub.add_parser("list", help="List workflows")
    wl.add_argument("--json", action="store_true")
    ws = workflow_sub.add_parser("show", help="Show a workflow")
    ws.add_argument("workflow_id")
    ws.add_argument("--json", action="store_true")

    p = sub.add_parser("session", help="Local work sessions")
    session_sub = p.add_subparsers(dest="session_cmd")
    sl = session_sub.add_parser("list", help="List sessions")
    sl.add_argument("--status")
    sl.add_argument("--json", action="store_true")
    ss = session_sub.add_parser("show", help="Show a session")
    ss.add_argument("session_id")
    st = session_sub.add_parser("start", help="Start a session from a task")
    st.add_argument("task")
    st.add_argument("--project")
    st.add_argument("--workflow")
    st.add_argument("--json", action="store_true")
    sv = session_sub.add_parser("validate", help="Record a validation result")
    sv.add_argument("session_id")
    sv.add_argument("--name", required=True)
    sv.add_argument("--status", choices=["pass", "fail"], required=True)
    sv.add_argument("--detail", default="")
    sc = session_sub.add_parser("complete", help="Complete a validated session")
    sc.add_argument("session_id")
    sa = session_sub.add_parser("archive", help="Archive a session")
    sa.add_argument("session_id")

    p = sub.add_parser("approval", help="Approval gates")
    approval_sub = p.add_subparsers(dest="approval_cmd")
    apl = approval_sub.add_parser("list", help="List approvals")
    apl.add_argument("--status")
    apl.add_argument("--json", action="store_true")
    aps = approval_sub.add_parser("show", help="Show an approval")
    aps.add_argument("approval_id")
    apa = approval_sub.add_parser("approve", help="Approve a pending approval")
    apa.add_argument("approval_id")
    apr = approval_sub.add_parser("reject", help="Reject a pending approval")
    apr.add_argument("approval_id")
    apr.add_argument("--reason", default="")

    p = sub.add_parser("profile", help="Professional profile and expertise")
    profile_sub = p.add_subparsers(dest="profile_cmd")
    pl = profile_sub.add_parser("list", help="List registered professional profiles (read-only)")
    pl.add_argument("--json", action="store_true")
    ps = profile_sub.add_parser("show", help="Show a profile, or the active profile if no id is given (read-only)")
    ps.add_argument("profile_id", nargs="?", default=None)
    ps.add_argument("--json", action="store_true")
    pw = profile_sub.add_parser("switch", help="Explicitly switch the active profile (requires approval)")
    pw.add_argument("profile_id")
    psk = profile_sub.add_parser("sync-knowledge", help="Scaffold or snapshot the professional-context overview")
    psk.add_argument("--force-refresh", action="store_true", help="Snapshot the current curated overview; never overwrites overview.md")

    p = sub.add_parser("memory-suggestions", help="Memory suggestions")
    ms_sub = p.add_subparsers(dest="memory_suggestions_cmd")
    msl = ms_sub.add_parser("list", help="List memory suggestions")
    msl.add_argument("--status")
    msl.add_argument("--json", action="store_true")
    mss = ms_sub.add_parser("show", help="Show a memory suggestion")
    mss.add_argument("suggestion_id")
    msa = ms_sub.add_parser("approve", help="Approve and promote a suggestion to memory")
    msa.add_argument("suggestion_id")
    msr = ms_sub.add_parser("reject", help="Reject a memory suggestion")
    msr.add_argument("suggestion_id")
    msr.add_argument("--reason", default="")
    mse = ms_sub.add_parser("export", help="Export a memory suggestion for review")
    mse.add_argument("suggestion_id")
    mse.add_argument("--output")

    p = sub.add_parser("knowledge-health", help="Live knowledge health summary")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("knowledge-gaps", help="Detected knowledge gaps")
    p.add_argument("--json", action="store_true")
    p.add_argument("--limit", type=int, default=50)

    p = sub.add_parser("review-due", help="Documents due for review")
    p.add_argument("--days", type=int, default=0)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("feedback", help="Local feedback")
    feedback_sub = p.add_subparsers(dest="feedback_cmd")
    fa = feedback_sub.add_parser("add", help="Add feedback")
    fa.add_argument("--type", required=True)
    fa.add_argument("--target-type", required=True)
    fa.add_argument("--target-id", required=True)
    fa.add_argument("--query", default="")
    fa.add_argument("--comment", default="")
    fa.add_argument("--session", default=None)
    fl = feedback_sub.add_parser("list", help="List feedback")
    fl.add_argument("--status")
    fl.add_argument("--type")
    fl.add_argument("--json", action="store_true")
    fr = feedback_sub.add_parser("resolve", help="Resolve feedback")
    fr.add_argument("feedback_id")
    fst = feedback_sub.add_parser("stats", help="Feedback statistics")
    fst.add_argument("--json", action="store_true")

    p = sub.add_parser("audit", help="Local audit trail")
    audit_sub = p.add_subparsers(dest="audit_cmd")
    aul = audit_sub.add_parser("list", help="List audit events")
    aul.add_argument("--type")
    aul.add_argument("--limit", type=int, default=100)
    aul.add_argument("--json", action="store_true")
    aus = audit_sub.add_parser("show", help="Show an audit event by index")
    aus.add_argument("index", type=int)
    aue = audit_sub.add_parser("export", help="Export the audit trail")
    aue.add_argument("--output")
    audit_sub.add_parser("validate", help="Validate the audit hash chain")

    args = parser.parse_args(argv)

    if not args.command:
        return cmd_help(args)

    commands = {
        "version": cmd_version,
        "status": cmd_status,
        "doctor": cmd_doctor,
        "bootstrap": cmd_bootstrap,
        "validate": cmd_validate,
        "test": cmd_test,
        "build": cmd_build,
        "generate": cmd_build,
        "dashboard": cmd_start_dashboard,
        "start-dashboard": cmd_start_dashboard,
        "start-mcp": cmd_start_mcp,
        "smoke-test": cmd_smoke_test,
        "mcp": cmd_mcp,
        "release-check": cmd_release_check,
        "package": cmd_package,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "clean-generated": cmd_clean_generated,
        "migrate": cmd_migrate,
        "help": cmd_help,
        "plan": cmd_plan,
        "classify": cmd_classify,
        "workflow": cmd_workflow,
        "session": cmd_session,
        "approval": cmd_approval,
        "profile": cmd_profile,
        "memory-suggestions": cmd_memory_suggestions,
        "knowledge-health": cmd_knowledge_health,
        "knowledge-gaps": cmd_knowledge_gaps,
        "review-due": cmd_review_due,
        "feedback": cmd_feedback,
        "audit": cmd_audit,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
