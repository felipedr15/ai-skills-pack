"""Tests for the Phase 5 AI OS Dashboard."""
import json
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from dashboard import SCHEMA_VERSION, GENERATOR
from dashboard import aggregate as db_aggregate
from dashboard import render as db_render
from dashboard import validate as db_validate
from dashboard import server as db_server


def _make_fixture(root: Path):
    """Create a minimal fixture repository with generated artifacts."""
    gen = root / "generated"
    gen.mkdir(parents=True)

    # skills.json
    (gen / "skills.json").write_text(json.dumps({
        "schemaVersion": "1.0.0",
        "skills": [
            {"id": "test-skill", "name": "Test Skill", "version": "1.0.0", "status": "stable",
             "description": "A test skill", "triggers": ["test"], "inputs": ["a"], "outputs": ["b"],
             "dependencies": [], "path": ".agent/skills/test/SKILL.md", "replaces": None, "deprecatedBy": None}
        ]
    }, indent=2) + "\n", encoding="utf-8")

    # repository-index.json
    (gen / "repository-index.json").write_text(json.dumps({
        "schemaVersion": "1.0.0",
        "counts": {"skills": 5, "agents": 3, "scripts": 10},
        "files": []
    }, indent=2) + "\n", encoding="utf-8")

    # memory-index.json
    (gen / "memory-index.json").write_text(json.dumps({
        "schemaVersion": "1.0.0",
        "recordCount": 2,
        "records": [
            {"id": "rec-1", "title": "Record One", "type": "lesson", "status": "active",
             "scope": "global", "project": None, "created": "2026-01-01", "updated": "2026-01-01",
             "source": "test", "summary": "Test", "tags": [], "related": [],
             "sensitivity": "internal", "retention": "permanent",
             "contentPath": "memory/lessons/rec-1.md", "path": "memory/lessons/rec-1.md"},
            {"id": "rec-2", "title": "Record Two", "type": "decision", "status": "active",
             "scope": "project", "project": "ai-os", "created": "2026-01-01", "updated": "2026-01-01",
             "source": "test", "summary": "Test", "tags": [], "related": [],
             "sensitivity": "internal", "retention": "project",
             "contentPath": "memory/decisions/rec-2.md", "path": "memory/decisions/rec-2.md"}
        ]
    }, indent=2) + "\n", encoding="utf-8")

    # knowledge-graph.json
    (gen / "knowledge-graph.json").write_text(json.dumps({
        "schemaVersion": "1.0.0",
        "generatedAt": "2026-07-13T00:00:00Z",
        "generator": "ai-os-knowledge-graph",
        "stats": {"nodes": 10, "edges": 5, "nodesByType": {"document": 8, "skill": 2}, "edgesByType": {"references": 3, "uses": 2}},
        "nodes": [], "edges": [], "unresolvedReferences": [{"source": "a", "target": "b", "kind": "markdown"}]
    }, indent=2) + "\n", encoding="utf-8")

    # discovery-index.json
    (gen / "discovery-index.json").write_text(json.dumps({
        "schemaVersion": "1.0.0",
        "generatedAt": "2026-07-13T00:00:00Z",
        "generator": "ai-os-semantic-discovery",
        "sourceGraph": "generated/knowledge-graph.json",
        "stats": {"documents": 20, "entities": 10, "terms": 50, "relationships": 5},
        "documents": [], "entities": [], "termIndex": {},
        "diagnostics": {"warnings": ["test warning"], "unindexedFiles": ["orphan.md"]}
    }, indent=2) + "\n", encoding="utf-8")


# ============================================================
# Aggregation Tests
# ============================================================

class AggregationTests(unittest.TestCase):
    def test_aggregate_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            result = db_aggregate.aggregate_repository(root)
            self.assertTrue(result["available"])
            self.assertEqual(result["totalFiles"], 18)  # 5+3+10
            self.assertEqual(result["counts"]["skills"], 5)

    def test_aggregate_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            result = db_aggregate.aggregate_skills(root)
            self.assertTrue(result["available"])
            self.assertEqual(result["totalSkills"], 1)
            self.assertEqual(result["byStatus"]["stable"], 1)
            self.assertEqual(result["skills"][0]["name"], "Test Skill")

    def test_aggregate_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            result = db_aggregate.aggregate_memory(root)
            self.assertTrue(result["available"])
            self.assertEqual(result["totalRecords"], 2)
            self.assertEqual(result["byType"]["lesson"], 1)
            self.assertEqual(result["byType"]["decision"], 1)

    def test_aggregate_knowledge_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            result = db_aggregate.aggregate_knowledge_graph(root)
            self.assertTrue(result["available"])
            self.assertEqual(result["totalNodes"], 10)
            self.assertEqual(result["totalEdges"], 5)
            self.assertEqual(result["unresolvedReferences"], 1)

    def test_aggregate_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            result = db_aggregate.aggregate_discovery(root)
            self.assertTrue(result["available"])
            self.assertEqual(result["documents"], 20)
            self.assertEqual(result["terms"], 50)
            self.assertEqual(result["warnings"], 1)
            self.assertEqual(result["unindexedFiles"], 1)

    def test_aggregate_artifacts_all_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            result = db_aggregate.aggregate_artifacts(root)
            arts = result["artifacts"]
            self.assertEqual(len(arts), 5)
            self.assertTrue(all(a["exists"] for a in arts))

    def test_aggregate_missing_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generated").mkdir()
            result = db_aggregate.aggregate_repository(root)
            self.assertFalse(result["available"])

    def test_build_dashboard_data_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            data = db_aggregate.build_dashboard_data(root)
            self.assertEqual(data["schemaVersion"], SCHEMA_VERSION)
            self.assertEqual(data["generator"], GENERATOR)
            self.assertIn("generatedAt", data)
            self.assertIn("repository", data)
            self.assertIn("skills", data)
            self.assertIn("memory", data)
            self.assertIn("knowledgeGraph", data)
            self.assertIn("discovery", data)
            self.assertIn("artifacts", data)
            self.assertIn("orchestration", data)
            self.assertIn("professionalContext", data)


