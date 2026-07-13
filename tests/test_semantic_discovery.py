"""Comprehensive tests for the Phase 4 Semantic Discovery engine."""
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

from semantic_discovery import SCHEMA_VERSION, GENERATOR, SOURCE_GRAPH
from semantic_discovery import utils as sd_utils
from semantic_discovery import query as sd_query
from semantic_discovery import extract as sd_extract
from semantic_discovery import index as sd_index
from semantic_discovery import rank as sd_rank
from semantic_discovery import traverse as sd_traverse
from semantic_discovery import validate as sd_validate
from semantic_discovery import render as sd_render
from semantic_discovery import build as sd_build


def _minimal_index():
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": "2026-07-13T00:00:00Z",
        "generator": GENERATOR,
        "sourceGraph": SOURCE_GRAPH,
        "stats": {"documents": 1, "entities": 1, "terms": 2, "relationships": 0},
        "documents": [
            {
                "id": "doc:README.md",
                "sourcePath": "README.md",
                "title": "AI OS",
                "category": "document",
                "headings": ["AI OS", "Getting Started"],
                "snippet": "Portable AI development framework.",
                "frontMatter": {},
            }
        ],
        "entities": [
            {
                "id": "entity:concept:validation",
                "nodeId": "concept:validation",
                "type": "concept",
                "name": "validation",
                "sourcePath": ".agent/skills/communication-skill/SKILL.md",
                "metadata": {"kind": "mention"},
            }
        ],
        "termIndex": {
            "ai": ["doc:README.md", "entity:concept:validation"],
            "validation": ["entity:concept:validation"],
        },
        "diagnostics": {"warnings": [], "unindexedFiles": []},
    }


def _make_fixture(root: Path):
    """Create a minimal fixture repository."""
    (root / "README.md").write_text("# Test Repo\n\nA test repository.\n", encoding="utf-8")
    skill_dir = root / ".agent" / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nid: test-skill\nname: Test Skill\nversion: 1.0.0\nstatus: stable\n"
        "description: A test skill for validation.\ntriggers:\n  - test\n"
        "inputs:\n  - a\noutputs:\n  - b\ndependencies: []\n"
        "replaces: null\ndeprecatedBy: null\n---\n# Test Skill\n\nTest content.\n",
        encoding="utf-8",
    )
    (skill_dir / "README.md").write_text("# Test Skill Readme\n", encoding="utf-8")
    mem_dir = root / "memory" / "lessons"
    mem_dir.mkdir(parents=True)
    (mem_dir / "lesson-a.md").write_text(
        "---\nid: lesson-a\ntitle: Lesson A\ntype: lesson\nscope: global\n"
        "project: null\nstatus: active\ncreated: 2026-01-01\nupdated: 2026-01-01\n"
        "source: test\nsummary: A test lesson\ntags:\n  - testing\nrelated: []\n"
        "sensitivity: internal\nretention: permanent\n"
        "contentPath: memory/lessons/lesson-a.md\n---\n# Lesson A\n\nContent here.\n",
        encoding="utf-8",
    )
    knowledge_dir = root / "knowledge" / "architecture"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "overview.md").write_text(
        "# Architecture Overview\n\n## Validation\n\nValidation is important.\n",
        encoding="utf-8",
    )
    # Create a minimal knowledge graph
    graph_dir = root / "generated"
    graph_dir.mkdir(parents=True)
    graph = {
        "schemaVersion": "1.0.0",
        "generatedAt": "2026-07-13T00:00:00Z",
        "generator": "ai-os-knowledge-graph",
        "stats": {"nodes": 3, "edges": 2, "nodesByType": {"document": 2, "skill": 1}, "edgesByType": {"references": 1, "uses": 1}},
        "nodes": [
            {"id": "document:README.md", "type": "document", "name": "Readme", "sourcePath": "README.md", "metadata": {"extension": ".md"}},
            {"id": "skill:test-skill", "type": "skill", "name": "Test Skill", "sourcePath": ".agent/skills/test-skill/SKILL.md", "metadata": {"skillId": "test-skill"}},
            {"id": "document:knowledge/architecture/overview.md", "type": "document", "name": "Overview", "sourcePath": "knowledge/architecture/overview.md", "metadata": {"extension": ".md"}},
        ],
        "edges": [
            {"id": "edge:abc123", "type": "references", "from": "skill:test-skill", "to": "document:README.md", "metadata": {}},
            {"id": "edge:def456", "type": "uses", "from": "document:knowledge/architecture/overview.md", "to": "skill:test-skill", "metadata": {}},
        ],
        "unresolvedReferences": [],
    }
    (graph_dir / "knowledge-graph.json").write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")


