"""Tests for Phase 9 data-layer: profile/registry.json, profile records,
expertise entries, evidence-pointer validation, and the memory/ <-> profile/
boundary guard (Tasks 001-004); also covers profile record loading
(scripts/profile/record.py, Task 012) and explicit profile switching
(scripts/profile/switch.py, Task 013).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import memory_utils
from profile import SCHEMA_VERSION
from profile import record as profile_record
from profile import registry as profile_registry
from profile import switch as profile_switch
from profile import validate as profile_validate
from profile.schema import RESERVED_PROFILE_KEYS


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
    """Write a synthetic profile/<id>.md fixture with real YAML-ish front
    matter, mirroring profile/primary.md's documented shape (design.md)."""
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


def _valid_evidence_pointer():
    return {"type": "project", "ref": "windows-11-autopilot-deployment"}


def _valid_expertise_entry(entry_id="expertise-windows-11"):
    return {
        "id": entry_id,
        "name": "Windows 11 Deployment",
        "level": "advanced",
        "evidence": [
            _valid_evidence_pointer(),
            {"type": "role", "ref": "senior-it-technical-support-analyst"},
            {"type": "source", "ref": "current-resume-2026"},
        ],
        "source": "user",
        "status": "approved",
        "createdAt": "2026-07-15T00:00:00Z",
        "updatedAt": "2026-07-15T00:00:00Z",
    }


class RegistryShapeTests(unittest.TestCase):
    def test_empty_registry_is_valid(self):
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": []}
        failures, warnings = profile_validate.validate_registry_shape(data)
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])

    def test_single_active_profile_is_valid(self):
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [_valid_registry_entry()]}
        failures, _ = profile_validate.validate_registry_shape(data)
        self.assertEqual(failures, [])

    def test_zero_active_with_profiles_present_fails(self):
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [_valid_registry_entry(active=False)]}
        failures, _ = profile_validate.validate_registry_shape(data)
        self.assertTrue(any("no active profile" in f for f in failures))

    def test_multiple_active_profiles_fails(self):
        data = {
            "schemaVersion": SCHEMA_VERSION,
            "profiles": [
                _valid_registry_entry("primary", active=True),
                _valid_registry_entry("secondary", active=True),
            ],
        }
        failures, _ = profile_validate.validate_registry_shape(data)
        self.assertTrue(any("more than one active profile" in f for f in failures))

    def test_duplicate_profile_id_fails(self):
        data = {
            "schemaVersion": SCHEMA_VERSION,
            "profiles": [
                _valid_registry_entry("primary", active=True),
                _valid_registry_entry("primary", active=False),
            ],
        }
        failures, _ = profile_validate.validate_registry_shape(data)
        self.assertTrue(any("duplicate profile id" in f for f in failures))

    def test_registry_entry_missing_required_field_fails(self):
        entry = _valid_registry_entry()
        del entry["createdAt"]
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [entry]}
        failures, _ = profile_validate.validate_registry_shape(data)
        self.assertTrue(any("createdAt" in f for f in failures))

    def test_registry_entry_non_normalized_id_fails(self):
        entry = _valid_registry_entry("Primary Profile!")
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [entry]}
        failures, _ = profile_validate.validate_registry_shape(data)
        self.assertTrue(any("normalized identifier" in f for f in failures))


