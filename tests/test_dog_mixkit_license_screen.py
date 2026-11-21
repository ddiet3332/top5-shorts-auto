import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_mixkit_license_screen import screen_catalog


def catalog(sources):
    return {"schema_version":1,"scope":"research_only_commercial_license_screen",
            "official_license_reference":"https://mixkit.co/license/modal/videoFree/",
            "publication_approved":False,"sources":sources}


def entry(sid="MK-101230",classification="FREE"):
    return {"id":sid,"provider":"mixkit","title":"Girl Doing Tricks with Dog",
            "source_url":"https://mixkit.co/free-stock-video/girl-doing-tricks-with-dog-"+sid[3:]+"/",
            "rank_target":"rank2","action_family_hypothesis":"dog_tricks",
            "license_class":classification,
            "official_page_license_text":("Mixkit Stock Video Free License" if classification=="FREE"
                                          else "Mixkit Restricted License - 720p free version for personal use only"),
            "semantic_review":"UNVERIFIED","rights_status":"UNVERIFIED" if classification=="FREE"
             else "RESTRICTED_NONCOMMERCIAL",
            "original_download_verified":False,"publication_approved":False}


class MixkitLicenseGateTests(unittest.TestCase):
    def check(self,content):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"mixkit.json"
            p.write_text(json.dumps(content),encoding="utf-8")
            return screen_catalog(p)

    def test_official_free_vs_restricted(self):
        free=entry()
        restricted=entry("MK-36528","RESTRICTED")
        report=self.check(catalog([free,restricted]))
        self.assertEqual([x["id"] for x in report["free_license_page_candidates"]],["MK-101230"])
        self.assertEqual(report["commercially_blocked"][0]["id"],"MK-36528")
        self.assertEqual(report["preview_count"],0)
        self.assertEqual(report["free_license_page_candidates"][0]["rights_status"],"UNVERIFIED")
        self.assertFalse(report["publication_approved"])

    def test_untrusted_domain_and_wrong_id(self):
        bad=entry()
        bad["source_url"]="https://mixkit.co.evil.invalid/free-stock-video/foo-101230/"
        with self.assertRaises(ValueError):
            self.check(catalog([bad]))
        bad=entry()
        bad["source_url"]="https://mixkit.co/free-stock-video/foo-9999/"
        with self.assertRaises(ValueError):
            self.check(catalog([bad]))

    def test_cannot_preapprove_or_implicitly_clear_free_license(self):
        bad=entry()
        bad["publication_approved"]=True
        with self.assertRaises(ValueError):
            self.check(catalog([bad]))
        bad=entry()
        bad["rights_status"]="CLEARED"
        with self.assertRaises(ValueError):
            self.check(catalog([bad]))

    def test_unknown_license_blocked(self):
        bad=entry(classification="MYSTERY")
        report=self.check(catalog([bad]))
        self.assertEqual(report["free_license_page_candidates"],[])
        self.assertEqual(report["commercially_blocked"][0]["id"],"MK-101230")
        self.assertFalse(report["publication_approved"])


if __name__=="__main__":
    unittest.main()
