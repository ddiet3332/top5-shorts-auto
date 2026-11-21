"""Fail if generic TOP5 dispatch silently regresses to dog-only default."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GenericTopicDefaultTests(unittest.TestCase):
    def test_generic_topic_workflow_defaults_to_auto_and_lists_all_families(self):
        workflow = (ROOT / ".github/workflows/top5_topic_production.yml").read_text(encoding="utf-8")
        self.assertIn("default: auto", workflow)
        self.assertIn("TOPIC: ${{ github.event.inputs.topic || 'auto' }}", workflow)
        self.assertNotIn("TOPIC: ${{ github.event.inputs.topic || 'dog_surprises' }}", workflow)
        for topic in ("dog_surprises", "cat_surprises", "nature_moments",
                      "objects_oddities", "human_moments", "auto"):
            self.assertIn("- "+topic, workflow)
        self.assertIn("publication", workflow.lower())
        self.assertLess(workflow.index("Audit discovery and save failure evidence"),
                        workflow.index("Run dog-only visual source audition only if dog topic was actually selected"))
        self.assertIn('test "$RESOLVED_TOPIC" = dog_surprises', workflow)
        self.assertEqual(workflow.count("src/v37_dog_audition.py"), 1)
        self.assertIn("Skipping dog-only audition", workflow)


if __name__ == "__main__":
    unittest.main()