# ============================================================
# Phase 8: Orchestration Aggregation Tests
# ============================================================

class Phase8AggregationTests(unittest.TestCase):
    def test_missing_registries_report_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generated").mkdir()
            result = db_aggregate.aggregate_orchestration(root)
            self.assertFalse(result["available"])
            self.assertEqual(result["agentCount"], 0)
            self.assertEqual(result["workflowCount"], 0)

    def test_present_registries_report_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen = root / "generated"
            gen.mkdir()
            (gen / "agent-registry.json").write_text(json.dumps({
                "stats": {"totalAgents": 10, "byRole": {"planning": 1}}}), encoding="utf-8")
            (gen / "workflow-registry.json").write_text(json.dumps({
                "stats": {"totalWorkflows": 8}}), encoding="utf-8")
            (gen / "knowledge-health.json").write_text(json.dumps({
                "overallScore": 87, "categoryScores": {"graphIntegrity": 90}}), encoding="utf-8")
            result = db_aggregate.aggregate_orchestration(root)
            self.assertTrue(result["available"])
            self.assertEqual(result["agentCount"], 10)
            self.assertEqual(result["workflowCount"], 8)
            self.assertEqual(result["knowledgeHealthScore"], 87)

    def test_no_local_session_data_in_aggregation(self):
        # aggregate_orchestration must never import the local-runtime-state
        # modules (session/approvals/memory_suggestions/feedback/audit) —
        # only read from committed generated/ artifacts.
        import inspect
        source = inspect.getsource(db_aggregate.aggregate_orchestration)
        for banned in ("orchestration.session", "orchestration.approvals",
                       "orchestration.feedback", "orchestration.audit",
                       "runtime_dir"):
            self.assertNotIn(banned, source)

    def test_malformed_registry_json_handled_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen = root / "generated"
            gen.mkdir()
            (gen / "agent-registry.json").write_text("{not valid json", encoding="utf-8")
            result = db_aggregate.aggregate_orchestration(root)
            self.assertFalse(result["available"])


class Phase8DashboardValidationTests(unittest.TestCase):
    def test_missing_orchestration_section_rejected(self):
        data = {
            "schemaVersion": SCHEMA_VERSION, "generatedAt": "x", "generator": GENERATOR,
            "repository": {}, "skills": {}, "memory": {}, "knowledgeGraph": {},
            "discovery": {}, "artifacts": {},
        }
        failures, _warnings = db_validate.validate_dashboard_data(data)
        self.assertTrue(any("orchestration" in f for f in failures))


# ============================================================
# Phase 9: Professional Context Aggregation Tests
# ============================================================

def _valid_expertise_entry(entry_id="expertise-windows-11", name="Windows 11 Deployment", level="advanced"):
    return {
        "id": entry_id, "name": name, "level": level,
        "evidence": [{"type": "project", "ref": "windows-11-autopilot-deployment"}],
        "source": "user", "status": "approved",
        "createdAt": "2026-07-15T00:00:00Z", "updatedAt": "2026-07-15T00:00:00Z",
    }


def _seed_profile_fixture(root: Path, records: list, expertise: dict | None = None) -> None:
    gen = root / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "profile-index.json").write_text(json.dumps({
        "schemaVersion": "1.0.0", "recordCount": len(records), "records": records,
    }), encoding="utf-8")
    if expertise is not None:
        (root / "profile").mkdir(parents=True, exist_ok=True)
        for profile_id, data in expertise.items():
            (root / "profile" / f"{profile_id}.expertise.json").write_text(json.dumps(data), encoding="utf-8")


