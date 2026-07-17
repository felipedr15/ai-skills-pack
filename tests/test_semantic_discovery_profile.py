"""Tests for Phase 9 semantic-discovery integration (Task 016): indexing
profile/ content with sanitized, structured metadata only, excluding
snapshots, and preventing duplicate results across the profile source,
generated/profile-index.json, and the knowledge graph.

Scope note: mirrors tests/test_knowledge_graph_profile.py's scope note --
this is the minimal, approved design.md integration. Expertise-level/role/
project searchable metadata is deferred (design.md defers evidence-derived
relationships to "a later phase"); these tests assert that role/team/
responsibilities text is never searchable, not that expertise search has
been implemented.

Uses synthetic fixtures only -- no real professional profile is created.
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

from knowledge_graph import build as kg_build
from knowledge_graph import render as kg_render
from semantic_discovery import index as sd_index
from semantic_discovery import extract as sd_extract
from semantic_discovery import query as sd_query
from semantic_discovery import rank as sd_rank
from semantic_discovery import validate as sd_validate
from profile import SCHEMA_VERSION
from profile import registry as profile_registry


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _seed_registry(root: Path, entries: list) -> None:
    profile_registry.save_registry(root, {"schemaVersion": SCHEMA_VERSION, "profiles": entries})


def _registry_entry(profile_id: str, active: bool) -> dict:
    return {"id": profile_id, "path": f"profile/{profile_id}.md", "active": active, "createdAt": "2026-07-15T00:00:00Z"}


def _write_profile_record(root: Path, profile_id: str, *, role: str = "Senior IT Technical Support Analyst",
                           responsibilities: list | None = None) -> None:
    responsibilities = responsibilities if responsibilities is not None else ["Tier 2/3 support"]
    resp_lines = "\n".join(f"  - {item}" for item in responsibilities)
    text = (
        "---\n"
        f"id: {profile_id}\n"
        'schemaVersion: "1.0.0"\n'
        f"role: {role}\n"
        "team: IT Support\n"
        f"responsibilities:\n{resp_lines}\n"
        "reportingTo: it-manager\n"
        "sensitivity: high\n"
        "createdAt: 2026-07-15\n"
        "updatedAt: 2026-07-15\n"
        "---\n"
        "# Primary Professional Profile\n"
    )
    _write(root / "profile" / f"{profile_id}.md", text)


def _seeded_fixture(root: Path, *, role="SECRET_ROLE_MARKER Analyst") -> None:
    _write(root / "README.md", "# Root\n")
    _seed_registry(root, [_registry_entry("primary", True)])
    _write_profile_record(root, "primary", role=role, responsibilities=["SECRET_RESPONSIBILITY_MARKER"])
    graph = kg_build.build_graph(root)
    _write(root / "generated" / "knowledge-graph.json", kg_render.render_json(graph))


class EmptyProfileStateTests(unittest.TestCase):
    def test_empty_profile_state_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            graph = kg_build.build_graph(root)
            _write(root / "generated" / "knowledge-graph.json", kg_render.render_json(graph))
            index = sd_index.build_discovery_index(root)
            failures, _warnings = sd_validate.validate_index_object(index)
            self.assertEqual(failures, [])
            self.assertEqual([d for d in index["documents"] if d["category"] == "profile"], [])
            self.assertEqual([e for e in index["entities"] if e["type"] == "profile"], [])


class ProfileIndexingTests(unittest.TestCase):
    def test_synthetic_profile_is_indexed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            index = sd_index.build_discovery_index(root)
            failures, _warnings = sd_validate.validate_index_object(index)
            self.assertEqual(failures, [])

            docs = [d for d in index["documents"] if d["category"] == "profile" and d["sourcePath"] == "profile/primary.md"]
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0]["title"], "primary")
            self.assertEqual(docs[0]["frontMatter"], {})
            self.assertEqual(docs[0]["snippet"], "")
            self.assertEqual(docs[0]["headings"], [])

            entities = [e for e in index["entities"] if e["type"] == "profile"]
            self.assertEqual(len(entities), 1)

    def test_active_profile_metadata_propagates_to_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            _seed_registry(root, [_registry_entry("primary", True), _registry_entry("secondary", False)])
            _write_profile_record(root, "primary")
            _write_profile_record(root, "secondary", role="Contractor")
            graph = kg_build.build_graph(root)
            _write(root / "generated" / "knowledge-graph.json", kg_render.render_json(graph))

            index = sd_index.build_discovery_index(root)
            by_name = {e["name"]: e for e in index["entities"] if e["type"] == "profile"}
            self.assertTrue(by_name["primary"]["metadata"]["active"])
            self.assertFalse(by_name["secondary"]["metadata"]["active"])

    def test_no_expertise_level_role_or_project_metadata_invented(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            index = sd_index.build_discovery_index(root)
            entity = next(e for e in index["entities"] if e["type"] == "profile")
            self.assertEqual(set(entity["metadata"]), {"schemaVersion", "active"})


class SnapshotHandlingTests(unittest.TestCase):
    def test_snapshots_excluded_prefer_canonical_overview(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            _write(root / "knowledge" / "professional-context" / "overview.md", "# Professional Context Overview\n")
            _write(
                root / "knowledge" / "professional-context" / "snapshots" / "professional-context-2026-01-01T000000Z.md",
                "# Old snapshot\n",
            )
            graph = kg_build.build_graph(root)
            _write(root / "generated" / "knowledge-graph.json", kg_render.render_json(graph))
            index = sd_index.build_discovery_index(root)
            sources = {d["sourcePath"] for d in index["documents"]}
            self.assertIn("knowledge/professional-context/overview.md", sources)
            self.assertFalse(any("snapshots/" in s for s in sources))


class DuplicateSuppressionTests(unittest.TestCase):
    def test_profile_index_json_not_double_counted_as_document_and_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            _write(
                root / "generated" / "profile-index.json",
                json.dumps({
                    "schemaVersion": "1.0.0", "recordCount": 1,
                    "records": [{"id": "primary", "path": "profile/primary.md", "role": "x", "team": "y", "active": True}],
                }),
            )
            # Rebuild the graph so its Pass-1b supplemental node picks up the
            # newly-created profile-index.json, then rebuild discovery.
            graph = kg_build.build_graph(root)
            _write(root / "generated" / "knowledge-graph.json", kg_render.render_json(graph))
            index = sd_index.build_discovery_index(root)

            as_document = [d for d in index["documents"] if d["sourcePath"] == "generated/profile-index.json"]
            as_entity = [e for e in index["entities"] if e.get("sourcePath") == "generated/profile-index.json"]
            self.assertEqual(as_document, [])  # never indexed as a raw document (would duplicate the entity)
            self.assertEqual(len(as_entity), 1)  # surfaces exactly once, via the graph

    def test_generated_profile_index_excluded_from_raw_file_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            _write(root / "generated" / "profile-index.json", "{}")
            _write(root / "generated" / "work-activity.json", "{}")
            files = sd_extract.discover_source_files(root)
            rels = {str(p.relative_to(root)).replace("\\", "/") for p in files}
            self.assertNotIn("generated/profile-index.json", rels)
            self.assertNotIn("generated/work-activity.json", rels)


class ProfilePrivacyAndSearchTests(unittest.TestCase):
    def test_role_and_responsibility_text_never_appears_in_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            index = sd_index.build_discovery_index(root)
            dump = json.dumps(index)
            self.assertNotIn("SECRET_ROLE_MARKER", dump)
            self.assertNotIn("SECRET_RESPONSIBILITY_MARKER", dump)

    def test_search_for_role_text_returns_no_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            index = sd_index.build_discovery_index(root)
            query = "SECRET_ROLE_MARKER"
            tokens = sd_query.tokenize_query(query)
            hits = []
            for doc in index["documents"]:
                score, _fields, _reasons = sd_rank.score_document(doc, query, tokens)
                if score > 0:
                    hits.append(doc["id"])
            for entity in index["entities"]:
                score, _fields, _reasons = sd_rank.score_entity(entity, query, tokens)
                if score > 0:
                    hits.append(entity["id"])
            self.assertEqual(hits, [])

    def test_search_for_profile_id_finds_the_profile_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            index = sd_index.build_discovery_index(root)
            query = "primary"
            tokens = sd_query.tokenize_query(query)
            results = []
            for entity in index["entities"]:
                score, fields, reasons = sd_rank.score_entity(entity, query, tokens)
                if score > 0:
                    results.append({"id": entity["id"], "type": entity["type"], "name": entity["name"], "score": score})
            ranked = sd_rank.rank_results(results)
            self.assertTrue(ranked)
            self.assertEqual(ranked[0]["type"], "profile")
            self.assertEqual(ranked[0]["name"], "primary")

    def test_active_professional_profile_query_identifies_the_active_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            _seed_registry(root, [_registry_entry("primary", True), _registry_entry("secondary", False)])
            _write_profile_record(root, "primary")
            _write_profile_record(root, "secondary")
            graph = kg_build.build_graph(root)
            _write(root / "generated" / "knowledge-graph.json", kg_render.render_json(graph))
            index = sd_index.build_discovery_index(root)

            active_entities = [e for e in index["entities"] if e["type"] == "profile" and e["metadata"].get("active")]
            self.assertEqual(len(active_entities), 1)
            self.assertEqual(active_entities[0]["name"], "primary")


class DeterminismTests(unittest.TestCase):
    def test_deterministic_document_and_entity_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            idx1 = sd_index.build_discovery_index(root)
            idx2 = sd_index.build_discovery_index(root)
            self.assertEqual([d["id"] for d in idx1["documents"]], [d["id"] for d in idx2["documents"]])
            self.assertEqual([e["id"] for e in idx1["entities"]], [e["id"] for e in idx2["entities"]])
            self.assertEqual(idx1["termIndex"], idx2["termIndex"])

    def test_deterministic_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seeded_fixture(root)
            index = sd_index.build_discovery_index(root)
            query = "primary"
            tokens = sd_query.tokenize_query(query)

            def _rank():
                results = []
                for entity in index["entities"]:
                    score, _f, _r = sd_rank.score_entity(entity, query, tokens)
                    if score > 0:
                        results.append({"id": entity["id"], "type": entity["type"], "name": entity["name"], "score": score})
                return [r["id"] for r in sd_rank.rank_results(results)]

            self.assertEqual(_rank(), _rank())


if __name__ == "__main__":
    unittest.main()