class RegistryIOTests(unittest.TestCase):
    def test_load_registry_defaults_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = profile_registry.load_registry(root)
            self.assertEqual(data, {"schemaVersion": SCHEMA_VERSION, "profiles": []})

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _valid_registry_entry()
            profile_registry.save_registry(root, {"schemaVersion": SCHEMA_VERSION, "profiles": [entry]})
            loaded = profile_registry.load_registry(root)
            self.assertEqual(loaded["profiles"], [entry])

    def test_active_profile_returns_none_when_empty(self):
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": []}
        self.assertIsNone(profile_registry.active_profile(data))

    def test_active_profile_returns_none_when_none_active(self):
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [_valid_registry_entry(active=False)]}
        self.assertIsNone(profile_registry.active_profile(data))

    def test_active_profile_returns_correct_entry(self):
        entry = _valid_registry_entry()
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [entry]}
        self.assertEqual(profile_registry.active_profile(data), entry)

    def test_find_profile_by_id(self):
        entry = _valid_registry_entry()
        data = {"schemaVersion": SCHEMA_VERSION, "profiles": [entry]}
        self.assertEqual(profile_registry.find_profile(data, "primary"), entry)
        self.assertIsNone(profile_registry.find_profile(data, "nonexistent"))


class ProfileRecordValidationTests(unittest.TestCase):
    def test_valid_profile_record_passes(self):
        failures, _ = profile_validate.validate_profile_record(_valid_profile_metadata())
        self.assertEqual(failures, [])

    def test_missing_required_field_fails(self):
        metadata = _valid_profile_metadata()
        del metadata["role"]
        failures, _ = profile_validate.validate_profile_record(metadata)
        self.assertTrue(any("role" in f for f in failures))

    def test_non_normalized_id_fails(self):
        metadata = _valid_profile_metadata()
        metadata["id"] = "Primary Profile"
        failures, _ = profile_validate.validate_profile_record(metadata)
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_empty_role_fails(self):
        metadata = _valid_profile_metadata()
        metadata["role"] = "   "
        failures, _ = profile_validate.validate_profile_record(metadata)
        self.assertTrue(any("role" in f for f in failures))

    def test_responsibilities_must_be_list(self):
        metadata = _valid_profile_metadata()
        metadata["responsibilities"] = "not a list"
        failures, _ = profile_validate.validate_profile_record(metadata)
        self.assertTrue(any("responsibilities must be a list" in f for f in failures))

    def test_invalid_sensitivity_fails(self):
        metadata = _valid_profile_metadata()
        metadata["sensitivity"] = "public"
        failures, _ = profile_validate.validate_profile_record(metadata)
        self.assertTrue(any("invalid sensitivity" in f for f in failures))


class ExpertiseValidationTests(unittest.TestCase):
    def test_valid_expertise_entry_passes(self):
        failures, _ = profile_validate.validate_expertise_entry(_valid_expertise_entry())
        self.assertEqual(failures, [])

    def test_invalid_level_fails(self):
        entry = _valid_expertise_entry()
        entry["level"] = "expert"  # not in the fixed enum
        failures, _ = profile_validate.validate_expertise_entry(entry)
        self.assertTrue(any("invalid expertise level" in f for f in failures))

    def test_every_valid_level_accepted(self):
        for level in ("foundational", "working", "proficient", "advanced", "lead"):
            entry = _valid_expertise_entry()
            entry["level"] = level
            failures, _ = profile_validate.validate_expertise_entry(entry)
            self.assertEqual(failures, [], level)

    def test_missing_evidence_fails(self):
        entry = _valid_expertise_entry()
        del entry["evidence"]
        failures, _ = profile_validate.validate_expertise_entry(entry)
        self.assertTrue(any("evidence" in f for f in failures))

    def test_empty_evidence_list_fails(self):
        entry = _valid_expertise_entry()
        entry["evidence"] = []
        failures, _ = profile_validate.validate_expertise_entry(entry)
        self.assertTrue(any("at least one evidence pointer" in f for f in failures))

    def test_evidence_pointer_missing_type_fails(self):
        failures = profile_validate.validate_evidence_pointer({"ref": "windows-11-autopilot-deployment"})
        self.assertTrue(any("missing required field: type" in f for f in failures))

    def test_evidence_pointer_missing_ref_fails(self):
        failures = profile_validate.validate_evidence_pointer({"type": "project"})
        self.assertTrue(any("missing required field: ref" in f for f in failures))

    def test_evidence_pointer_invalid_type_fails(self):
        failures = profile_validate.validate_evidence_pointer({"type": "certificate", "ref": "aws-saa"})
        self.assertTrue(any("invalid evidence type" in f for f in failures))

    def test_evidence_pointer_not_an_object_fails(self):
        failures = profile_validate.validate_evidence_pointer("windows-11-autopilot-deployment")
        self.assertTrue(any("must be an object" in f for f in failures))

    def test_duplicate_expertise_id_fails(self):
        data = {
            "schemaVersion": SCHEMA_VERSION,
            "profileId": "primary",
            "updatedAt": "2026-07-15T00:00:00Z",
            "entries": [_valid_expertise_entry(), _valid_expertise_entry()],
        }
        failures, _ = profile_validate.validate_expertise_file(data)
        self.assertTrue(any("duplicate expertise entry id" in f for f in failures))


