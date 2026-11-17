import unittest
from src.editorial_gate import assess, WEIGHTS

class GateTests(unittest.TestCase):
    def setUp(self):
        self.card = {"dimensions": dict(WEIGHTS)}
        self.tech = {"technical_pass": True}
        self.rights = {"independent_review_complete": True,
                       "youtube_reused_content_review_pass": True,
                       "sources": [{"copyright_verified": True, "likeness_verified": True,
                                    "license_verified": True} for _ in range(5)]}

    def test_80_passes_only_with_rights(self):
        card = {"dimensions": dict(WEIGHTS)}
        card["dimensions"]["humor_payoff"] = 5
        self.assertEqual(assess(card, self.tech, self.rights)["editorial_score"], 80)
        self.assertTrue(assess(card, self.tech, self.rights)["approved"])

    def test_missing_score_never_inherits_technical_pass(self):
        self.assertIsNone(assess({}, self.tech, self.rights)["editorial_score"])

    def test_rights_missing_blocks_even_100(self):
        self.assertFalse(assess(self.card, self.tech, {})["approved"])

    def test_79_rejected(self):
        card = {"dimensions": dict(WEIGHTS)}
        card["dimensions"]["humor_payoff"] = 4
        self.assertEqual(assess(card, self.tech, self.rights)["editorial_score"], 79)
        self.assertFalse(assess(card, self.tech, self.rights)["approved"])

    def test_technical_fail_blocks(self):
        self.assertFalse(assess(self.card, {}, self.rights)["approved"])

if __name__ == "__main__":
    unittest.main()
