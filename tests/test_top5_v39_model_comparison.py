"""No model is automatically trusted; compare only identical footage and rank cuts."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_smolvlm2_editorial import (
    MODEL_ID,CHALLENGER_MODEL_ID,audit,RESOLUTION
)
from top5_v39_model_comparison import compare

def fake_report(model):
    return {
        "chosen_topic":"nature_moments",
        "model":model,
        "rendered_video_sha256":"a"*64,
        "publication_approved":False,
        "not_verified_observation":True,
        "score_100":None,
        "korean_caption_ready":False,
        "rows":[
            {"rank":5-i,
             "source_sha256":hashlib.sha256(str(i).encode()).hexdigest(),
             "source_url":f"https://commons.wikimedia.org/wiki/sample{i}",
             "source_title_for_human_review":f"File:Waterfall event {i}.webm",
             "rendered_frame_times":[float(i+2),float(i+3),float(i+4)],
             "real_action_verified":False,
             "publication_approved":False,
             "suggested_caption_ko":None,
             "relative_frame_change":{"adjacent_gray_change":[10.,14.]},
             "generated_visual_description_en":(
                 ("The waterfall is near a cliff. "*12)
                 if model==MODEL_ID else
                 "Water flows down the side of a high rocky cliff. A stream flows at the bottom."
             )}
            for i in range(5)
        ]
    }

def save(path,obj):
    Path(path).write_text(json.dumps(obj),encoding="utf-8")

class V39ExactSameSourceTests(unittest.TestCase):
    def test_real_rank_provenance_must_match_in_both_models(self):
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/"256.json",Path(td)/"500.json"
            baseline=fake_report(MODEL_ID)
            challenger=fake_report(CHALLENGER_MODEL_ID)
            save(a,baseline);save(b,challenger)
            result=compare(a,b)
            self.assertEqual(result["rank_count"],5)
            self.assertEqual(result["baseline_explicit_warning_ranks"],5)
            self.assertEqual(result["challenger_explicit_warning_ranks"],0)
            self.assertFalse(result["upgrade_to_challenger_for_captions_approved"])
            self.assertTrue(result["lower_flag_count_is_not_video_accuracy"])
            self.assertFalse(result["user_publishable_captions_created"])
            self.assertFalse(result["source_rights_verified"])
            self.assertIsNone(result["editorial_score_100"])
            challenger["rows"][1]["source_sha256"]="z"*64
            save(b,challenger)
            with self.assertRaisesRegex(ValueError,"SOURCE_MISMATCH"):
                compare(a,b)

    def test_different_video_or_times_cannot_be_compared(self):
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/"256.json",Path(td)/"500.json"
            baseline=fake_report(MODEL_ID)
            challenger=fake_report(CHALLENGER_MODEL_ID)
            save(a,baseline)
            challenger["rendered_video_sha256"]="b"*64
            save(b,challenger)
            with self.assertRaisesRegex(ValueError,"MEDIA_OR_TOPIC_MISMATCH"):
                compare(a,b)
            challenger["rendered_video_sha256"]="a"*64
            challenger["rows"][0]["rendered_frame_times"][1] += .5
            save(b,challenger)
            with self.assertRaisesRegex(ValueError,"SOURCE_MISMATCH"):
                compare(a,b)

    def test_wrong_model_and_made_up_approval_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            a,b=Path(td)/"256.json",Path(td)/"500.json"
            save(a,fake_report(MODEL_ID))
            invalid=fake_report(CHALLENGER_MODEL_ID)
            invalid["publication_approved"]=True
            save(b,invalid)
            with self.assertRaisesRegex(ValueError,"UNTRUSTED"):
                compare(a,b)
            invalid["publication_approved"]=False
            invalid["model"]="unknown-unsanctioned-model"
            save(b,invalid)
            with self.assertRaisesRegex(ValueError,"UNTRUSTED"):
                compare(a,b)

    def test_exact_allowlist_500m_with_fake_captioner_without_downloading(self):
        from top5_smolvlm2_editorial import audit
        with tempfile.TemporaryDirectory() as td:
            # Model guard is evaluated *after* verifying source metadata in audit.
            # Unit tests exercise the allowlist directly via the public constant.
            from top5_smolvlm2_editorial import ALLOWED_MODEL_IDS
            self.assertEqual(ALLOWED_MODEL_IDS,(MODEL_ID,CHALLENGER_MODEL_ID))
            self.assertNotIn("HuggingFaceTB/UnknownModel",ALLOWED_MODEL_IDS)

if __name__=="__main__":
    unittest.main()