class EvidenceRefPrivacyTests(unittest.TestCase):
    """Evidence refs are normalized identifiers only — never free text, file
    paths, or contact information. This is the structural proxy design.md
    relies on to keep raw resumes/evaluation files/contact info out of
    evidence entries.
    """

    def test_valid_normalized_ref_passes(self):
        failures = profile_validate.validate_evidence_pointer(_valid_evidence_pointer())
        self.assertEqual(failures, [])

    def test_free_text_sentence_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "source", "ref": "My current resume as of 2026"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_contact_info_shaped_ref_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "source", "ref": "john.doe@county.gov"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_windows_file_path_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "source", "ref": r"C:\Users\jdoe\resume.docx"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_posix_file_path_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "source", "ref": "/home/jdoe/resume.pdf"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_path_traversal_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "source", "ref": "../../etc/passwd"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_uppercase_ref_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "role", "ref": "Senior-IT-Technical-Support-Analyst"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))

    def test_whitespace_ref_rejected(self):
        failures = profile_validate.validate_evidence_pointer(
            {"type": "project", "ref": "windows 11 deployment"}
        )
        self.assertTrue(any("normalized identifier" in f for f in failures))


class EvidenceResolutionWarningTests(unittest.TestCase):
    """Phase 9 does not require evidence refs to resolve against other data
    sources (design.md). Unresolved refs must produce a warning, never a
    failure, and must never be silently dropped.
    """

    def test_no_resolution_context_produces_no_warnings(self):
        entries = [_valid_expertise_entry()]
        warnings = profile_validate.check_evidence_resolution(entries, known_refs=None)
        self.assertEqual(warnings, [])

    def test_unresolved_ref_produces_warning_not_failure(self):
        entries = [_valid_expertise_entry()]
        known_refs = {"senior-it-technical-support-analyst", "current-resume-2026"}  # missing the project ref
        warnings = profile_validate.check_evidence_resolution(entries, known_refs=known_refs)
        self.assertEqual(len(warnings), 1)
        self.assertIn("windows-11-autopilot-deployment", warnings[0])
        # The entry itself is preserved as-authored — resolution never removes it.
        failures, _ = profile_validate.validate_expertise_entry(_valid_expertise_entry())
        self.assertEqual(failures, [])

    def test_all_refs_resolved_produces_no_warnings(self):
        entries = [_valid_expertise_entry()]
        known_refs = {
            "windows-11-autopilot-deployment",
            "senior-it-technical-support-analyst",
            "current-resume-2026",
        }
        warnings = profile_validate.check_evidence_resolution(entries, known_refs=known_refs)
        self.assertEqual(warnings, [])