# ============================================================
# Index Construction Tests
# ============================================================

class IndexConstructionTests(unittest.TestCase):
    def test_stable_document_ids(self):
        self.assertEqual(sd_utils.stable_doc_id("README.md"), "doc:README.md")
        self.assertEqual(sd_utils.stable_doc_id("a/b.md"), "doc:a/b.md")

    def test_stable_entity_ids(self):
        self.assertEqual(sd_utils.stable_entity_id("concept:test"), "entity:concept:test")

    def test_windows_path_normalization(self):
        self.assertEqual(sd_utils.normalize_path("a\\b\\c.md"), "a/b/c.md")
        self.assertEqual(sd_utils.normalize_path("a/b/c.md"), "a/b/c.md")

    def test_deterministic_document_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            idx1 = sd_index.build_discovery_index(root)
            idx2 = sd_index.build_discovery_index(root)
            self.assertEqual(
                [d["id"] for d in idx1["documents"]],
                [d["id"] for d in idx2["documents"]],
            )

    def test_deterministic_entity_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            idx1 = sd_index.build_discovery_index(root)
            idx2 = sd_index.build_discovery_index(root)
            self.assertEqual(
                [e["id"] for e in idx1["entities"]],
                [e["id"] for e in idx2["entities"]],
            )

    def test_deterministic_term_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            idx1 = sd_index.build_discovery_index(root)
            idx2 = sd_index.build_discovery_index(root)
            self.assertEqual(list(idx1["termIndex"].keys()), list(idx2["termIndex"].keys()))

    def test_ignored_directory_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            venv = root / ".venv" / "lib" / "file.md"
            venv.parent.mkdir(parents=True)
            venv.write_text("# Should not appear\n", encoding="utf-8")
            idx = sd_index.build_discovery_index(root)
            paths = [d["sourcePath"] for d in idx["documents"]]
            self.assertNotIn(".venv/lib/file.md", paths)

    def test_secret_like_file_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            (root / "secret.key").write_text("PRIVATE", encoding="utf-8")
            (root / ".env").write_text("TOKEN=x", encoding="utf-8")
            idx = sd_index.build_discovery_index(root)
            paths = [d["sourcePath"] for d in idx["documents"]]
            self.assertNotIn("secret.key", paths)
            self.assertNotIn(".env", paths)

    def test_markdown_title_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc.md").write_text("# My Title\n\nBody text.\n", encoding="utf-8")
            meta = sd_extract.extract_markdown_metadata(root / "doc.md")
            self.assertEqual(meta["title"], "My Title")

    def test_heading_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc.md").write_text("# H1\n## H2\n### H3\n", encoding="utf-8")
            meta = sd_extract.extract_markdown_metadata(root / "doc.md")
            self.assertIn("H1", meta["headings"])
            self.assertIn("H2", meta["headings"])
            self.assertIn("H3", meta["headings"])

    def test_json_metadata_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.json").write_text(
                json.dumps({"name": "Test", "description": "A description"}),
                encoding="utf-8",
            )
            meta = sd_extract.extract_json_metadata(root / "data.json")
            self.assertEqual(meta["title"], "Test")
            self.assertIn("description", meta["snippet"].lower())

    def test_no_full_memory_content_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            idx = sd_index.build_discovery_index(root)
            # Snippets should be at most 200 chars
            for doc in idx["documents"]:
                self.assertLessEqual(len(doc.get("snippet", "")), 200)


