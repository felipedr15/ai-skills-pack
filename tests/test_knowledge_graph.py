import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from knowledge_graph import build as kg_build
from knowledge_graph import extract as kg_extract
from knowledge_graph import render as kg_render
from knowledge_graph import utils as kg_utils
from knowledge_graph import validate as kg_validate


def load_generate_knowledge_graph_module():
    script_path = SCRIPTS / "generate-knowledge-graph.py"
    spec = importlib.util.spec_from_file_location("generate_knowledge_graph", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load generate-knowledge-graph.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KnowledgeGraphTests(unittest.TestCase):
    def _minimal_graph(self) -> dict:
        return {
            "schemaVersion": "1.0.0",
            "generatedAt": "2026-07-12T00:00:00Z",
            "generator": "ai-os-knowledge-graph",
            "stats": {
                "nodes": 1,
                "edges": 1,
                "nodesByType": {"document": 1},
                "edgesByType": {"references": 1},
            },
            "nodes": [
                {
                    "id": "n1",
                    "type": "document",
                    "name": "Node",
                    "sourcePath": "README.md",
                    "metadata": {},
                }
            ],
            "edges": [
                {
                    "id": "e1",
                    "type": "references",
                    "from": "n1",
                    "to": "n1",
                    "metadata": {},
                }
            ],
            "unresolvedReferences": [],
        }

    def test_stable_node_id_generation(self):
        self.assertEqual(kg_utils.node_id("skill", "creator"), kg_utils.node_id("skill", "creator"))

    def test_stable_edge_id_generation(self):
        first = kg_utils.edge_id("references", "a", "b", "x")
        second = kg_utils.edge_id("references", "a", "b", "x")
        self.assertEqual(first, second)

    def test_windows_path_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "folder" / "nested" / "file.md"
            path.parent.mkdir(parents=True)
            path.write_text("x", encoding="utf-8")
            normalized = kg_utils.normalize_relpath(path, root)
            self.assertEqual(normalized, "folder/nested/file.md")
            self.assertNotIn("\\", normalized)

    def test_markdown_link_extraction(self):
        text = "See [Doc](../README.md) and [Other](memory/README.md)."
        links = kg_utils.markdown_links(text)
        self.assertIn("../README.md", links)
        self.assertIn("memory/README.md", links)

    def test_wiki_link_extraction(self):
        text = "Use [[Memory Engine]] and [[Knowledge Graph]]."
        links = kg_utils.wiki_links(text)
        self.assertEqual(links, ["Memory Engine", "Knowledge Graph"])

    def test_duplicate_node_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [
                {"id": "n1", "type": "document", "name": "A", "sourcePath": "a.md", "metadata": {}},
                {"id": "n1", "type": "document", "name": "B", "sourcePath": "b.md", "metadata": {}},
            ],
            "edges": [],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("duplicate node id" in item for item in failures))

    def test_duplicate_edge_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [
                {"id": "n1", "type": "document", "name": "A", "sourcePath": "a.md", "metadata": {}},
                {"id": "n2", "type": "document", "name": "B", "sourcePath": "b.md", "metadata": {}},
            ],
            "edges": [
                {"id": "e1", "type": "references", "from": "n1", "to": "n2", "metadata": {}},
                {"id": "e1", "type": "references", "from": "n1", "to": "n2", "metadata": {}},
            ],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("duplicate edge id" in item for item in failures))

    def test_dangling_edge_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [
                {"id": "n1", "type": "document", "name": "A", "sourcePath": "a.md", "metadata": {}},
            ],
            "edges": [
                {"id": "e1", "type": "references", "from": "n1", "to": "missing", "metadata": {}},
            ],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("nonexistent node" in item for item in failures))

    def test_unsupported_node_type_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [{"id": "n1", "type": "unknown", "name": "A", "sourcePath": "a.md", "metadata": {}}],
            "edges": [],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("unsupported node type" in item for item in failures))

    def test_unsupported_edge_type_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [
                {"id": "n1", "type": "document", "name": "A", "sourcePath": "a.md", "metadata": {}},
                {"id": "n2", "type": "document", "name": "B", "sourcePath": "b.md", "metadata": {}},
            ],
            "edges": [{"id": "e1", "type": "unknown", "from": "n1", "to": "n2", "metadata": {}}],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("unsupported edge type" in item for item in failures))

    def test_absolute_path_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [{"id": "n1", "type": "document", "name": "A", "sourcePath": "/tmp/a.md", "metadata": {}}],
            "edges": [],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("absolute sourcePath" in item or "invalid sourcePath" in item for item in failures))

    def test_path_traversal_rejection(self):
        graph = {
            "schemaVersion": "1.0.0",
            "nodes": [{"id": "n1", "type": "document", "name": "A", "sourcePath": "../a.md", "metadata": {}}],
            "edges": [],
        }
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("escapes repository" in item or "invalid sourcePath" in item for item in failures))

    def test_deterministic_node_and_edge_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / ".agent" / "skills" / "demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nid: demo\nname: Demo\nversion: 1.0.0\nstatus: stable\ndescription: Demo skill for workflow and validation.\ntriggers:\n  - demo\ninputs:\n  - a\noutputs:\n  - b\ndependencies: []\nreplaces: null\ndeprecatedBy: null\n---\n# Demo\nSee [Readme](README.md).\n",
                encoding="utf-8",
            )
            (skill / "README.md").write_text("# Skill Readme\n", encoding="utf-8")
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            graph1 = kg_build.build_graph(root)
            graph2 = kg_build.build_graph(root)
            self.assertEqual([item["id"] for item in graph1["nodes"]], [item["id"] for item in graph2["nodes"]])
            self.assertEqual([item["id"] for item in graph1["edges"]], [item["id"] for item in graph2["edges"]])

    def test_unresolved_references_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Root\nSee [Missing](missing.md) and [[Missing Item]].\n", encoding="utf-8")
            graph = kg_build.build_graph(root)
            self.assertGreaterEqual(len(graph.get("unresolvedReferences", [])), 2)

    def test_valid_graph_generation_from_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            memory = root / "memory" / "lessons"
            memory.mkdir(parents=True)
            (memory / "lesson-a.md").write_text(
                "---\nid: lesson-a\ntitle: Lesson A\ntype: lesson\nscope: global\nproject: null\nstatus: active\ncreated: 2026-07-12\nupdated: 2026-07-12\nsource: fixture\nsummary: test\ntags: []\nrelated: []\nsensitivity: internal\nretention: permanent\ncontentPath: memory/lessons/lesson-a.md\n---\n\n# Lesson A\n",
                encoding="utf-8",
            )
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertFalse(failures)
            self.assertTrue(graph["stats"]["nodes"] >= 2)

    def test_stale_generated_graph_detection(self):
        current = {"schemaVersion": "1.0.0", "generatedAt": "2026-01-01T00:00:00Z", "nodes": [], "edges": []}
        saved = {"schemaVersion": "1.0.0", "generatedAt": "2027-01-01T00:00:00Z", "nodes": [], "edges": []}
        self.assertTrue(kg_validate.compare_graphs_ignoring_generated_at(current, saved))
        saved["nodes"].append({"id": "n1"})
        self.assertFalse(kg_validate.compare_graphs_ignoring_generated_at(current, saved))

    def test_secret_like_files_excluded_from_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Root\n", encoding="utf-8")
            (root / "secret.key").write_text("PRIVATE KEY", encoding="utf-8")
            files = kg_extract.discover_source_files(root)
            rels = [kg_utils.normalize_relpath(path, root) for path in files]
            self.assertIn("README.md", rels)
            self.assertNotIn("secret.key", rels)

    def test_json_array_graph_root_rejected(self):
        failures, _warnings = kg_validate.validate_graph_object([])
        self.assertTrue(any("graph root must be an object" in item for item in failures))

    def test_null_graph_root_rejected(self):
        failures, _warnings = kg_validate.validate_graph_object(None)
        self.assertTrue(any("graph root must be an object" in item for item in failures))

    def test_non_string_source_path_rejected(self):
        graph = self._minimal_graph()
        graph["nodes"][0]["sourcePath"] = []
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("invalid sourcePath" in item for item in failures))

    def test_list_valued_node_id_rejected(self):
        graph = self._minimal_graph()
        graph["nodes"][0]["id"] = []
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("node id must be a nonempty string" in item for item in failures))

    def test_list_valued_edge_id_rejected(self):
        graph = self._minimal_graph()
        graph["edges"][0]["id"] = []
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("edge id must be a nonempty string" in item for item in failures))

    def test_non_string_edge_from_to_rejected(self):
        graph = self._minimal_graph()
        graph["edges"][0]["from"] = []
        graph["edges"][0]["to"] = {}
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("edge from must be a nonempty string" in item for item in failures))
        self.assertTrue(any("edge to must be a nonempty string" in item for item in failures))

    def test_invalid_metadata_types_rejected(self):
        graph = self._minimal_graph()
        graph["nodes"][0]["metadata"] = []
        graph["edges"][0]["metadata"] = []
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("node metadata must be an object" in item for item in failures))
        self.assertTrue(any("edge metadata must be an object" in item for item in failures))

    def test_missing_generated_at_rejected(self):
        graph = self._minimal_graph()
        del graph["generatedAt"]
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("generatedAt must be a nonempty string" in item for item in failures))

    def test_invalid_generator_rejected(self):
        graph = self._minimal_graph()
        graph["generator"] = 123
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("generator must be a nonempty string" in item for item in failures))

    def test_mismatched_node_count_rejected(self):
        graph = self._minimal_graph()
        graph["stats"]["nodes"] = 2
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("stats.nodes does not match nodes length" in item for item in failures))

    def test_mismatched_edge_count_rejected(self):
        graph = self._minimal_graph()
        graph["stats"]["edges"] = 2
        failures, _warnings = kg_validate.validate_graph_object(graph)
        self.assertTrue(any("stats.edges does not match edges length" in item for item in failures))

    def test_missing_graph_file_load_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"
            with self.assertRaises(kg_validate.KnowledgeGraphError) as error:
                kg_validate.load_graph(path)
            self.assertIn("unable to read graph file", str(error.exception))

    def test_malformed_json_load_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(kg_validate.KnowledgeGraphError) as error:
                kg_validate.load_graph(path)
            self.assertIn("invalid JSON", str(error.exception))


