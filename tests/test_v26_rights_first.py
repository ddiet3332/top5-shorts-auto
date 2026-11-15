"""V26 must never turn a free preview or a provider description into rights approval."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v26_rights_first import (
    validate_candidates,triage,validate_private_rights_record,
    REQUIRED_RIGHTS,
)
CATALOG=ROOT/"sample/v26-licensed-ugc-candidates.json"


def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


class V26RigorousLicenseGate(unittest.TestCase):
    def test_official_catalog_six_unlicensed_distinct_sources(self):
        rows=validate_candidates(catalog())
        self.assertEqual(len(rows),6)
        self.assertEqual(len({x["id"] for x in rows}),6)
        self.assertTrue(all(x["rights_status"]=="NOT_CONTACTED" for x in rows))
        self.assertFalse(any(x["source_mp4_available"] for x in rows))

    def test_v25_baseline_score_not_fabricated_into_v26(self):
        r=triage(catalog())
        self.assertEqual(r["baseline_version"],"V25")
        self.assertEqual(r["baseline_score"],82)
        self.assertIsNone(r["final_V26_video_100_point_score"])
        self.assertEqual(r["rights_ready_for_full_visual_review"],0)
        self.assertFalse(r["new_source_video_rendered"])
        self.assertFalse(r["publication_approved"])
        self.assertTrue(all(row["human_comedy_score"] is None for row in r["candidates"]))

    def test_reject_duplicate_ids_and_arbitrary_provider_urls(self):
        c=catalog()
        c["candidates"][1]["id"]=c["candidates"][0]["id"]
        with self.assertRaisesRegex(ValueError,"match"):
            validate_candidates(c)
        c=catalog()
        c["candidates"][0]["url"]="https://fake-vbear-viral.example/paid-preview.mp4"
        with self.assertRaisesRegex(ValueError,"official"):
            validate_candidates(c)
        c=catalog()
        c["candidates"][0]["url"]="https://vbear.media/library/11111/a-fake-title"
        with self.assertRaisesRegex(ValueError,"must match"):
            validate_candidates(c)

    def test_cannot_leak_contract_text_to_public_github(self):
        c=catalog()
        c["candidates"][0]["full_license_email"]="private user@example.com"
        with self.assertRaisesRegex(ValueError,"contracts"):
            validate_candidates(c)

    def test_signed_flag_alone_cannot_unlock_clip(self):
        c=catalog()
        rows=c["candidates"]
        private={rows[0]["id"]:{"id":rows[0]["id"],"licensed":True}}
        r=triage(c,private)
        self.assertEqual(r["rights_ready_for_full_visual_review"],0)
        self.assertFalse(r["candidates"][0]["may_download_unwatermarked_master"])
        self.assertIn("ORIGINAL_MASTER_SHA256_MISSING",r["candidates"][0]["rights_gate_reasons"])

    def test_even_full_metadata_does_not_claim_publication(self):
        c=catalog()
        source=c["candidates"][0]
        record={"id":source["id"],
                **{flag:True for flag in REQUIRED_RIGHTS},
                "private_evidence_digest":"a"*64,
                "original_master_sha256":"b"*64,
                "reviewer_alias":"licensing-reviewer",
                "license_expires_on":"2030-12-31",
                "audio_use_allowed":False}
        self.assertEqual(validate_private_rights_record(record,source),[])
        r=triage(c,{source["id"]:record})
        # Actual footage has not been watched; provider text is no substitute.
        self.assertIn("ACTUAL_RAW_VIDEO_NOT_WATCHED",r["candidates"][0]["rights_gate_reasons"])
        self.assertFalse(r["publication_approved"])

    def test_third_party_audio_rights_remain_separate(self):
        c=catalog(); source=c["candidates"][0]
        record={"id":source["id"],
                **{flag:True for flag in REQUIRED_RIGHTS},
                "private_evidence_digest":"a"*64,
                "original_master_sha256":"b"*64,
                "reviewer_alias":"licensing-reviewer",
                "license_expires_on":"2030-12-31",
                "audio_use_allowed":True}
        issues=validate_private_rights_record(record,source)
        self.assertIn("RAW_AUDIO_NOT_CLEARED",issues)

    def test_publisher_preview_without_license_is_blocked(self):
        c=catalog()
        c["candidates"][0]["preview_downloaded"]=True
        with self.assertRaisesRegex(ValueError,"not legitimately"):
            validate_candidates(c)


if __name__=="__main__":
    unittest.main()