# ============================================================
# Tokenization Tests
# ============================================================

class TokenizationTests(unittest.TestCase):
    def test_lowercase_normalization(self):
        tokens = sd_query.tokenize("Hello WORLD")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)

    def test_punctuation_handling(self):
        tokens = sd_query.tokenize("hello, world! (test)")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("test", tokens)

    def test_hyphenated_terms(self):
        tokens = sd_query.tokenize("knowledge-graph")
        self.assertIn("knowledge", tokens)
        self.assertIn("graph", tokens)

    def test_snake_case_splitting(self):
        tokens = sd_query.tokenize("memory_engine")
        self.assertIn("memory", tokens)
        self.assertIn("engine", tokens)

    def test_camel_case_splitting(self):
        tokens = sd_query.tokenize("knowledgeGraph")
        self.assertIn("knowledge", tokens)
        self.assertIn("graph", tokens)

    def test_phrase_matching(self):
        self.assertTrue(sd_query.phrase_matches("The Knowledge Graph is useful", "knowledge graph"))
        self.assertFalse(sd_query.phrase_matches("Knowledge is useful", "knowledge graph"))

    def test_preserved_technical_terms(self):
        tokens = sd_query.tokenize("Use GitHub and PowerShell with MCP")
        self.assertIn("github", tokens)
        self.assertIn("powershell", tokens)
        self.assertIn("mcp", tokens)

    def test_empty_input(self):
        self.assertEqual(sd_query.tokenize(""), [])
        self.assertEqual(sd_query.tokenize_query(""), [])


# ============================================================
# Search and Ranking Tests
# ============================================================

