import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration.workflow import (
    build_workflow_registry,
    compare_registries_ignoring_generated_at,
    validate_workflow_registry,
)


class WorkflowRegistryBuildTests(unittest.TestCase):
    def test_build_produces_all_required_workflow_types(self):
        registry = build_workflow_registry(ROOT)
        intents = {w["triggerIntent"] for w in registry["workflows"]}
        self.assertGreaterEqual(len(registry["workflows"]), 8)
        self.assertIn("bug-fix", intents)
        self.assertIn("feature-development", intents)

    def test_deterministic_ordering(self):
        first = build_workflow_registry(ROOT)
        second = build_workflow_registry(ROOT)
        self.assertEqual([w["id"] for w in first["workflows"]], [w["id"] for w in second["workflows"]])

    def test_every_workflow_has_approval_gate(self):
        registry = build_workflow_registry(ROOT)
        for workflow in registry["workflows"]:
            self.assertTrue(workflow["approvalGates"], workflow["id"])

    def test_no_cycles_detected(self):
        registry = build_workflow_registry(ROOT)
        for workflow in registry["workflows"]:
            self.assertFalse(workflow["metadata"]["hasCycle"], workflow["id"])

    def test_no_unknown_agent_references(self):
        registry = build_workflow_registry(ROOT)
        for workflow in registry["workflows"]:
            self.assertEqual(workflow["metadata"]["unknownAgentRefs"], [], workflow["id"])

    def test_validation_passes_for_built_registry(self):
        registry = build_workflow_registry(ROOT)
        failures, _warnings = validate_workflow_registry(registry)
        self.assertEqual(failures, [])


class WorkflowRegistryValidationTests(unittest.TestCase):
    def test_duplicate_workflow_id_rejected(self):
        registry = build_workflow_registry(ROOT)
        registry["workflows"].append(dict(registry["workflows"][0]))
        failures, _warnings = validate_workflow_registry(registry)
        self.assertTrue(any("duplicate workflow id" in f for f in failures))

    def test_missing_approval_gate_rejected(self):
        registry = build_workflow_registry(ROOT)
        registry["workflows"][0]["approvalGates"] = []
        failures, _warnings = validate_workflow_registry(registry)
        self.assertTrue(any("no approval gate" in f for f in failures))

    def test_cycle_rejected(self):
        registry = build_workflow_registry(ROOT)
        registry["workflows"][0]["metadata"]["hasCycle"] = True
        failures, _warnings = validate_workflow_registry(registry)
        self.assertTrue(any("cyclic step dependency" in f for f in failures))

    def test_unknown_agent_reference_rejected(self):
        registry = build_workflow_registry(ROOT)
        registry["workflows"][0]["metadata"]["unknownAgentRefs"] = ["nonexistent-agent"]
        failures, _warnings = validate_workflow_registry(registry)
        self.assertTrue(any("unknown agent references" in f for f in failures))

    def test_missing_step_fields_rejected(self):
        registry = build_workflow_registry(ROOT)
        registry["workflows"][0]["steps"][0] = {"id": "broken-step"}
        failures, _warnings = validate_workflow_registry(registry)
        self.assertTrue(any("missing fields" in f for f in failures))


class WorkflowCycleDetectionUnitTests(unittest.TestCase):
    def test_explicit_cycle_is_detected(self):
        from orchestration.workflow import _has_cycle, _step_graph
        steps = [
            {"id": "a", "next": ["b"]},
            {"id": "b", "next": ["c"]},
            {"id": "c", "next": ["a"]},
        ]
        graph = _step_graph(steps)
        self.assertTrue(_has_cycle(graph))

    def test_linear_chain_has_no_cycle(self):
        from orchestration.workflow import _has_cycle, _step_graph
        steps = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        graph = _step_graph(steps)
        self.assertFalse(_has_cycle(graph))


class WorkflowRegistryStaleDetectionTests(unittest.TestCase):
    def test_identical_ignoring_generated_at_match(self):
        first = build_workflow_registry(ROOT)
        second = dict(first)
        second["generatedAt"] = "2000-01-01T00:00:00Z"
        self.assertTrue(compare_registries_ignoring_generated_at(first, second))

    def test_changed_workflow_detected_as_stale(self):
        first = build_workflow_registry(ROOT)
        second = build_workflow_registry(ROOT)
        second["workflows"][0]["description"] = "changed for test"
        self.assertFalse(compare_registries_ignoring_generated_at(first, second))


if __name__ == "__main__":
    unittest.main()