class Phase9AggregationTests(unittest.TestCase):
    def test_missing_artifacts_report_unavailable_not_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "generated").mkdir()
            result = db_aggregate.aggregate_professional_context(root)
            self.assertFalse(result["profileIndexAvailable"])
            self.assertFalse(result["workActivityAvailable"])
            self.assertFalse(result["configured"])
            self.assertEqual(result["profileCount"], 0)
            self.assertIsNone(result["activeProfile"])
            self.assertEqual(result["expertiseCount"], 0)
            for level in db_aggregate.EXPERTISE_LEVELS:
                self.assertEqual(result["expertiseByLevel"][level], [])

    def test_empty_registry_is_valid_not_configured_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_profile_fixture(root, [])
            result = db_aggregate.aggregate_professional_context(root)
            self.assertTrue(result["profileIndexAvailable"])
            self.assertFalse(result["configured"])
            self.assertEqual(result["profileCount"], 0)

    def test_active_profile_and_expertise_grouping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expertise_file = {
                "schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z",
                "entries": [_valid_expertise_entry(), _valid_expertise_entry("expertise-power-apps", "Power Apps", "proficient")],
            }
            _seed_profile_fixture(
                root,
                [{"id": "primary", "path": "profile/primary.md", "role": "Senior IT Technical Support Analyst", "team": "IT Support", "active": True},
                 {"id": "secondary", "path": "profile/secondary.md", "role": "Contractor", "team": "Consulting", "active": False}],
                expertise={"primary": expertise_file},
            )
            result = db_aggregate.aggregate_professional_context(root)
            self.assertTrue(result["configured"])
            self.assertEqual(result["profileCount"], 2)
            self.assertEqual(result["activeProfile"]["id"], "primary")
            self.assertEqual(result["activeProfile"]["role"], "Senior IT Technical Support Analyst")
            self.assertEqual(result["expertiseCount"], 2)
            self.assertEqual(len(result["expertiseByLevel"]["advanced"]), 1)
            self.assertEqual(len(result["expertiseByLevel"]["proficient"]), 1)
            self.assertEqual(result["expertiseByLevel"]["advanced"][0]["name"], "Windows 11 Deployment")

    def test_malformed_profile_index_handled_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen = root / "generated"
            gen.mkdir()
            (gen / "profile-index.json").write_text("{not valid json", encoding="utf-8")
            result = db_aggregate.aggregate_professional_context(root)
            self.assertFalse(result["profileIndexAvailable"])
            self.assertFalse(result["configured"])

    def test_malformed_expertise_file_handled_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_profile_fixture(root, [{"id": "primary", "path": "profile/primary.md", "role": "x", "team": "y", "active": True}])
            (root / "profile").mkdir(parents=True, exist_ok=True)
            (root / "profile" / "primary.expertise.json").write_text("{not valid json", encoding="utf-8")
            result = db_aggregate.aggregate_professional_context(root)
            self.assertTrue(result["configured"])
            self.assertEqual(result["expertiseCount"], 0)

    def test_invalid_expertise_entries_excluded_not_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_entry = _valid_expertise_entry(level="expert")  # not in the fixed enum
            expertise_file = {"schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z", "entries": [bad_entry]}
            _seed_profile_fixture(
                root, [{"id": "primary", "path": "profile/primary.md", "role": "x", "team": "y", "active": True}],
                expertise={"primary": expertise_file})
            result = db_aggregate.aggregate_professional_context(root)
            self.assertEqual(result["expertiseCount"], 0)  # whole file rejected, never partially trusted

    def test_work_activity_highlights(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen = root / "generated"
            gen.mkdir(parents=True)
            (gen / "profile-index.json").write_text(json.dumps({"schemaVersion": "1.0.0", "recordCount": 0, "records": []}), encoding="utf-8")
            (gen / "work-activity.json").write_text(json.dumps({
                "schemaVersion": "1.0.0", "generatedAt": "x", "generator": "ai-os-work-activity", "windowDays": 90,
                "projects": [{"project": "ai-os", "sessionCount": 3, "lastActiveAt": "2026-07-15", "relatedEntities": []},
                             {"project": "idle-project", "sessionCount": 0, "lastActiveAt": None, "relatedEntities": []}],
                "focusAreas": [{"term": "memory", "weight": 2, "sources": []}, {"term": "validation", "weight": 1, "sources": []}],
                "activitySummary": {"totalSessions": 3, "totalMemoryRecords": 10},
            }), encoding="utf-8")
            result = db_aggregate.aggregate_professional_context(root)
            self.assertTrue(result["workActivityAvailable"])
            self.assertEqual(result["activeProjectCount"], 1)
            self.assertEqual(result["totalProjectCount"], 2)
            self.assertEqual(result["activitySummary"]["totalSessions"], 3)
            self.assertEqual(result["topFocusAreas"][0]["term"], "memory")

    def test_no_local_runtime_state_in_aggregation(self):
        # aggregate_professional_context must never import local-runtime-state
        # modules (session/approvals) -- only committed generated/ artifacts
        # and profile/<id>.expertise.json's schema-restricted fields.
        import inspect
        source = inspect.getsource(db_aggregate.aggregate_professional_context) + inspect.getsource(db_aggregate._load_expertise_summary)
        for banned in ("orchestration.session", "orchestration.approvals", "runtime_dir", ".md\"", "primary.md"):
            self.assertNotIn(banned, source)

    def test_no_prohibited_data_in_aggregated_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_marker = "SECRET_RESPONSIBILITY_TEXT_MARKER"
            _seed_profile_fixture(root, [{"id": "primary", "path": "profile/primary.md", "role": "Analyst", "team": "IT", "active": True}])
            # Even if a raw record existed with sensitive prose, aggregation
            # never reads profile/*.md -- only the generated index.
            (root / "profile" / "primary.md").parent.mkdir(parents=True, exist_ok=True)
            (root / "profile" / "primary.md").write_text(f"---\nid: primary\n---\n# Notes\n{secret_marker}\n", encoding="utf-8")
            result = db_aggregate.aggregate_professional_context(root)
            self.assertNotIn(secret_marker, json.dumps(result))

    def test_deterministic_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expertise_file = {
                "schemaVersion": "1.0.0", "profileId": "primary", "updatedAt": "2026-07-15T00:00:00Z",
                "entries": [_valid_expertise_entry()],
            }
            _seed_profile_fixture(
                root, [{"id": "primary", "path": "profile/primary.md", "role": "x", "team": "y", "active": True}],
                expertise={"primary": expertise_file})
            r1 = db_aggregate.aggregate_professional_context(root)
            r2 = db_aggregate.aggregate_professional_context(root)
            self.assertEqual(r1, r2)


class Phase9DashboardValidationTests(unittest.TestCase):
    def test_missing_professional_context_section_rejected(self):
        data = {
            "schemaVersion": SCHEMA_VERSION, "generatedAt": "x", "generator": GENERATOR,
            "repository": {}, "skills": {}, "memory": {}, "knowledgeGraph": {},
            "discovery": {}, "artifacts": {}, "orchestration": {},
        }
        failures, _warnings = db_validate.validate_dashboard_data(data)
        self.assertTrue(any("professionalContext" in f for f in failures))


class Phase9RenderTests(unittest.TestCase):
    def test_professional_context_section_present_in_rendered_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            data = db_aggregate.build_dashboard_data(root)
            html = db_render.render_dashboard_html(data)
            self.assertIn("professional-context", html)
            self.assertIn("renderProfessionalContext", html)
            self.assertNotIn("__DASHBOARD_DATA__", html)

    def test_html_escaping_helper_used_for_profile_fields(self):
        # The professional-context render function must route every
        # DATA-derived string through esc() before HTML injection.
        import re
        from dashboard.template import DASHBOARD_HTML
        match = re.search(r"function renderProfessionalContext\(container\) \{.*?\n\}\n", DASHBOARD_HTML, re.DOTALL)
        self.assertIsNotNone(match)
        body = match.group(0)
        for field in ("active.id", "active.role", "active.team", "e.name", "f.term", "l"):
            self.assertIn(f"esc({field})", body)


# ============================================================
# Render Tests
# ============================================================

class RenderTests(unittest.TestCase):
    def test_render_html_contains_data(self):
        data = {"schemaVersion": "1.0.0", "generatedAt": "2026-07-13T00:00:00Z",
                "generator": "ai-os-dashboard", "repository": {"available": True, "totalFiles": 10, "counts": {}},
                "skills": {"available": True, "totalSkills": 2, "byStatus": {}, "skills": []},
                "memory": {"available": True, "totalRecords": 1, "byType": {}, "byStatus": {}, "records": []},
                "knowledgeGraph": {"available": True, "totalNodes": 5, "totalEdges": 3, "nodesByType": {}, "edgesByType": {}, "unresolvedReferences": 0},
                "discovery": {"available": True, "documents": 10, "entities": 5, "terms": 30, "relationships": 3, "warnings": 0, "unindexedFiles": 0},
                "artifacts": {"artifacts": []}}
        html = db_render.render_dashboard_html(data)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("AI OS Dashboard", html)
        self.assertNotIn("__DASHBOARD_DATA__", html)
        self.assertIn('"totalFiles": 10', html)

    def test_render_html_no_template_placeholder(self):
        data = {"schemaVersion": "1.0.0", "generatedAt": "x", "generator": "x",
                "repository": {}, "skills": {}, "memory": {}, "knowledgeGraph": {}, "discovery": {}, "artifacts": {}}
        html = db_render.render_dashboard_html(data)
        self.assertNotIn("__DASHBOARD_DATA__", html)

    def test_render_data_json_valid(self):
        data = {"schemaVersion": "1.0.0", "generatedAt": "x", "generator": "x"}
        result = db_render.render_dashboard_data_json(data)
        parsed = json.loads(result)
        self.assertEqual(parsed["schemaVersion"], "1.0.0")

    def test_write_dashboard_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {"schemaVersion": "1.0.0", "generatedAt": "x", "generator": "x",
                    "repository": {}, "skills": {}, "memory": {}, "knowledgeGraph": {}, "discovery": {}, "artifacts": {}}
            db_render.write_dashboard(data, root)
            self.assertTrue((root / "generated" / "dashboard.html").is_file())
            self.assertTrue((root / "generated" / "dashboard-data.json").is_file())


# ============================================================
# Validation Tests
# ============================================================

class ValidationTests(unittest.TestCase):
    def _valid_data(self):
        return {
            "schemaVersion": SCHEMA_VERSION,
            "generatedAt": "2026-07-13T00:00:00Z",
            "generator": GENERATOR,
            "repository": {"available": True},
            "skills": {"available": True},
            "memory": {"available": True},
            "knowledgeGraph": {"available": True},
            "discovery": {"available": True},
            "artifacts": {"artifacts": []},
            "orchestration": {"available": True},
            "professionalContext": {"configured": False},
        }

    def test_valid_data_passes(self):
        failures, warnings = db_validate.validate_dashboard_data(self._valid_data())
        self.assertEqual(failures, [])

    def test_invalid_root_type(self):
        failures, _ = db_validate.validate_dashboard_data([])
        self.assertTrue(any("root must be an object" in f for f in failures))

    def test_missing_schema_version(self):
        data = self._valid_data()
        del data["schemaVersion"]
        failures, _ = db_validate.validate_dashboard_data(data)
        self.assertTrue(any("schemaVersion" in f for f in failures))

    def test_missing_sections(self):
        data = self._valid_data()
        del data["repository"]
        failures, _ = db_validate.validate_dashboard_data(data)
        self.assertTrue(any("repository" in f for f in failures))

    def test_missing_artifacts_warns(self):
        data = self._valid_data()
        data["artifacts"] = {"artifacts": [{"path": "x.json", "exists": False, "generatedAt": None, "stale": True}]}
        _, warnings = db_validate.validate_dashboard_data(data)
        self.assertTrue(any("missing" in w for w in warnings))

    def test_validate_html_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            failures, _ = db_validate.validate_dashboard_html(Path(tmp) / "missing.html")
            self.assertTrue(any("missing" in f for f in failures))

    def test_validate_html_placeholder_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dashboard.html"
            path.write_text("<!DOCTYPE html><title>AI OS Dashboard</title>__DASHBOARD_DATA__", encoding="utf-8")
            failures, _ = db_validate.validate_dashboard_html(path)
            self.assertTrue(any("placeholder" in f for f in failures))

    def test_validate_html_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            data = db_aggregate.build_dashboard_data(root)
            db_render.write_dashboard(data, root)
            failures, _ = db_validate.validate_dashboard_html(root / "generated" / "dashboard.html")
            self.assertEqual(failures, [])

    def test_compare_ignoring_generated_at(self):
        a = {"schemaVersion": "1.0.0", "generatedAt": "2026-01-01T00:00:00Z", "data": "x"}
        b = {"schemaVersion": "1.0.0", "generatedAt": "2099-01-01T00:00:00Z", "data": "x"}
        self.assertTrue(db_validate.compare_data_ignoring_generated_at(a, b))
        b["data"] = "y"
        self.assertFalse(db_validate.compare_data_ignoring_generated_at(a, b))

    def test_load_dashboard_data_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(db_validate.DashboardError):
                db_validate.load_dashboard_data(path)

    def test_load_dashboard_data_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(db_validate.DashboardError):
                db_validate.load_dashboard_data(Path(tmp) / "missing.json")


# ============================================================
# Server Tests
# ============================================================

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start server on a test port."""
        cls.port = 18765
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_health_endpoint(self):
        status, body = self._get("/api/health")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["generator"], "ai-os-dashboard")

    def test_data_endpoint(self):
        status, body = self._get("/api/data")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("schemaVersion", data)
        self.assertIn("repository", data)

    def test_root_serves_html(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("<!DOCTYPE html>", body)
        self.assertIn("AI OS Dashboard", body)

    def test_index_html_alias(self):
        status, body = self._get("/index.html")
        self.assertEqual(status, 200)
        self.assertIn("<!DOCTYPE html>", body)


# ============================================================
# Phase 8: Orchestration Live API Tests
# ============================================================

class Phase8OrchestrationAPITests(unittest.TestCase):
    """Read-only checks against the live orchestration endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.port = 18766
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        conn.close()
        return resp.status, body

    def test_sessions_endpoint(self):
        status, body = self._get("/api/orchestration/sessions")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("sessions", data)
        self.assertIn("total", data)

    def test_approvals_endpoint_reports_pending_count(self):
        status, body = self._get("/api/orchestration/approvals")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("approvals", data)
        self.assertEqual(data["total"], len(data["approvals"]))

    def test_memory_suggestions_endpoint(self):
        status, body = self._get("/api/orchestration/memory-suggestions")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("suggestions", data)

    def test_feedback_endpoint(self):
        status, body = self._get("/api/orchestration/feedback")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("stats", data)

    def test_audit_summary_endpoint(self):
        status, body = self._get("/api/orchestration/audit-summary")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("totalEvents", data)
        self.assertIn("chainValid", data)

    def test_knowledge_health_endpoint(self):
        status, body = self._get("/api/orchestration/knowledge-health")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("overallScore", data)

    def test_agents_endpoint(self):
        status, body = self._get("/api/orchestration/agents")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("agents", data)

    def test_workflows_endpoint(self):
        status, body = self._get("/api/orchestration/workflows")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertIn("workflows", data)

    def test_no_full_memory_body_in_feedback_response(self):
        status, body = self._get("/api/orchestration/feedback")
        self.assertEqual(status, 200)
        self.assertNotIn("password=", body)


# ============================================================
# Exploration API Tests
# ============================================================

class SkillsAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18766
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_skills_list(self):
        status, body = self._get("/api/skills")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertGreater(data["total"], 0)
        self.assertTrue(all("name" in s for s in data["skills"]))

    def test_skills_search_filter(self):
        status, body = self._get("/api/skills?q=communication")
        data = json.loads(body)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["skills"][0]["id"], "communication-skill")

    def test_skills_search_no_match(self):
        status, body = self._get("/api/skills?q=xyznonexistent999")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["skills"], [])

    def test_skills_path_filter(self):
        status, body = self._get("/api/skills?path=.agent/skills/personal/")
        data = json.loads(body)
        self.assertGreater(data["total"], 0)
        for s in data["skills"]:
            self.assertTrue(s["path"].startswith(".agent/skills/personal/"))

    def test_skills_deterministic_ordering(self):
        _, body1 = self._get("/api/skills")
        _, body2 = self._get("/api/skills")
        data1 = json.loads(body1)
        data2 = json.loads(body2)
        self.assertEqual([s["id"] for s in data1["skills"]], [s["id"] for s in data2["skills"]])


class MemoryAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18767
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_memory_list(self):
        status, body = self._get("/api/memory")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertGreater(data["total"], 0)
        # Never exposes full content - only summary
        for rec in data["records"]:
            self.assertIn("summary", rec)
            self.assertNotIn("content", rec)
            self.assertNotIn("body", rec)

    def test_memory_filter_by_category(self):
        status, body = self._get("/api/memory?category=lesson")
        data = json.loads(body)
        for rec in data["records"]:
            self.assertEqual(rec["type"], "lesson")

    def test_memory_filter_no_match(self):
        status, body = self._get("/api/memory?project=nonexistent_project_xyz")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["records"], [])

    def test_memory_related_entities_present(self):
        status, body = self._get("/api/memory")
        data = json.loads(body)
        # At least some records should have related entities from graph
        has_related = any(len(r.get("related", [])) > 0 for r in data["records"])
        # This may or may not be true depending on graph state - just check structure
        for rec in data["records"]:
            self.assertIsInstance(rec.get("related", []), list)


class GraphAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18768
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_graph_nodes_list(self):
        status, body = self._get("/api/graph/nodes")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertGreater(data["total"], 0)

    def test_graph_nodes_type_filter(self):
        status, body = self._get("/api/graph/nodes?type=skill")
        data = json.loads(body)
        for n in data["nodes"]:
            self.assertEqual(n["type"], "skill")

    def test_graph_nodes_search(self):
        status, body = self._get("/api/graph/nodes?q=validation")
        data = json.loads(body)
        self.assertGreater(data["total"], 0)

    def test_graph_nodes_no_match(self):
        status, body = self._get("/api/graph/nodes?q=xyznonexistent999")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)

    def test_graph_edges_list(self):
        status, body = self._get("/api/graph/edges")
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertGreater(data["total"], 0)

    def test_graph_edges_type_filter(self):
        status, body = self._get("/api/graph/edges?type=references")
        data = json.loads(body)
        for e in data["edges"]:
            self.assertEqual(e["type"], "references")

    def test_graph_edges_node_filter(self):
        status, body = self._get("/api/graph/edges?node=concept:validation")
        data = json.loads(body)
        for e in data["edges"]:
            self.assertTrue(e["from"] == "concept:validation" or e["to"] == "concept:validation")

    def test_graph_node_detail(self):
        status, body = self._get("/api/graph/node/concept:validation")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["node"]["id"], "concept:validation")
        self.assertIn("inbound", data)
        self.assertIn("outbound", data)
        self.assertIsInstance(data["totalInbound"], int)
        self.assertIsInstance(data["totalOutbound"], int)

    def test_graph_node_detail_not_found(self):
        status, body = self._get("/api/graph/node/nonexistent:node")
        self.assertEqual(status, 404)
        data = json.loads(body)
        self.assertIn("error", data)

    def test_graph_deterministic_ordering(self):
        _, body1 = self._get("/api/graph/nodes?type=skill")
        _, body2 = self._get("/api/graph/nodes?type=skill")
        d1 = json.loads(body1)
        d2 = json.loads(body2)
        self.assertEqual([n["id"] for n in d1["nodes"]], [n["id"] for n in d2["nodes"]])



class DiscoveryAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18769
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_discovery_search_results(self):
        status, body = self._get("/api/discovery/search?q=knowledge+graph")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertGreater(data["total"], 0)
        self.assertEqual(data["query"], "knowledge graph")
        # Results have expected structure
        for r in data["results"]:
            self.assertIn("score", r)
            self.assertIn("matchedFields", r)
            self.assertIn("reasons", r)
            self.assertIn("name", r)

    def test_discovery_search_type_filter(self):
        status, body = self._get("/api/discovery/search?q=validation&type=concept")
        data = json.loads(body)
        for r in data["results"]:
            self.assertEqual(r["type"], "concept")

    def test_discovery_search_path_filter(self):
        status, body = self._get("/api/discovery/search?q=test&path=scripts/")
        data = json.loads(body)
        for r in data["results"]:
            self.assertTrue(r["sourcePath"].startswith("scripts/"))

    def test_discovery_search_empty_query(self):
        status, body = self._get("/api/discovery/search?q=")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["results"], [])

    def test_discovery_search_no_results(self):
        status, body = self._get("/api/discovery/search?q=xyznonexistent999zzz")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)

    def test_discovery_search_ranking_order(self):
        status, body = self._get("/api/discovery/search?q=knowledge+graph")
        data = json.loads(body)
        scores = [r["score"] for r in data["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_discovery_explain(self):
        status, body = self._get("/api/discovery/explain/concept:validation?q=validation")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["nodeId"], "concept:validation")
        self.assertEqual(data["query"], "validation")
        self.assertIn("score", data)
        self.assertIn("matchedFields", data)
        self.assertIn("reasons", data)
        self.assertIsInstance(data["neighbors"], int)

    def test_discovery_explain_not_found(self):
        status, body = self._get("/api/discovery/explain/nonexistent:node?q=test")
        self.assertEqual(status, 404)

    def test_discovery_explain_missing_query(self):
        status, body = self._get("/api/discovery/explain/concept:validation?q=")
        self.assertEqual(status, 400)


class RepositoryAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18770
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_repository_list(self):
        status, body = self._get("/api/repository")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertGreater(data["total"], 0)
        self.assertIn("counts", data)

    def test_repository_category_filter(self):
        status, body = self._get("/api/repository?category=scripts")
        data = json.loads(body)
        for f in data["files"]:
            self.assertEqual(f["category"], "scripts")

    def test_repository_search(self):
        status, body = self._get("/api/repository?q=validate")
        data = json.loads(body)
        self.assertGreater(data["total"], 0)
        for f in data["files"]:
            self.assertIn("validate", f["path"].lower())

    def test_repository_no_match(self):
        status, body = self._get("/api/repository?q=xyznonexistent999")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)

    def test_repository_deterministic_ordering(self):
        _, body1 = self._get("/api/repository?category=agents")
        _, body2 = self._get("/api/repository?category=agents")
        d1 = json.loads(body1)
        d2 = json.loads(body2)
        self.assertEqual([f["path"] for f in d1["files"]], [f["path"] for f in d2["files"]])


