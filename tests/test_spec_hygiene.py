"""Regression coverage for Phase 9 Task 026: specs/ is the only canonical
specification location; .kiro/specs/ holds pointer files only.

Mirrors tasks.md TASK-026's own validation command:
  grep -rn ".kiro/specs/phase-9-professional-context" --include="*.md"
    --include="*.py" --include="*.json" --include="*.yml" .
(excluding generated/ and pointer files) returns nothing -- with one
explicit, intentional exception: tasks.md's own text describing this check.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STALE_PATTERN = re.compile(r"\.kiro/specs/phase-9-professional-context")

SCANNED_SUFFIXES = (".md", ".py", ".json", ".yml")

# TASK-026's validation command excludes generated/ (regenerable artifacts
# that legitimately index the pointer files) and the intentional pointer
# files themselves. tasks.md's own prose, which names the old path while
# describing this exact check, is also an intentional, self-referential
# mention -- not a stale reference.
EXCLUDED_DIR_PARTS = {"generated", ".git"}
ALLOWED_SELF_REFERENCES = {
    ROOT / "specs" / "phase-9-professional-context" / "tasks.md",
    Path(__file__).resolve(),
}


def _iter_scanned_files():
    for suffix in SCANNED_SUFFIXES:
        for path in ROOT.rglob(f"*{suffix}"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(ROOT).parts
            if any(part in EXCLUDED_DIR_PARTS for part in rel_parts):
                continue
            yield path


class SpecHygieneTests(unittest.TestCase):
    def test_no_stale_kiro_specs_phase9_references_outside_generated_and_pointers(self):
        offenders = []
        for path in _iter_scanned_files():
            if path in ALLOWED_SELF_REFERENCES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if STALE_PATTERN.search(text):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_kiro_specs_phase9_directory_is_pointer_only(self):
        pointer = ROOT / ".kiro" / "specs" / "phase-9-professional-context" / "README.md"
        self.assertTrue(pointer.is_file())
        text = pointer.read_text(encoding="utf-8")
        self.assertIn("specs/phase-9-professional-context/", text)
        self.assertIn("pointer", text.lower())
        # No canonical content (requirements/design/task headings) lives here.
        self.assertNotIn("### TASK-", text)
        self.assertNotIn("## Functional Requirements", text)

        siblings = [p.name for p in pointer.parent.iterdir()]
        self.assertEqual(siblings, ["README.md"])

    def test_canonical_specs_directory_has_the_three_expected_documents(self):
        canonical_dir = ROOT / "specs" / "phase-9-professional-context"
        for name in ("requirements.md", "design.md", "tasks.md"):
            self.assertTrue((canonical_dir / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
