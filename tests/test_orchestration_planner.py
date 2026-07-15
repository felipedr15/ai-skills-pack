import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration.planner import build_retrieval_plan, create_plan
from orchestration.router import classify_task


class RetrievalPlanTests(unittest.TestCase):
    def test_plan_includes_task_as_query(self):
        classification = classify_task(ROOT, "Fix the login bug")
        plan = build_retrieval_plan(ROOT, classification)
        self.assertIn("Fix the login bug", plan["queries"])

    def test_plan_respects_limit(self):
        classification = classify_task(ROOT, "Fix the login bug")
        plan = build_retrieval_plan(ROOT, classification, limit=5)
        self.assertEqual(plan["maxResults"], 5)

    def test_plan_types_include_expected_categories(self):
        classification = classify_task(ROOT, "Fix the login bug")
        plan = build_retrieval_plan(ROOT, classification)
        for expected in ("project", "memory", "skill", "document"):
            self.assertIn(expected, plan["types"])


class CreatePlanTests(unittest.TestCase):
    def test_workflow_selection_for_bug_fix(self):
        plan = create_plan(ROOT, "Fix the login bug", no_history=True)
        self.assertEqual(plan["selectedWorkflow"]["id"], "workflow:bug-fix")

    def test_agent_selection_matches_workflow_steps(self):
        plan = create_plan(ROOT, "Fix the login bug", no_history=True)
        agent_ids = {a["id"] for a in plan["selectedAgents"]}
        self.assertIn("agent:planner", agent_ids)
        self.assertIn("agent:builder", agent_ids)
        self.assertIn("agent:qa", agent_ids)

    def test_approval_gates_present(self):
        plan = create_plan(ROOT, "Fix the login bug", no_history=True)
        self.assertTrue(plan["approvalGates"])

    def test_validation_gates_present(self):
        plan = create_plan(ROOT, "Fix the login bug", no_history=True)
        self.assertTrue(plan["validationRequirements"])

    def test_no_execution_side_effects(self):
        # Creating a plan must never touch .ai-os/ or memory/.
        import tempfile
        with tempfile.TemporaryDirectory():
            pass  # placeholder to keep isolation conventions consistent
        ai_os_dir = ROOT / ".ai-os"
        before = set(ai_os_dir.rglob("*")) if ai_os_dir.is_dir() else set()
        create_plan(ROOT, "Fix the login bug", no_history=True)
        after = set(ai_os_dir.rglob("*")) if ai_os_dir.is_dir() else set()
        self.assertEqual(before, after)

    def test_json_serializable(self):
        import json
        plan = create_plan(ROOT, "Fix the login bug", no_history=True)
        json.dumps(plan)  # raises if not serializable

    def test_empty_knowledge_result_when_no_history(self):
        plan = create_plan(ROOT, "Fix the login bug", no_history=True)
        self.assertEqual(plan["retrievedKnowledge"], [])

    def test_workflow_override_respected(self):
        plan = create_plan(ROOT, "Fix the login bug", workflow_override="workflow:incident-response", no_history=True)
        self.assertEqual(plan["selectedWorkflow"]["id"], "workflow:incident-response")

    def test_unknown_intent_has_no_workflow(self):
        plan = create_plan(ROOT, "zzz qqq xyzzy plugh", no_history=True)
        self.assertIsNone(plan["selectedWorkflow"])
        self.assertTrue(any("could not be classified" in w for w in plan["risksAndWarnings"]))


if __name__ == "__main__":
    unittest.main()
