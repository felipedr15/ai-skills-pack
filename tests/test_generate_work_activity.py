"""Tests for scripts/generate-work-activity.py (Task 006), including its
integration with scripts/profile/validate.py's check_evidence_resolution
(evidence-resolution warnings using real generated known refs)."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from profile.validate import check_evidence_resolution  # noqa: E402


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


work_activity = load_script("generate-work-activity.py")


def _write_memory_fixture(root: Path):
    (root / "memory" / "sessions").mkdir(parents=True)
    (root / "memory" / "sessions" / "session-ai-os-001.md").write_text(
        "---\nid: session-ai-os-001\ntitle: AI OS session\ntype: session\nscope: session\n"
        "project: ai-os\nstatus: active\ncreated: 2026-07-10\nupdated: 2026-07-12\n"
        "source: unit-test\nsummary: CONFIDENTIAL-DO-NOT-SURFACE-abc123\n"
        "tags:\n  - orchestration\nrelated: []\nsensitivity: internal\nretention: temporary\n"
        "contentPath: memory/sessions/session-ai-os-001.md\n---\n# Session\nBody text never read by the aggregator.\n",
        encoding="utf-8",
    )
    (root / "memory" / "registry.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1.0.0",
                "records": [
                    {
                        "id": "session-ai-os-001",
                        "title": "AI OS session",
                        "type": "session",
                        "scope": "session",
                        "project": "ai-os",
                        "status": "active",
                        "path": "memory/sessions/session-ai-os-001.md",
                        "tags": ["orchestration"],
                        "sensitivity": "internal",
                        "retention": "temporary",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    graph = {
        "schemaVersion": "1.0.0",
        "generatedAt": "2026-07-12T00:00:00Z",
        "generator": "ai-os-knowledge-graph",
        "stats": {"nodes": 2, "edges": 1, "nodesByType": {"memory": 1, "project": 1}, "edgesByType": {"belongs_to": 1}},
        "nodes": [
            {"id": "memory:session-ai-os-001", "type": "memory", "name": "AI OS session", "sourcePath": "memory/sessions/session-ai-os-001.md", "metadata": {}},
            {"id": "project:ai-os", "type": "project", "name": "ai-os", "sourcePath": "memory/registry.json", "metadata": {}},
        ],
        "edges": [
            {"id": "edge:abc123", "type": "belongs_to", "from": "memory:session-ai-os-001", "to": "project:ai-os", "metadata": {}},
        ],
        "unresolvedReferences": [],
    }
    (root / "generated").mkdir(parents=True, exist_ok=True)
    (root / "generated" / "knowledge-graph.json").write_text(json.dumps(graph), encoding="utf-8")


class EmptySourceTests(unittest.TestCase):
    def test_no_memory_or_graph_produces_empty_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = work_activity.build_work_activity(root)
            self.assertEqual(data["projects"], [])
            self.assertEqual(data["focusAreas"], [])
            self.assertEqual(data["activitySummary"], {"totalSessions": 0, "totalMemoryRecords": 0})


class AggregationTests(unittest.TestCase):
    def test_project_and_focus_area_aggregation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)

            self.assertEqual(len(data["projects"]), 1)
            project = data["projects"][0]
            self.assertEqual(project["project"], "ai-os")
            self.assertEqual(project["sessionCount"], 1)
            self.assertEqual(project["lastActiveAt"], "2026-07-12")
            self.assertEqual(project["relatedEntities"], ["memory:session-ai-os-001"])

            self.assertEqual(len(data["focusAreas"]), 1)
            self.assertEqual(data["focusAreas"][0]["term"], "orchestration")
            self.assertEqual(data["focusAreas"][0]["weight"], 1)

            self.assertEqual(data["activitySummary"], {"totalSessions": 1, "totalMemoryRecords": 1})

    def test_window_days_is_a_constant_not_a_filter(self):
        # windowDays is documented metadata, not applied as a wall-clock
        # filter -- otherwise identical input would produce different
        # output on different days, breaking determinism.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            self.assertEqual(data["windowDays"], work_activity.WINDOW_DAYS)
            # The 2026-07-12 record still appears regardless of how far in
            # the past that is relative to "now" when the test runs.
            self.assertEqual(data["projects"][0]["lastActiveAt"], "2026-07-12")

    def test_no_prohibited_free_text_reaches_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            rendered = work_activity.render_json(data) + work_activity.render_markdown(data)
            self.assertNotIn("CONFIDENTIAL-DO-NOT-SURFACE", rendered)
            self.assertNotIn("Body text never read", rendered)


class DeterminismAndStalenessTests(unittest.TestCase):
    def test_determinism_ignoring_generated_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            first = work_activity.build_work_activity(root)
            second = work_activity.build_work_activity(root)
            self.assertTrue(work_activity.compare_ignoring_generated_at(first, second))

    def test_stale_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            with self.assertRaises(work_activity.WorkActivityError):
                work_activity.check_report(data, root)  # nothing written yet

    def test_check_mode_performs_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            try:
                work_activity.check_report(data, root)
            except work_activity.WorkActivityError:
                pass
            self.assertFalse((root / "generated" / "work-activity.json").exists())

    def test_check_passes_after_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            work_activity.write_report(data, root)
            rebuilt = work_activity.build_work_activity(root)
            work_activity.check_report(rebuilt, root)  # must not raise

    def test_does_not_mutate_memory_or_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            before = (root / "memory" / "sessions" / "session-ai-os-001.md").read_text(encoding="utf-8")
            work_activity.build_work_activity(root)
            work_activity.write_report(work_activity.build_work_activity(root), root)
            after = (root / "memory" / "sessions" / "session-ai-os-001.md").read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertFalse((root / "profile").exists())
            self.assertFalse((root / "knowledge" / "professional-context").exists())


class KnownRefsAndEvidenceResolutionTests(unittest.TestCase):
    """Evidence-resolution warnings using real generated known refs."""

    def test_collect_known_refs_includes_project_and_focus_area_and_memory_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            refs = work_activity.collect_known_refs(data)
            self.assertIn("ai-os", refs)
            self.assertIn("orchestration", refs)
            self.assertIn("session-ai-os-001", refs)

    def test_resolvable_evidence_produces_no_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            known_refs = work_activity.collect_known_refs(data)
            entries = [{"id": "expertise-x", "evidence": [{"type": "project", "ref": "ai-os"}]}]
            warnings = check_evidence_resolution(entries, known_refs)
            self.assertEqual(warnings, [])

    def test_unresolved_evidence_is_warning_not_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_memory_fixture(root)
            data = work_activity.build_work_activity(root)
            known_refs = work_activity.collect_known_refs(data)
            entries = [
                {
                    "id": "expertise-x",
                    "evidence": [
                        {"type": "project", "ref": "ai-os"},
                        {"type": "source", "ref": "current-resume-2026"},
                    ],
                }
            ]
            warnings = check_evidence_resolution(entries, known_refs)
            self.assertEqual(len(warnings), 1)
            self.assertIn("current-resume-2026", warnings[0])
            # The entry itself is unaffected -- resolution never invalidates a claim.
            self.assertEqual(len(entries[0]["evidence"]), 2)

    def test_no_resolution_context_when_known_refs_absent(self):
        entries = [{"id": "expertise-x", "evidence": [{"type": "project", "ref": "anything"}]}]
        self.assertEqual(check_evidence_resolution(entries, known_refs=None), [])


if __name__ == "__main__":
    unittest.main()
