import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration import UNIVERSAL_FORBIDDEN_ACTIONS
from orchestration.registry import (
    build_agent_registry,
    compare_registries_ignoring_generated_at,
    validate_agent_registry,
)


class AgentRegistryBuildTests(unittest.TestCase):
    def test_build_produces_stable_ids(self):
        registry = build_agent_registry(ROOT)
        ids = [a["id"] for a in registry["agents"]]
        self.assertTrue(all(i.startswith("agent:") for i in ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_deterministic_ordering(self):
        first = build_agent_registry(ROOT)
        second = build_agent_registry(ROOT)
        self.assertEqual([a["id"] for a in first["agents"]], [a["id"] for a in second["agents"]])
        self.assertEqual(first["agents"], second["agents"])

    def test_no_duplicate_agents(self):
        registry = build_agent_registry(ROOT)
        failures, _warnings = validate_agent_registry(registry)
        self.assertEqual(failures, [])

    def test_every_agent_forbids_universal_actions(self):
        registry = build_agent_registry(ROOT)
        for agent in registry["agents"]:
            for action in UNIVERSAL_FORBIDDEN_ACTIONS:
                self.assertIn(action, agent["forbiddenActions"], agent["id"])

    def test_no_agent_allows_forbidden_action(self):
        registry = build_agent_registry(ROOT)
        for agent in registry["agents"]:
            overlap = set(agent["allowedActions"]) & set(agent["forbiddenActions"])
            self.assertEqual(overlap, set(), agent["id"])

    def test_source_paths_are_normalized_and_safe(self):
        registry = build_agent_registry(ROOT)
        for agent in registry["agents"]:
            self.assertNotIn("\\", agent["sourcePath"])
            self.assertFalse(agent["sourcePath"].startswith("/"))
            self.assertNotIn("..", agent["sourcePath"])

    def test_stats_role_counts_match_agents(self):
        registry = build_agent_registry(ROOT)
        total_by_role = sum(registry["stats"]["byRole"].values())
        self.assertEqual(total_by_role, registry["stats"]["totalAgents"])
        self.assertEqual(registry["stats"]["totalAgents"], len(registry["agents"]))


class AgentRegistryValidationTests(unittest.TestCase):
    def test_duplicate_id_rejected(self):
        registry = build_agent_registry(ROOT)
        registry["agents"].append(dict(registry["agents"][0]))
        failures, _warnings = validate_agent_registry(registry)
        self.assertTrue(any("duplicate agent id" in f for f in failures))

    def test_missing_forbidden_action_rejected(self):
        registry = build_agent_registry(ROOT)
        registry["agents"][0]["forbiddenActions"] = []
        failures, _warnings = validate_agent_registry(registry)
        self.assertTrue(any("missing required forbidden actions" in f for f in failures))

    def test_unsafe_allowed_action_rejected(self):
        registry = build_agent_registry(ROOT)
        registry["agents"][0]["allowedActions"] = ["git_push"]
        failures, _warnings = validate_agent_registry(registry)
        self.assertTrue(any("forbidden capability" in f for f in failures))

    def test_unsupported_schema_version_rejected(self):
        registry = build_agent_registry(ROOT)
        registry["schemaVersion"] = "9.9.9"
        failures, _warnings = validate_agent_registry(registry)
        self.assertTrue(any("schemaVersion" in f for f in failures))

    def test_non_dict_root_rejected(self):
        failures, _warnings = validate_agent_registry([])
        self.assertTrue(failures)


class AgentRegistryStaleDetectionTests(unittest.TestCase):
    def test_identical_registries_ignoring_generated_at_match(self):
        first = build_agent_registry(ROOT)
        second = dict(first)
        second["generatedAt"] = "2000-01-01T00:00:00Z"
        self.assertTrue(compare_registries_ignoring_generated_at(first, second))

    def test_changed_agent_data_detected_as_stale(self):
        first = build_agent_registry(ROOT)
        second = build_agent_registry(ROOT)
        second["agents"][0]["description"] = "changed for test"
        self.assertFalse(compare_registries_ignoring_generated_at(first, second))


if __name__ == "__main__":
    unittest.main()