class SearchRankingTests(unittest.TestCase):
    def test_exact_name_match_ranks_first(self):
        docs = [
            {"title": "Validation", "headings": [], "snippet": "", "sourcePath": "a.md", "category": "document", "frontMatter": {}},
            {"title": "Validation Guide Notes", "headings": [], "snippet": "About validation.", "sourcePath": "b.md", "category": "document", "frontMatter": {}},
        ]
        tokens = sd_query.tokenize_query("validation")
        results = []
        for doc in docs:
            score, fields, reasons = sd_rank.score_document(doc, "validation", tokens)
            results.append({"id": doc["sourcePath"], "score": score, "name": doc["title"], "type": doc["category"]})
        ranked = sd_rank.rank_results(results)
        self.assertEqual(ranked[0]["id"], "a.md")

    def test_exact_phrase_ranks_above_partial(self):
        docs = [
            {"title": "Knowledge Graph", "headings": [], "snippet": "", "sourcePath": "a.md", "category": "document", "frontMatter": {}},
            {"title": "Graph Theory", "headings": ["Knowledge"], "snippet": "", "sourcePath": "b.md", "category": "document", "frontMatter": {}},
        ]
        tokens = sd_query.tokenize_query("knowledge graph")
        results = []
        for doc in docs:
            score, fields, reasons = sd_rank.score_document(doc, "knowledge graph", tokens)
            results.append({"id": doc["sourcePath"], "score": score, "name": doc["title"], "type": doc["category"]})
        ranked = sd_rank.rank_results(results)
        self.assertEqual(ranked[0]["id"], "a.md")

    def test_type_filter(self):
        doc = {"title": "Test", "headings": [], "snippet": "test content", "sourcePath": "a.md", "category": "skill", "frontMatter": {}}
        tokens = sd_query.tokenize_query("test")
        score, _, _ = sd_rank.score_document(doc, "test", tokens, type_filter="document")
        self.assertEqual(score, 0)
        score2, _, _ = sd_rank.score_document(doc, "test", tokens, type_filter="skill")
        self.assertGreater(score2, 0)

    def test_path_filter(self):
        doc = {"title": "Test", "headings": [], "snippet": "content", "sourcePath": "scripts/test.py", "category": "script", "frontMatter": {}}
        tokens = sd_query.tokenize_query("test")
        score, _, _ = sd_rank.score_document(doc, "test", tokens, path_filter="knowledge/")
        self.assertEqual(score, 0)
        score2, _, _ = sd_rank.score_document(doc, "test", tokens, path_filter="scripts/")
        self.assertGreater(score2, 0)

    def test_relationship_filter_entity(self):
        entity = {"name": "Test", "type": "concept", "sourcePath": "a.md", "nodeId": "concept:test", "metadata": {}}
        tokens = sd_query.tokenize_query("test")
        neighbors = {"concept:test"}
        score, _, reasons = sd_rank.score_entity(entity, "test", tokens, neighbors=neighbors)
        self.assertGreater(score, 0)
        self.assertTrue(any("relationship" in r for r in reasons))

    def test_result_limit(self):
        results = [{"id": f"r{i}", "score": 100 - i, "type": "doc", "name": f"R{i}"} for i in range(50)]
        ranked = sd_rank.rank_results(results)[:5]
        self.assertEqual(len(ranked), 5)

    def test_stable_tie_breaking(self):
        results = [
            {"id": "b", "score": 50, "type": "document", "name": "Beta"},
            {"id": "a", "score": 50, "type": "document", "name": "Alpha"},
        ]
        ranked = sd_rank.rank_results(results)
        # Alpha comes before Beta alphabetically
        self.assertEqual(ranked[0]["id"], "a")
        self.assertEqual(ranked[1]["id"], "b")

    def test_empty_query_handling(self):
        doc = {"title": "Test", "headings": [], "snippet": "", "sourcePath": "a.md", "category": "document", "frontMatter": {}}
        tokens = sd_query.tokenize_query("")
        score, _, _ = sd_rank.score_document(doc, "", tokens)
        # Empty query should score 0
        self.assertEqual(score, 0)

    def test_no_result_handling(self):
        doc = {"title": "Unrelated", "headings": [], "snippet": "nothing", "sourcePath": "a.md", "category": "document", "frontMatter": {}}
        tokens = sd_query.tokenize_query("xyznonexistent")
        score, _, _ = sd_rank.score_document(doc, "xyznonexistent", tokens)
        self.assertEqual(score, 0)

    def test_json_result_output(self):
        results = [{"id": "r1", "score": 10, "type": "doc", "name": "Test", "sourcePath": "a.md", "matchedFields": ["title"], "reasons": ["match"], "relationships": []}]
        output = sd_render.render_search_results_json(results)
        parsed = json.loads(output)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], "r1")

    def test_scoring_explanation_present(self):
        doc = {"title": "Validation", "headings": [], "snippet": "Validation content", "sourcePath": "val.md", "category": "document", "frontMatter": {}}
        tokens = sd_query.tokenize_query("validation")
        score, fields, reasons = sd_rank.score_document(doc, "validation", tokens)
        self.assertGreater(score, 0)
        self.assertTrue(len(reasons) > 0)
        self.assertTrue(len(fields) > 0)


# ============================================================
# Graph Traversal Tests
# ============================================================