class MemoryProfileBoundaryTests(unittest.TestCase):
    """Task 004: memory/ records must never carry profile-only fields, and
    this must be enforced actively (not by convention), per REQ-001/REQ-005.
    """

    def _valid_memory_metadata(self):
        return {
            "id": "lesson-example-001",
            "title": "Example",
            "type": "lesson",
            "scope": "global",
            "project": None,
            "status": "active",
            "created": "2026-07-15",
            "updated": "2026-07-15",
            "source": "unit-test",
            "summary": "Example summary.",
            "tags": [],
            "related": [],
            "sensitivity": "internal",
            "retention": "permanent",
            "contentPath": "memory/lessons/lesson-example-001.md",
        }

    def test_memory_record_without_reserved_keys_passes(self):
        errors = memory_utils.validate_metadata(self._valid_memory_metadata())
        self.assertEqual(errors, [])

    def test_memory_record_with_role_key_fails(self):
        metadata = self._valid_memory_metadata()
        metadata["role"] = "Senior IT Technical Support Analyst"
        errors = memory_utils.validate_metadata(metadata)
        self.assertTrue(any("canonical profile data" in e and "role" in e for e in errors))

    def test_memory_record_with_team_key_fails(self):
        metadata = self._valid_memory_metadata()
        metadata["team"] = "IT Support"
        errors = memory_utils.validate_metadata(metadata)
        self.assertTrue(any("canonical profile data" in e and "team" in e for e in errors))

    def test_memory_record_with_reporting_to_key_fails(self):
        metadata = self._valid_memory_metadata()
        metadata["reportingTo"] = "it-manager"
        errors = memory_utils.validate_metadata(metadata)
        self.assertTrue(any("canonical profile data" in e and "reportingTo" in e for e in errors))

    def test_memory_record_with_multiple_reserved_keys_reports_all(self):
        metadata = self._valid_memory_metadata()
        metadata["role"] = "x"
        metadata["team"] = "y"
        errors = memory_utils.validate_metadata(metadata)
        combined = " ".join(errors)
        self.assertIn("role", combined)
        self.assertIn("team", combined)

    def test_reserved_keys_shared_from_single_source(self):
        # memory_utils imports RESERVED_PROFILE_KEYS from scripts/profile/schema.py
        # rather than duplicating the list (Task 004 dependency note).
        self.assertEqual(set(memory_utils.RESERVED_PROFILE_KEYS), set(RESERVED_PROFILE_KEYS))


class ProfileRecordLoadingTests(unittest.TestCase):
    """Task 012: profile show reads only the schema-defined fields from
    profile/<id>.md's front matter -- never the free-text prose body, and
    never any extra front-matter key outside schema.PROFILE_REQUIRED_FIELDS.
    """

    def test_load_profile_summary_returns_only_schema_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = _valid_profile_metadata()
            _write_profile_record_file(root, metadata, body="# Notes\nConfidential prose that must never be echoed.\n")
            entry = _valid_registry_entry()
            summary = profile_record.load_profile_summary(root, entry)
            self.assertEqual(summary["id"], "primary")
            self.assertEqual(summary["role"], metadata["role"])
            self.assertEqual(summary["team"], metadata["team"])
            self.assertEqual(summary["responsibilities"], metadata["responsibilities"])
            self.assertEqual(summary["reportingTo"], metadata["reportingTo"])
            self.assertTrue(summary["active"])
            # Exactly the fixed schema fields plus 'active' -- nothing else
            # from the record's front matter or body is ever surfaced.
            self.assertEqual(set(summary) - {"active"}, set(profile_record.PROFILE_REQUIRED_FIELDS))

    def test_prose_body_never_appears_in_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_profile_record_file(
                root, _valid_profile_metadata(),
                body="# Notes\nSECRET_PROSE_MARKER should never leak into the summary.\n")
            entry = _valid_registry_entry()
            summary = profile_record.load_profile_summary(root, entry)
            self.assertNotIn("SECRET_PROSE_MARKER", json.dumps(summary))

    def test_missing_record_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = _valid_registry_entry()
            with self.assertRaises(profile_record.ProfileRecordError):
                profile_record.load_profile_summary(root, entry)

    def test_invalid_record_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = _valid_profile_metadata()
            metadata["sensitivity"] = "public"  # invalid: only "high" is allowed
            _write_profile_record_file(root, metadata)
            entry = _valid_registry_entry()
            with self.assertRaises(profile_record.ProfileRecordError):
                profile_record.load_profile_summary(root, entry)

    def test_entry_without_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = {"id": "primary", "active": True}
            with self.assertRaises(profile_record.ProfileRecordError):
                profile_record.load_profile_summary(root, entry)