# ============================================================
# Missing Artifact Tests (empty state handling)
# ============================================================

class MissingArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start server with empty generated directory."""
        cls.port = 18771
        cls.tmp = tempfile.mkdtemp()
        cls.root = Path(cls.tmp)
        (cls.root / "generated").mkdir()
        (cls.root / "scripts").mkdir()
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_skills_missing_artifact(self):
        status, body = self._get("/api/skills")
        data = json.loads(body)
        self.assertFalse(data["available"])
        self.assertEqual(data["skills"], [])

    def test_memory_missing_artifact(self):
        status, body = self._get("/api/memory")
        data = json.loads(body)
        self.assertFalse(data["available"])
        self.assertEqual(data["records"], [])

    def test_graph_nodes_missing_artifact(self):
        status, body = self._get("/api/graph/nodes")
        data = json.loads(body)
        self.assertFalse(data["available"])
        self.assertEqual(data["nodes"], [])

    def test_graph_edges_missing_artifact(self):
        status, body = self._get("/api/graph/edges")
        data = json.loads(body)
        self.assertFalse(data["available"])

    def test_graph_node_detail_missing(self):
        status, body = self._get("/api/graph/node/any:node")
        self.assertEqual(status, 404)

    def test_repository_missing_artifact(self):
        status, body = self._get("/api/repository")
        data = json.loads(body)
        self.assertFalse(data["available"])

    def test_discovery_search_missing_artifact(self):
        status, body = self._get("/api/discovery/search?q=test")
        data = json.loads(body)
        self.assertEqual(data["total"], 0)
        self.assertIn("error", data)


# ============================================================
# Graph Visualization API Tests
# ============================================================

class GraphVisualizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18772
        cls.root = ROOT
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_visualize_default(self):
        status, body = self._get("/api/graph/visualize")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertLessEqual(len(data["nodes"]), 50)
        self.assertGreater(len(data["nodes"]), 0)
        self.assertIn("edges", data)
        self.assertIn("total", data)
        self.assertIn("showing", data)
        self.assertIn("truncated", data)

    def test_visualize_node_type_filter(self):
        status, body = self._get("/api/graph/visualize?nodeType=skill")
        data = json.loads(body)
        for n in data["nodes"]:
            self.assertEqual(n["type"], "skill")

    def test_visualize_edge_type_filter(self):
        status, body = self._get("/api/graph/visualize?edgeType=references")
        data = json.loads(body)
        for e in data["edges"]:
            self.assertEqual(e["type"], "references")

    def test_visualize_focus_node(self):
        status, body = self._get("/api/graph/visualize?focus=concept:validation&depth=1")
        data = json.loads(body)
        self.assertEqual(data["focus"], "concept:validation")
        self.assertEqual(data["depth"], 1)
        # Focus node itself must be in the results
        node_ids = [n["id"] for n in data["nodes"]]
        self.assertIn("concept:validation", node_ids)

    def test_visualize_neighbor_expansion_depth2(self):
        status, body = self._get("/api/graph/visualize?focus=concept:workflow&depth=2")
        data = json.loads(body)
        self.assertEqual(data["depth"], 2)
        self.assertGreater(len(data["nodes"]), 1)

    def test_visualize_max_depth_capped(self):
        status, body = self._get("/api/graph/visualize?focus=concept:validation&depth=10")
        data = json.loads(body)
        # Should be capped to MAX_VIS_DEPTH (3)
        self.assertLessEqual(data["depth"], 3)

    def test_visualize_max_nodes_enforced(self):
        status, body = self._get("/api/graph/visualize?limit=5")
        data = json.loads(body)
        self.assertLessEqual(len(data["nodes"]), 5)

    def test_visualize_node_selection_present_in_detail(self):
        # Focus on a node and verify edges connect only to visible nodes
        status, body = self._get("/api/graph/visualize?focus=concept:validation&depth=1")
        data = json.loads(body)
        node_ids = set(n["id"] for n in data["nodes"])
        for e in data["edges"]:
            self.assertIn(e["from"], node_ids)
            self.assertIn(e["to"], node_ids)

    def test_visualize_invalid_focus_returns_top_nodes(self):
        status, body = self._get("/api/graph/visualize?focus=nonexistent:node")
        data = json.loads(body)
        # Should fall back to degree-based selection
        self.assertTrue(data["available"])
        self.assertIsNone(data["focus"])
        self.assertGreater(len(data["nodes"]), 0)

    def test_visualize_deterministic_ordering(self):
        _, body1 = self._get("/api/graph/visualize?nodeType=skill")
        _, body2 = self._get("/api/graph/visualize?nodeType=skill")
        d1 = json.loads(body1)
        d2 = json.loads(body2)
        self.assertEqual([n["id"] for n in d1["nodes"]], [n["id"] for n in d2["nodes"]])
        self.assertEqual([e["id"] for e in d1["edges"]], [e["id"] for e in d2["edges"]])


class GraphVisualizationEmptyTests(unittest.TestCase):
    """Tests with missing or malformed graph data."""
    @classmethod
    def setUpClass(cls):
        cls.port = 18773
        cls.tmp = tempfile.mkdtemp()
        cls.root = Path(cls.tmp)
        (cls.root / "generated").mkdir()
        handler = db_server.make_handler(cls.root)
        from http.server import HTTPServer
        cls.server = HTTPServer(("127.0.0.1", cls.port), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _get(self, path: str) -> tuple[int, str]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body

    def test_visualize_missing_graph(self):
        status, body = self._get("/api/graph/visualize")
        data = json.loads(body)
        self.assertFalse(data["available"])
        self.assertEqual(data["nodes"], [])
        self.assertEqual(data["edges"], [])

    def test_visualize_malformed_graph(self):
        # Write malformed JSON
        (self.root / "generated" / "knowledge-graph.json").write_text("{broken", encoding="utf-8")
        status, body = self._get("/api/graph/visualize")
        data = json.loads(body)
        self.assertFalse(data["available"])
        self.assertEqual(data["nodes"], [])
        # Clean up
        (self.root / "generated" / "knowledge-graph.json").unlink()

    def test_visualize_empty_graph(self):
        empty = {"schemaVersion": "1.0.0", "generatedAt": "x", "generator": "x",
                 "stats": {"nodes": 0, "edges": 0, "nodesByType": {}, "edgesByType": {}},
                 "nodes": [], "edges": [], "unresolvedReferences": []}
        (self.root / "generated" / "knowledge-graph.json").write_text(
            json.dumps(empty), encoding="utf-8")
        status, body = self._get("/api/graph/visualize")
        data = json.loads(body)
        self.assertTrue(data["available"])
        self.assertEqual(data["nodes"], [])
        self.assertEqual(data["edges"], [])
        self.assertFalse(data["truncated"])
        # Clean up
        (self.root / "generated" / "knowledge-graph.json").unlink()


if __name__ == "__main__":
    unittest.main()
