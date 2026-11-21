"""V48 actual-source licence gate: independent hook is a sixth copyrighted clip."""
from __future__ import annotations
import hashlib,json,sys,tempfile,unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_all_source_license_audit import audit,collect_visual_sources

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False),encoding="utf-8")

class AllVisualSourceRightsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.video=self.root/"TOP5_AUTO_V29_REVIEW_1080x1920.mp4"
        self.video.write_bytes(b"real-artifact-identity-placeholder")
        self.hash=hashlib.sha256(self.video.read_bytes()).hexdigest()
        self.rank=[{"rank":5-i,"sha256":f"{i+1:064x}",
                     "source_page":f"https://example.org/footage/{i+1}",
                     "rights_verified":False,"publication_approved":False}
                    for i in range(5)]
        write(self.root/"SELECTED_SOURCE_PROVENANCE.json",{
            "selected":self.rank,"rights_verified":False,"publication_approved":False})
        self.hook={"status":"HOOK_RENDER_VERIFIED","independent_hook":True,
            "hook_mode":"independent_source","sha256":f"{6:064x}",
            "source_page":"https://example.org/footage/hook",
            "rendered_video_sha256":self.hash,
            "rights_verified":False,"publication_approved":False}
        write(self.root/"INDEPENDENT_HOOK_AUDIT.json",self.hook)
        self.catalog=self.root/"obs.json"
        self.samples=[{"sha256":row["sha256"],"source_page":row["source_page"],
            "creator":f"Creator {i}","license":"CC BY 4.0",
            "license_url":"https://creativecommons.org/licenses/by/4.0/",
            "attribution_required":True,"share_alike_review_required":False,
            "source_page_license_observed":True,
            "owner_authorization_independently_verified":False,
            "third_party_rights_verified":False,
            "youtube_reused_content_verified":False,
            "publication_approved":False}
            for i,row in enumerate([*self.rank,self.hook])]
        write(self.catalog,{"sources":self.samples})

    def test_sixth_hook_included_and_credited(self):
        x=audit(self.root,self.catalog)
        self.assertEqual(x["unique_visual_source_count"],6)
        self.assertEqual(x["source_page_metadata_observed_count"],6)
        self.assertTrue(x["independent_hook_included"])
        self.assertFalse(x["publication_approved"])
        self.assertFalse(x["source_rights_independently_verified"])
        draft=(self.root/"TOP5_SOURCE_CREDITS_COPY_DRAFT_KO.md").read_text()
        self.assertIn("오프닝(0~2초)",draft)
        self.assertIn("Creator 5",draft)
        self.assertEqual(draft.count("라이선스:"),6)

    def test_hook_rank_reuse_has_five_unique_not_six(self):
        self.hook.update(hook_mode="nonoverlapping_rank_source",
                         independent_hook=False,sha256=self.rank[0]["sha256"],
                         source_page=self.rank[0]["source_page"])
        write(self.root/"INDEPENDENT_HOOK_AUDIT.json",self.hook)
        x=audit(self.root,self.catalog)
        self.assertEqual(x["unique_visual_source_count"],5)
        self.assertFalse(x["independent_hook_included"])

    def test_unknown_hook_has_pending_rights_not_fake_clearance(self):
        self.samples.pop()
        write(self.catalog,{"sources":self.samples})
        x=audit(self.root,self.catalog)
        self.assertEqual(x["unobserved_source_roles"],["hook_0_2sec"])
        self.assertFalse(x["publication_approved"])
        draft=(self.root/"TOP5_SOURCE_CREDITS_COPY_DRAFT_KO.md").read_text()
        self.assertIn("출처 메타데이터 미확인",draft)

    def test_source_same_sha_but_wrong_url_not_matched(self):
        self.samples[0]["source_page"]="https://attacker.invalid/fake"
        write(self.catalog,{"sources":self.samples})
        x=audit(self.root,self.catalog)
        self.assertIn("rank_5",x["unobserved_source_roles"])

    def test_hook_metadata_cannot_be_from_different_mp4(self):
        self.hook["rendered_video_sha256"]="0"*64
        write(self.root/"INDEPENDENT_HOOK_AUDIT.json",self.hook)
        with self.assertRaisesRegex(ValueError,"HOOK_FOR_DIFFERENT_MP4"):
            collect_visual_sources(self.root)

    def test_share_alike_flag_requires_review_and_does_not_approve(self):
        self.samples[3]["license"]="CC BY-SA 4.0"
        self.samples[3]["share_alike_review_required"]=True
        write(self.catalog,{"sources":self.samples})
        x=audit(self.root,self.catalog)
        self.assertEqual(x["share_alike_legal_review_roles"],["rank_2"])
        self.assertFalse(x["youtube_reused_content_monetization_verified"])

    def test_all_five_other_topic_sources_get_provisional_metadata_not_false_licence_clearance(self):
        # V48 real nature run #44920949507 had 0/5 catalogue observations,
        # but V37 already contains author/licence *provider claims* for 5 ranks.
        v37=["# Publication gates"]
        for i,row in enumerate(self.rank):
            v37.extend([f"## {row['rank']}위: 자연 장면",
                f"- Source: {row['source_page']}",
                f"- Credited author: Metadata Creator {i}",
                "- Source licence: CC BY 4.0",
                "- Licence URL: https://creativecommons.org/licenses/by/4.0/",
                "- Rights not independently verified.",""])
        (self.root/"V37_ATTRIBUTION_AND_PUBLISH_GATES.md").write_text("\n".join(v37))
        write(self.catalog,{"sources":[]})
        result=audit(self.root,self.catalog)
        self.assertEqual(result["source_page_metadata_observed_count"],0)
        self.assertEqual(result["upstream_provider_metadata_unverified_count"],5)
        self.assertEqual(result["unobserved_source_roles"],
                         ["rank_5","rank_4","rank_3","rank_2","rank_1","hook_0_2sec"])
        self.assertFalse(result["publication_approved"])
        self.assertIn("Metadata Creator 0",
            (self.root/"TOP5_SOURCE_CREDITS_COPY_DRAFT_KO.md").read_text())
        self.assertIn("미검증",
            (self.root/"TOP5_SOURCE_CREDITS_COPY_DRAFT_KO.md").read_text())

    def test_independent_hook_gets_provisional_credit_from_existing_source_credits(self):
        (self.root/"SOURCE_CREDITS_REVIEW.md").write_text(
            "## 시작 훅\n"
            "- 원본 · https://example.org/footage/hook\n"
            "- 제작자 · Trougnouf\n"
            "- 표시 라이선스 · CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)\n")
        write(self.catalog,{"sources":[]})
        result=audit(self.root,self.catalog)
        self.assertEqual(result["upstream_provider_metadata_unverified_count"],1)
        hook=result["items"][-1]
        self.assertEqual(hook["role"],"hook_0_2sec")
        self.assertEqual(hook["creator"],"Trougnouf")
        self.assertEqual(hook["licence_data_status"],"UPSTREAM_METADATA_UNVERIFIED")
        self.assertFalse(hook["publication_approved"])

    def test_missing_hook_is_rejected_not_five_rights_approved(self):
        (self.root/"INDEPENDENT_HOOK_AUDIT.json").unlink()
        with self.assertRaises(FileNotFoundError):
            audit(self.root,self.catalog)

if __name__=="__main__":
    unittest.main()