class ProfileSwitchTests(unittest.TestCase):
    """Task 013: profile.switch.switch() is pure validation + atomic
    mutation. Approval gating itself is enforced one layer up, at the CLI
    (see tests/test_profile_cli.py) -- this class covers the mutation's
    own invariants directly.
    """

    def _seed_two_profiles(self, root: Path, active="primary"):
        profiles = [
            _valid_registry_entry("primary", active=(active == "primary")),
            _valid_registry_entry("secondary", active=(active == "secondary")),
        ]
        profile_registry.save_registry(root, {"schemaVersion": SCHEMA_VERSION, "profiles": profiles})

    def test_switch_activates_target_and_deactivates_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_two_profiles(root, active="primary")
            activated = profile_switch.switch(root, "secondary")
            self.assertEqual(activated["id"], "secondary")
            data = profile_registry.load_registry(root)
            active_ids = [p["id"] for p in data["profiles"] if p["active"]]
            self.assertEqual(active_ids, ["secondary"])

    def test_switch_is_idempotent_for_already_active_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_two_profiles(root, active="primary")
            profile_switch.switch(root, "primary")
            before = (root / "profile" / "registry.json").read_bytes()
            profile_switch.switch(root, "primary")
            after = (root / "profile" / "registry.json").read_bytes()
            self.assertEqual(before, after)

    def test_unknown_target_leaves_registry_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_two_profiles(root, active="primary")
            before = (root / "profile" / "registry.json").read_bytes()
            with self.assertRaises(profile_switch.SwitchError):
                profile_switch.switch(root, "does-not-exist")
            after = (root / "profile" / "registry.json").read_bytes()
            self.assertEqual(before, after)

    def test_empty_registry_fails_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(profile_switch.SwitchError):
                profile_switch.switch(root, "primary")
            self.assertFalse((root / "profile" / "registry.json").is_file())

    def test_invalid_registry_fails_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Two active profiles -- structurally invalid.
            profiles = [
                _valid_registry_entry("primary", active=True),
                _valid_registry_entry("secondary", active=True),
            ]
            registry_path = root / "profile" / "registry.json"
            registry_path.parent.mkdir(parents=True)
            registry_path.write_text(
                json.dumps({"schemaVersion": SCHEMA_VERSION, "profiles": profiles}), encoding="utf-8")
            before = registry_path.read_bytes()
            with self.assertRaises(profile_switch.SwitchError):
                profile_switch.switch(root, "primary")
            after = registry_path.read_bytes()
            self.assertEqual(before, after)

    def test_non_activation_fields_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_two_profiles(root, active="primary")
            profile_switch.switch(root, "secondary")
            data = profile_registry.load_registry(root)
            secondary = profile_registry.find_profile(data, "secondary")
            self.assertEqual(secondary["path"], "profile/secondary.md")
            self.assertEqual(secondary["createdAt"], "2026-07-15T00:00:00Z")

    def test_atomic_write_failure_leaves_original_content_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_two_profiles(root, active="primary")
            before = (root / "profile" / "registry.json").read_bytes()
            import os as os_module
            original_replace = os_module.replace
            os_module.replace = lambda *a, **kw: (_ for _ in ()).throw(OSError("simulated atomic-write failure"))
            try:
                with self.assertRaises(OSError):
                    profile_switch.switch(root, "secondary")
            finally:
                os_module.replace = original_replace
            after = (root / "profile" / "registry.json").read_bytes()
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
