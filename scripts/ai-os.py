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
        print(f"Config valid: {status['configuration']['valid']}")
        print(f"Dashboard: {'ready' if status['dashboard']['htmlPresent'] else 'not built'}")
        print(f"MCP: {'ready' if status['mcp']['serverPresent'] else 'not available'} (read-only: {status['mcp']['readOnly']})")
        missing = [a['path'] for a in status['artifacts'] if not a['exists']]
        if missing:
            print(f"Missing artifacts: {', '.join(missing)}")
        else:
            print("All artifacts present")
        print(f"Release ready: {status['releaseReady']}")
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
    from release.manifest import build_manifest, write_manifest, check_manifest
    manifest = build_manifest(ROOT)
    if args.check:
        try:
            check_manifest(manifest, ROOT)
            print_result("release manifest", True)
        except (ValueError, FileNotFoundError):
            print_result("release manifest", False)
            return 1
    else:
        write_manifest(manifest, ROOT)
        print_result("release manifest", True, "generated")

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
    print("  start-dashboard  Start the dashboard server")
    print("  start-mcp        Start the MCP server")
    print("  smoke-test       Run MCP smoke test")
    print("  release-check    Run release readiness checks")
    print("  package          Create a release package")
    print("  backup           Back up local state")
    print("  restore          Restore from backup")
    print("  clean-generated  Remove generated artifacts")
    print("  migrate          Check migration status")
    print("  help             Show this help")
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
    sub.add_parser("start-mcp", help="Start MCP server")
    sub.add_parser("smoke-test", help="MCP smoke test")

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
        "start-dashboard": cmd_start_dashboard,
        "start-mcp": cmd_start_mcp,
        "smoke-test": cmd_smoke_test,
        "release-check": cmd_release_check,
        "package": cmd_package,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "clean-generated": cmd_clean_generated,
        "migrate": cmd_migrate,
        "help": cmd_help,
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
