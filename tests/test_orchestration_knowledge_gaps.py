import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration.freshness import review_due, scan_freshness
from orchestration.knowledge_gaps import build_knowledge_health, validate_knowledge_health


class KnowledgeHealthRealRepoTests(unittest.TestCase):
    """Read-only checks against the real repo — nothing here writes."""

    def test_deterministic_health_score(self):
        first = build_knowledge_health(ROOT, include_live=False)
        second = build_knowledge_health(ROOT, include_live=False)
        self.assertEqual(first["overallScore"], second["overallScore"])
        self.assertEqual(first["categoryScores"], second["categoryScores"])

    def test_score_in_valid_range(self):
        report = build_knowledge_health(ROOT, include_live=False)
        self.assertTrue(0 <= report["overallScore"] <= 100)
        for score in report["categoryScores"].values():
            self.assertTrue(0 <= score <= 100)

    def test_static_report_has_no_live_signal_categories(self):
        report = build_knowledge_health(ROOT, include_live=False)
        self.assertNotIn("sessionHealth", report["categoryScores"])
        self.assertNotIn("feedbackSignal", report["categoryScores"])
        self.assertFalse(report["diagnostics"]["includesLiveSignals"])

    def test_live_report_includes_signal_categories(self):
        report = build_knowledge_health(ROOT, include_live=True)
        self.assertIn("sessionHealth", report["categoryScores"])
        self.assertIn("feedbackSignal", report["categoryScores"])

    def test_recommendation_generation(self):
        report = build_knowledge_health(ROOT, include_live=False)
        self.assertTrue(report["recommendations"])

    def test_validation_passes_for_built_report(self):
        report = build_knowledge_health(ROOT, include_live=False)
        failures, _warnings = validate_knowledge_health(report)
        self.assertEqual(failures, [])

    def test_no_query_log_diagnostic_present(self):
        report = build_knowledge_health(ROOT, include_live=False)
        self.assertIn("not logged", report["diagnostics"]["searchQueryLogging"])


class KnowledgeHealthIsolatedRepoTests(unittest.TestCase):
    """Missing-artifact handling with a fully isolated fake repo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "generated").mkdir(parents=True)
        (self.root / "knowledge").mkdir(parents=True)
        (self.root / "agents").mkdir(parents=True)
        (self.root / ".agent" / "skills").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_artifacts_score_100_not_zero(self):
        # No generated/ files at all: nothing to flag, so categories score 100.
        report = build_knowledge_health(self.root, include_live=False)
        self.assertEqual(report["categoryScores"]["graphIntegrity"], 100)
        self.assertEqual(report["categoryScores"]["workflowGovernance"], 100)

    def test_no_project_overview_detected(self):
        graph = {
            "nodes": [{"id": "project:demo", "type": "project", "name": "demo", "sourcePath": "demo-project", "metadata": {}}],
            "edges": [],
            "unresolvedReferences": [],
        }
        (self.root / "demo-project").mkdir()
        (self.root / "generated" / "knowledge-graph.json").write_text(json.dumps(graph), encoding="utf-8")
        report = build_knowledge_health(self.root, include_live=False)
        gap_categories = {g["category"] for g in report["gaps"]}
        self.assertIn("project-without-overview", gap_categories)
        self.assertIn("project-without-architecture", gap_categories)


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "knowledge").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_doc(self, name, front_matter_lines):
        text = "---\n" + "\n".join(front_matter_lines) + "\n---\n\nBody text.\n"
        (self.root / "knowledge" / name).write_text(text, encoding="utf-8")

    def test_doc_without_freshness_fields_is_ignored(self):
        self._write_doc("plain.md", ["status: active"])
        records = scan_freshness(self.root)
        self.assertEqual(records, [])

    def test_doc_with_owner_is_tracked(self):
        self._write_doc("tracked.md", ["owner: DCBA IT", "status: approved"])
        records = scan_freshness(self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["owner"], "DCBA IT")

    def test_missing_owner_flagged(self):
        self._write_doc("no-owner.md", ["lastReviewed: 2020-01-01", "reviewIntervalDays: 30"])
        records = scan_freshness(self.root)
        self.assertIn("missing owner", records[0]["issues"])

    def test_overdue_review_detected(self):
        old_date = (date.today() - timedelta(days=400)).isoformat()
        self._write_doc("overdue.md", ["owner: Team X", f"lastReviewed: {old_date}", "reviewIntervalDays: 30"])
        due = review_due(self.root)
        self.assertTrue(due)
        self.assertTrue(due[0]["overdue"])

    def test_due_soon_detected_within_window(self):
        recent_date = (date.today() - timedelta(days=25)).isoformat()
        self._write_doc("due-soon.md", ["owner: Team X", f"lastReviewed: {recent_date}", "reviewIntervalDays: 30"])
        due = review_due(self.root, days=10)
        self.assertTrue(due)
        self.assertTrue(due[0]["dueSoon"])

    def test_invalid_date_flagged(self):
        self._write_doc("bad-date.md", ["owner: Team X", "lastReviewed: not-a-date"])
        records = scan_freshness(self.root)
        self.assertTrue(any("invalid lastReviewed" in i for i in records[0]["issues"]))

    def test_deprecated_status_flagged(self):
        self._write_doc("deprecated.md", ["owner: Team X", "status: deprecated"])
        records = scan_freshness(self.root)
        self.assertIn("deprecated document still referenced", records[0]["issues"])

    def test_never_writes_review_dates(self):
        self._write_doc("tracked.md", ["owner: Team X", "lastReviewed: 2020-01-01", "reviewIntervalDays: 30"])
        before = (self.root / "knowledge" / "tracked.md").read_text(encoding="utf-8")
        review_due(self.root)
        after = (self.root / "knowledge" / "tracked.md").read_text(encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