class KnowledgeGraphCheckTests(unittest.TestCase):
    def _graph(self, generated_at: str = "2026-07-12T00:00:00Z") -> dict:
        return {
            "schemaVersion": "1.0.0",
            "generatedAt": generated_at,
            "generator": "ai-os-knowledge-graph",
            "stats": {
                "nodes": 1,
                "edges": 0,
                "nodesByType": {"document": 1},
                "edgesByType": {},
            },
            "nodes": [
                {
                    "id": "document:README.md",
                    "type": "document",
                    "name": "Readme",
                    "sourcePath": "README.md",
                    "metadata": {"extension": ".md"},
                }
            ],
            "edges": [],
            "unresolvedReferences": [],
        }

    def _write_generated_files(self, module, graph: dict) -> None:
        module.OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        module.OUT_JSON.write_text(kg_render.render_json(graph), encoding="utf-8", newline="\n")
        module.OUT_MD.write_text(kg_render.render_markdown(graph), encoding="utf-8", newline="\n")

    def _configure_paths(self, module, root: Path) -> None:
        module.ROOT = root
        module.OUT_JSON = root / "generated" / "knowledge-graph.json"
        module.OUT_MD = root / "generated" / "knowledge-graph.md"

    def test_modified_json_fails(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = self._graph()
            self._configure_paths(module, root)
            self._write_generated_files(module, graph)
            broken = dict(graph)
            broken["stats"] = dict(graph["stats"])
            broken["stats"]["nodes"] = 2
            module.OUT_JSON.write_text(kg_render.render_json(broken), encoding="utf-8", newline="\n")

            with self.assertRaises(module.GraphBuildError) as error:
                module.check_graph(graph)
            self.assertIn("knowledge-graph.json", str(error.exception))

    def test_modified_markdown_fails(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = self._graph()
            self._configure_paths(module, root)
            self._write_generated_files(module, graph)
            module.OUT_MD.write_text(module.OUT_MD.read_text(encoding="utf-8") + "\nextra", encoding="utf-8", newline="\n")

            with self.assertRaises(module.GraphBuildError) as error:
                module.check_graph(graph)
            self.assertIn("knowledge-graph.md", str(error.exception))

    def test_missing_json_fails(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = self._graph()
            self._configure_paths(module, root)
            self._write_generated_files(module, graph)
            module.OUT_JSON.unlink()

            with self.assertRaises(module.GraphBuildError):
                module.check_graph(graph)

    def test_missing_markdown_fails(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = self._graph()
            self._configure_paths(module, root)
            self._write_generated_files(module, graph)
            module.OUT_MD.unlink()

            with self.assertRaises(module.GraphBuildError):
                module.check_graph(graph)

    def test_malformed_json_fails_cleanly(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = self._graph()
            self._configure_paths(module, root)
            self._write_generated_files(module, graph)
            module.OUT_JSON.write_text("{", encoding="utf-8", newline="\n")
            module.build = lambda: graph

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = module.main(["--check"])

            output = stderr.getvalue()
            self.assertEqual(result, 1)
            self.assertIn("FAIL invalid JSON", output)
            self.assertNotIn("Traceback", output)

    def test_generated_at_only_difference_passes(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = self._graph("2026-07-12T00:00:00Z")
            saved = self._graph("2030-01-01T00:00:00Z")
            self._configure_paths(module, root)
            self._write_generated_files(module, saved)

            module.check_graph(current)

    def test_markdown_read_failure_fails_cleanly(self):
        module = load_generate_knowledge_graph_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = self._graph()
            self._configure_paths(module, root)
            self._write_generated_files(module, graph)
            real_md = module.OUT_MD

            class FailingMarkdownPath:
                def is_file(self):
                    return True

                def read_text(self, encoding="utf-8"):
                    raise OSError("simulated read failure")

            module.OUT_MD = FailingMarkdownPath()
            module.build = lambda: graph

            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = module.main(["--check"])

            output = stderr.getvalue()
            self.assertEqual(result, 1)
            self.assertIn("FAIL unable to read generated files", output)
            self.assertNotIn("Traceback", output)
            module.OUT_MD = real_md


if __name__ == "__main__":
    unittest.main()
