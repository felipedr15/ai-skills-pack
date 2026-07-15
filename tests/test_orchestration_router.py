import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from orchestration.router import classify_task


class TaskClassificationTests(unittest.TestCase):
    def test_feature_intent(self):
        result = classify_task(ROOT, "Add a new feature to export reports as PDF")
        self.assertEqual(result["intent"], "feature-development")
        self.assertEqual(result["suggestedWorkflow"], "workflow:feature-development")

    def test_bug_intent(self):
        result = classify_task(ROOT, "Fix the bug where the form throws an error on submit")
        self.assertEqual(result["intent"], "bug-fix")
        self.assertEqual(result["suggestedWorkflow"], "workflow:bug-fix")

    def test_documentation_intent(self):
        result = classify_task(ROOT, "Update the README documentation for the new CLI")
        self.assertEqual(result["intent"], "documentation")

    def test_release_intent(self):
        result = classify_task(ROOT, "Prepare the release and update the changelog")
        self.assertEqual(result["intent"], "release")

    def test_incident_intent(self):
        result = classify_task(ROOT, "Production is down, this is an urgent incident")
        self.assertEqual(result["intent"], "incident-response")

    def test_unknown_intent_for_no_signals(self):
        result = classify_task(ROOT, "zzz qqq xyzzy plugh")
        self.assertEqual(result["intent"], "unknown")
        self.assertEqual(result["confidence"], 0.0)
        self.assertIsNone(result["suggestedWorkflow"])
        self.assertTrue(result["approvalRequired"])

    def test_empty_task_is_unknown_and_safe(self):
        result = classify_task(ROOT, "")
        self.assertEqual(result["intent"], "unknown")
        self.assertTrue(result["approvalRequired"])
        self.assertIn("empty task description", result["warnings"])

    def test_deterministic_confidence(self):
        first = classify_task(ROOT, "Fix the login bug that throws an error")
        second = classify_task(ROOT, "Fix the login bug that throws an error")
        self.assertEqual(first["confidence"], second["confidence"])
        self.assertEqual(first["intent"], second["intent"])

    def test_stable_tie_breaking(self):
        # "issue" alone is a weak bug-fix signal; ensure repeated calls agree.
        results = [classify_task(ROOT, "There is an issue with the report") for _ in range(5)]
        intents = {r["intent"] for r in results}
        self.assertEqual(len(intents), 1)

    def test_explanation_reasons_present_for_known_intent(self):
        result = classify_task(ROOT, "Fix the bug in the login form")
        self.assertTrue(result["matchedSignals"])

    def test_override_workflow(self):
        result = classify_task(ROOT, "Fix the bug", requested_workflow="workflow:incident-response")
        self.assertEqual(result["suggestedWorkflow"], "workflow:incident-response")
        self.assertTrue(any("overridden" in w for w in result["warnings"]))

    def test_low_confidence_warning(self):
        result = classify_task(ROOT, "add")
        if result["intent"] != "unknown":
            self.assertLess(result["confidence"], 0.5)
            self.assertTrue(any("low confidence" in w for w in result["warnings"]))

    def test_no_randomness_across_many_calls(self):
        task = "Investigate why the dashboard is slow to load"
        results = [classify_task(ROOT, task) for _ in range(10)]
        first = results[0]
        for other in results[1:]:
            self.assertEqual(other, first)

    def test_project_and_source_path_included_in_knowledge_queries(self):
        result = classify_task(ROOT, "Fix the bug", project="mws-app", source_path="src/x.py")
        self.assertIn("mws-app", result["knowledgeQueries"])
        self.assertIn("src/x.py", result["knowledgeQueries"])


if __name__ == "__main__":
    unittest.main()
