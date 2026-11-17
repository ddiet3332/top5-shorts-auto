import unittest
from src.top5_feedback_repair import apply_feedback

class FeedbackRepairTests(unittest.TestCase):
    def setUp(self):
        self.clips=[{"caption":"old","duration_sec":12,"cut_start":2} for _ in range(5)]
    def test_rank_one_maps_to_last_clip(self):
        result,report=apply_feedback(self.clips,{"schema_version":1,"repairs":[{"rank":1,"action":"revise_caption","caption":"new"}]})
        self.assertEqual(result[4]["caption"],"new")
        self.assertEqual(result[0]["caption"],"old")
    def test_shift_clamps_to_source(self):
        result,_=apply_feedback(self.clips,{"schema_version":1,"repairs":[{"rank":5,"action":"shift_highlight","delta_seconds":3}]})
        self.assertEqual(result[0]["cut_start"],5)
    def test_unknown_source_replacement_is_not_permitted(self):
        result,report=apply_feedback(self.clips,{"schema_version":1,"repairs":[{"rank":3,"action":"replace_source","url":"https://example.com"}]})
        self.assertFalse(report["applied"])
        self.assertEqual(result,self.clips)
    def test_invalid_schema_fails(self):
        with self.assertRaises(ValueError):
            apply_feedback(self.clips,{"repairs":[]})
if __name__=="__main__":unittest.main()