class GraphTraversalTests(unittest.TestCase):
    def _edges(self):
        return [
            {"id": "e1", "type": "references", "from": "A", "to": "B", "metadata": {}},
            {"id": "e2", "type": "uses", "from": "B", "to": "C", "metadata": {}},
            {"id": "e3", "type": "uses", "from": "C", "to": "D", "metadata": {}},
            {"id": "e4", "type": "related_to", "from": "A", "to": "D", "metadata": {}},
            {"id": "e5", "type": "references", "from": "D", "to": "A", "metadata": {}},
        ]

    def test_direct_neighbor_discovery(self):
        neighbors = sd_traverse.direct_neighbors("A", self._edges())
        node_ids = {n["nodeId"] for n in neighbors}
        self.assertIn("B", node_ids)
        self.assertIn("D", node_ids)

    def test_inbound_traversal(self):
        inbound = sd_traverse.inbound_edges("A", self._edges())
        sources = {e["from"] for e in inbound}
        self.assertIn("D", sources)

    def test_outbound_traversal(self):
        outbound = sd_traverse.outbound_edges("A", self._edges())
        targets = {e["to"] for e in outbound}
        self.assertIn("B", targets)
        self.assertIn("D", targets)

    def test_relationship_filtering(self):
        neighbors = sd_traverse.direct_neighbors("A", self._edges(), relationship="uses")
        node_ids = {n["nodeId"] for n in neighbors}
        # No outbound "uses" from A; but B->C (uses) means C is not an inbound "uses" to A
        self.assertNotIn("C", node_ids)
        # "references" includes B (outbound) and D (inbound D->A)
        ref_neighbors = sd_traverse.direct_neighbors("A", self._edges(), relationship="references")
        ref_ids = {n["nodeId"] for n in ref_neighbors}
        self.assertIn("B", ref_ids)
        self.assertIn("D", ref_ids)  # D->A is a "references" inbound edge

    def test_breadth_first_traversal(self):
        result = sd_traverse.breadth_first_traverse("A", self._edges(), depth=3)
        visited_ids = {r["nodeId"] for r in result}
        self.assertIn("B", visited_ids)
        self.assertIn("C", visited_ids)
        self.assertIn("D", visited_ids)

    def test_cycle_protection(self):
        # A->B, B->C, C->D, D->A creates a cycle
        result = sd_traverse.breadth_first_traverse("A", self._edges(), depth=10)
        # Each node should appear at most once
        node_ids = [r["nodeId"] for r in result]
        self.assertEqual(len(node_ids), len(set(node_ids)))

    def test_maximum_depth_enforcement(self):
        result = sd_traverse.breadth_first_traverse("A", self._edges(), depth=1)
        for entry in result:
            self.assertLessEqual(entry["depth"], 1)

    def test_shortest_path_found(self):
        path = sd_traverse.find_shortest_path("A", "C", self._edges())
        self.assertIsNotNone(path)
        self.assertEqual(path[0], "A")
        self.assertEqual(path[-1], "C")
        self.assertLessEqual(len(path), 4)

    def test_no_path_handled_cleanly(self):
        edges = [{"id": "e1", "type": "references", "from": "A", "to": "B", "metadata": {}}]
        path = sd_traverse.find_shortest_path("A", "Z", edges)
        self.assertIsNone(path)

    def test_unknown_node_handled_cleanly(self):
        neighbors = sd_traverse.direct_neighbors("NONEXISTENT", self._edges())
        self.assertEqual(neighbors, [])

    def test_hard_max_depth_cap(self):
        from semantic_discovery import MAX_TRAVERSAL_DEPTH
        # Requesting depth beyond MAX should be capped
        result = sd_traverse.breadth_first_traverse("A", self._edges(), depth=100)
        for entry in result:
            self.assertLessEqual(entry["depth"], MAX_TRAVERSAL_DEPTH)


# ============================================================
# Validation Tests
# ============================================================

