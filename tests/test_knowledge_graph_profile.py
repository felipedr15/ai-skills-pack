"""Tests for Phase 9 knowledge-graph integration (Task 015): classifying
profile/*.md as a "profile" node, cross-referencing profile/registry.json
for active status, excluding snapshots, and never ingesting profile prose
or unrestricted front matter into the graph.

Scope note: per the approved design.md, this is a minimal, structural-only
classification -- there is no role/team/expertise/evidence-pointer node or
edge schema in Phase 9. design.md's Data Model explicitly defers deriving
relationships from evidence pointers to "a later phase... without any
change to this schema." These tests assert that deferral holds (no such
nodes/edges appear), not that it has been implemented.

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
from knowledge_graph import extract as kg_extract
from knowledge_graph import utils as kg_utils
from knowledge_graph import validate as kg_validate
from knowledge_graph import NODE_TYPES
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
                           responsibilities: list | None = None, extra_body: str = "") -> None:
    responsibilities = responsibilities if responsibilities is not None else ["Tier 2/3 support"]
    resp_lines = "\n".join(f"  - {item}" for item in responsibilities)
    resp_block = f"responsibilities:\n{resp_lines}\n" if responsibilities else "responsibilities: []\n"
    text = (
        "---\n"
        f"id: {profile_id}\n"
        'schemaVersion: "1.0.0"\n'
        f"role: {role}\n"
        "team: IT Support\n"
        f"{resp_block}"
        "reportingTo: it-manager\n"
        "sensitivity: high\n"
        "createdAt: 2026-07-15\n"
        "updatedAt: 2026-07-15\n"
        "---\n"
        "# Primary Professional Profile\n"
        f"{extra_body}\n"
    )
    _write(root / "profile" / f"{profile_id}.md", text)


class EmptyProfileStateTests(unittest.TestCase):
    def test_empty_registry_is_a_valid_graph_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertEqual(failures, [])
            self.assertEqual([n for n in graph["nodes"] if n["type"] == "profile"], [])

    def test_no_profile_directory_at_all_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertEqual(failures, [])


class ProfileNodeClassificationTests(unittest.TestCase):
    def test_profile_md_classified_as_profile(self):
        self.assertEqual(kg_extract.classify_document("profile/primary.md"), "profile")

    def test_profile_readme_not_classified_as_profile(self):
        self.assertEqual(kg_extract.classify_document("profile/README.md"), "document")

    def test_profile_json_files_not_classified_as_profile(self):
        # Mirrors memory/registry.json's precedent: only .md records get the
        # dedicated category; registry.json/expertise.json stay generic.
        self.assertEqual(kg_extract.classify_document("profile/registry.json"), "document")

    def test_profile_type_registered_in_node_types(self):
        self.assertIn("profile", NODE_TYPES)

    def test_one_active_synthetic_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertEqual(failures, [])
            profile_nodes = [n for n in graph["nodes"] if n["type"] == "profile"]
            self.assertEqual(len(profile_nodes), 1)
            node = profile_nodes[0]
            self.assertEqual(node["id"], "profile:primary")
            self.assertEqual(node["name"], "primary")
            self.assertEqual(node["sourcePath"], "profile/primary.md")
            self.assertTrue(node["metadata"]["active"])

    def test_multiple_profiles_one_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True), _registry_entry("secondary", False)])
            _write_profile_record(root, "primary")
            _write_profile_record(root, "secondary", role="Contractor")
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertEqual(failures, [])
            by_name = {n["name"]: n for n in graph["nodes"] if n["type"] == "profile"}
            self.assertEqual(set(by_name), {"primary", "secondary"})
            self.assertTrue(by_name["primary"]["metadata"]["active"])
            self.assertFalse(by_name["secondary"]["metadata"]["active"])


class ProfilePrivacyTests(unittest.TestCase):
    """No raw profile/expertise free text may be exposed through generic
    document traversal (Task 015 completion criteria)."""

    def test_role_team_responsibilities_never_appear_in_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(
                root, "primary",
                role="SECRET_ROLE_MARKER",
                responsibilities=["SECRET_RESPONSIBILITY_MARKER"],
                extra_body="SECRET_BODY_MARKER must never leak.\n",
            )
            graph = kg_build.build_graph(root)
            dump = json.dumps(graph)
            self.assertNotIn("SECRET_ROLE_MARKER", dump)
            self.assertNotIn("SECRET_RESPONSIBILITY_MARKER", dump)
            self.assertNotIn("SECRET_BODY_MARKER", dump)

    def test_profile_node_metadata_is_structural_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            graph = kg_build.build_graph(root)
            node = next(n for n in graph["nodes"] if n["type"] == "profile")
            self.assertEqual(set(node["metadata"]), {"schemaVersion", "active"})

    def test_profile_prose_produces_no_platform_tool_concept_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            # Body text mentions terms that WOULD normally trigger uses/related_to
            # edges for a generic document (e.g. "python", "docker").
            _write_profile_record(root, "primary", extra_body="Uses python and docker daily.\n")
            graph = kg_build.build_graph(root)
            profile_node_id = next(n["id"] for n in graph["nodes"] if n["type"] == "profile")
            outgoing = [e for e in graph["edges"] if e["from"] == profile_node_id]
            self.assertEqual(outgoing, [])

    def test_no_role_team_expertise_evidence_node_types_invented(self):
        # design.md defers evidence-derived relationships to a later phase,
        # "without any change to this schema" -- confirm this deferral holds.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            graph = kg_build.build_graph(root)
            types_present = {n["type"] for n in graph["nodes"]}
            self.assertEqual(types_present & {"role", "team", "expertise", "evidenceRef", "responsibility"}, set())


class SnapshotExclusionTests(unittest.TestCase):
    def test_snapshot_files_produce_no_nodes_or_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            _write(
                root / "knowledge" / "professional-context" / "overview.md",
                "# Professional Context Overview\n",
            )
            _write(
                root / "knowledge" / "professional-context" / "snapshots" / "professional-context-2026-01-01T000000Z.md",
                "# SECRET_SNAPSHOT_MARKER stale content\n",
            )
            graph = kg_build.build_graph(root)
            dump = json.dumps(graph)
            self.assertNotIn("SECRET_SNAPSHOT_MARKER", dump)
            self.assertNotIn("snapshots/professional-context-2026-01-01T000000Z.md", dump)
            # The curated overview itself is a normal generic document.
            self.assertIn("knowledge/professional-context/overview.md", dump)


class MalformedProfileRecordTests(unittest.TestCase):
    """Graph generation is defensive/best-effort over profile front matter,
    exactly like the existing memory-record branch: correctness is enforced
    by scripts/profile/validate.py and generate-profile-index.py --check,
    not by knowledge-graph generation itself."""

    def test_missing_id_falls_back_to_slugged_path_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "profile" / "primary.md",
                "---\nrole: Test\nteam: Test\n---\n# Profile\n",
            )
            graph = kg_build.build_graph(root)
            failures, _warnings = kg_validate.validate_graph_object(graph)
            self.assertEqual(failures, [])
            profile_nodes = [n for n in graph["nodes"] if n["type"] == "profile"]
            self.assertEqual(len(profile_nodes), 1)


class DeterminismAndNoDuplicationTests(unittest.TestCase):
    def test_deterministic_node_and_edge_ordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True), _registry_entry("secondary", False)])
            _write_profile_record(root, "primary")
            _write_profile_record(root, "secondary")
            graph1 = kg_build.build_graph(root)
            graph2 = kg_build.build_graph(root)
            self.assertTrue(kg_validate.compare_graphs_ignoring_generated_at(graph1, graph2))

    def test_no_duplicate_profile_nodes_across_generated_index_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            _write(
                root / "generated" / "profile-index.json",
                json.dumps({
                    "schemaVersion": "1.0.0", "recordCount": 1,
                    "records": [{"id": "primary", "path": "profile/primary.md", "role": "x", "team": "y", "active": True}],
                }),
            )
            graph = kg_build.build_graph(root)
            profile_source_nodes = [n for n in graph["nodes"] if n["type"] == "profile"]
            self.assertEqual(len(profile_source_nodes), 1)
            # profile-index.json becomes a single supplemental "document" node,
            # not a second "profile"-typed node for the same fact.
            supplemental = [n for n in graph["nodes"] if n.get("sourcePath") == "generated/profile-index.json"]
            self.assertEqual(len(supplemental), 1)
            self.assertEqual(supplemental[0]["type"], "document")

    def test_stale_detection_triggers_when_profile_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Root\n")
            before = kg_build.build_graph(root)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            after = kg_build.build_graph(root)
            self.assertFalse(kg_validate.compare_graphs_ignoring_generated_at(before, after))

    def test_build_graph_performs_no_filesystem_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            before = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
            kg_build.build_graph(root)
            after = {p: p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            after_paths = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
            before_paths = {p.relative_to(root).as_posix() for p in before}
            self.assertEqual(before_paths, after_paths)

    def test_windows_and_posix_profile_paths_normalize_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_registry(root, [_registry_entry("primary", True)])
            _write_profile_record(root, "primary")
            path = root / "profile" / "primary.md"
            normalized = kg_utils.normalize_relpath(path, root)
            self.assertEqual(normalized, "profile/primary.md")
            self.assertNotIn("\\", normalized)


if __name__ == "__main__":
    unittest.main()
