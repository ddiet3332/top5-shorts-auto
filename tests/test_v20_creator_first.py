"""V20 creator-first source licensing is explicitly checked; never auto-approves."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from v20_creator_first import valid_metadata, audit


def fixture():
    original=[
       {"title":"File:Cat Jumpscare.webm",
        "source_page":"https://commons.wikimedia.org/wiki/File:Cat_Jumpscare.webm",
        "author":"Panini!","license":"CC0","license_url":"https://creativecommons.org/publicdomain/zero/1.0/",
        "source_claim":"Own work","size_bytes":14000000,
        "review_flags":[],"download_url":"https://upload.wikimedia.org/test.webm"},
       {"title":"File:Black and white cat growl and hiss.webm",
        "source_page":"https://commons.wikimedia.org/wiki/File:Black_and_white_cat_growl_and_hiss.webm",
        "author":"Abujoy","license":"CC BY 4.0","license_url":"https://creativecommons.org/licenses/by/4.0/",
        "source_claim":"Own work","size_bytes":11000000,
        "review_flags":[],"download_url":"https://upload.wikimedia.org/test2.webm"}
    ]
    candidates=[
       {"title":"File:Cat Jumpscare.webm",
        "page_url":"https://commons.wikimedia.org/wiki/File:Cat_Jumpscare.webm",
        "expected_author":"Panini!","expected_source":"Own work","expected_license":"CC0"},
       {"title":"File:Black and white cat growl and hiss.webm",
        "page_url":"https://commons.wikimedia.org/wiki/File:Black_and_white_cat_growl_and_hiss.webm",
        "expected_author":"Abujoy","expected_source":"Own work","expected_license":"CC BY 4.0"}
    ]
    return candidates,original


class TestCreatorFirst(unittest.TestCase):
    def test_exact_current_cc_licenses_allow_preview_only(self):
        requested,current=fixture()
        accepted,rejected=valid_metadata(current,requested)
        self.assertEqual(len(accepted),2)
        self.assertEqual(rejected,[])
        self.assertTrue(all(x["cat_category_evidence"] for x in accepted))

    def test_reposted_claim_is_not_accepted(self):
        req,src=fixture()
        src[0]["source_claim"]="https://www.youtube.com/watch?v=duplicate"
        accepted,rejected=valid_metadata(src,req)
        self.assertEqual(len(accepted),1)
        self.assertEqual(rejected[0]["reason"],"NO_CURRENT_OWN_WORK_METADATA")

    def test_author_mismatch_or_license_change_blocked(self):
        req,src=fixture()
        src[0]["author"]="Mysterious Reuploader"
        src[1]["license_url"]="https://creativecommons.org/licenses/by-sa/4.0/"
        accepted,rejected=valid_metadata(src,req)
        self.assertEqual(accepted,[])
        self.assertEqual({x["reason"] for x in rejected},
                         {"CREATOR_MISMATCH","CC_BY_LICENSE_CHANGED_OR_ABSENT"})

    def test_no_unofficial_source_page(self):
        req,src=fixture()
        req[0]["page_url"]="https://random-reupload.example.com/clip.webm"
        accepted,rejected=valid_metadata(src,req)
        self.assertEqual(len(accepted),1)
        self.assertEqual(rejected[0]["reason"],"SOURCE_PAGE_NOT_OFFICIAL")

    def test_license_audit_fails_without_video(self):
        req,src=fixture()
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,"No source passed"):
                audit(req,[],Path(tmp))
            self.assertTrue((Path(tmp)/"V20_CREATOR_LICENSE_AUDIT.json").exists())

    def test_repeated_curated_file_titles_rejected(self):
        req,src=fixture()
        with self.assertRaises(ValueError):
            valid_metadata(src,[req[0],req[0]])


if __name__=="__main__":
    unittest.main()