class ValidationTests(unittest.TestCase):
    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(sd_validate.DiscoveryError) as ctx:
                sd_validate.load_discovery_index(path)
            self.assertIn("invalid JSON", str(ctx.exception))

    def test_invalid_root_object(self):
        failures, _ = sd_validate.validate_index_object([])
        self.assertTrue(any("root must be an object" in f for f in failures))

    def test_duplicate_document_ids(self):
        idx = _minimal_index()
        idx["documents"].append(idx["documents"][0])
        idx["stats"]["documents"] = 2
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("duplicate document id" in f for f in failures))

    def test_duplicate_entity_ids(self):
        idx = _minimal_index()
        idx["entities"].append(idx["entities"][0])
        idx["stats"]["entities"] = 2
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("duplicate entity id" in f for f in failures))

    def test_dangling_term_references(self):
        idx = _minimal_index()
        idx["termIndex"]["bad"] = ["nonexistent:id"]
        idx["stats"]["terms"] = 3
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("nonexistent id" in f for f in failures))

    def test_unsupported_schema(self):
        idx = _minimal_index()
        idx["schemaVersion"] = "99.0.0"
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("schemaVersion" in f for f in failures))

    def test_absolute_path_rejection(self):
        idx = _minimal_index()
        idx["documents"][0]["sourcePath"] = "/etc/secret"
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("absolute" in f or "invalid" in f for f in failures))

    def test_traversal_path_rejection(self):
        idx = _minimal_index()
        idx["documents"][0]["sourcePath"] = "../escape/file.md"
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("escapes" in f or "invalid" in f for f in failures))

    def test_backslash_path_rejection(self):
        idx = _minimal_index()
        idx["documents"][0]["sourcePath"] = "folder\\file.md"
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("backslash" in f or "invalid" in f for f in failures))

    def test_mismatched_statistics(self):
        idx = _minimal_index()
        idx["stats"]["documents"] = 999
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("does not match" in f for f in failures))

    def test_stale_json_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            index = sd_index.build_discovery_index(root)
            sd_build.write_index(index, root)
            # Modify index
            modified = dict(index)
            modified["stats"] = dict(index["stats"])
            modified["stats"]["documents"] = 999
            with self.assertRaises(sd_validate.DiscoveryError) as ctx:
                sd_build.check_index(modified, root)
            self.assertIn("stale", str(ctx.exception))

    def test_stale_markdown_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            index = sd_index.build_discovery_index(root)
            sd_build.write_index(index, root)
            # Modify markdown
            md_path = root / "generated" / "discovery-index.md"
            md_path.write_text(md_path.read_text(encoding="utf-8") + "\nextra line", encoding="utf-8")
            with self.assertRaises(sd_validate.DiscoveryError) as ctx:
                sd_build.check_index(index, root)
            self.assertIn("stale", str(ctx.exception).lower())

    def test_generated_at_only_difference_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_fixture(root)
            index = sd_index.build_discovery_index(root)
            sd_build.write_index(index, root)
            # Change only generatedAt
            different_time = dict(index)
            different_time["generatedAt"] = "2099-01-01T00:00:00Z"
            sd_build.check_index(different_time, root)  # Should not raise

    def test_secret_like_source_in_index_rejected(self):
        idx = _minimal_index()
        idx["documents"][0]["sourcePath"] = "config.key"
        failures, _ = sd_validate.validate_index_object(idx)
        self.assertTrue(any("secret" in f.lower() for f in failures))


# ============================================================
# CLI Tests
# ============================================================

class CLITests(unittest.TestCase):
    def test_search_command(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main(["search", "knowledge graph"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("Search results", output)

    def test_related_command_valid_node(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main(["related", "concept:validation"])
        self.assertEqual(code, 0)

    def test_traverse_command(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main(["traverse", "concept:validation", "--depth", "2"])
        self.assertEqual(code, 0)

    def test_path_command(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main(["path", "concept:validation", "concept:workflow"])
        # May or may not find a path - should not crash
        self.assertIn(code, (0,))

    def test_explain_command(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main(["explain", "concept:validation", "repository validation"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("Explanation", output)

    def test_stats_command(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main(["stats"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("Documents", output)

    def test_invalid_command_nonzero(self):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = importlib.util.spec_from_file_location("discover", SCRIPTS / "discover.py")
            mod = importlib.util.module_from_spec(result)
            result.loader.exec_module(mod)
            code = mod.main([])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
