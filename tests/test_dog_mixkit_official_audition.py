import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from dog_mixkit_official_audition import (select_explicit_download_link,
                                          audit_mixkit)


def free_html(anchor=""):
    return "<html>Mixkit Stock Video Free License Download Free Video"+anchor+"</html>"


def sample_catalog(path):
    d={"schema_version":1,
       "scope":"research_only_commercial_license_screen",
       "official_license_reference":"https://mixkit.co/license/modal/videoFree/",
       "publication_approved":False,
       "sources":[{"id":"MK-101230","provider":"mixkit","title":"Dog tricks",
                   "source_url":"https://mixkit.co/free-stock-video/girl-doing-tricks-with-dog-101230/",
                   "rank_target":"rank2","license_class":"FREE",
                   "official_page_license_text":"Mixkit Stock Video Free License",
                   "semantic_review":"UNVERIFIED","rights_status":"UNVERIFIED",
                   "original_download_verified":False,"publication_approved":False},
                  {"id":"MK-36528","provider":"mixkit","title":"Restricted man dog",
                   "source_url":"https://mixkit.co/free-stock-video/man-teaching-tricks-to-his-dog-36528/",
                   "rank_target":"rank2","license_class":"RESTRICTED",
                   "official_page_license_text":"Mixkit Restricted License - 720p free version for personal use only",
                   "semantic_review":"UNVERIFIED","rights_status":"RESTRICTED_NONCOMMERCIAL",
                   "original_download_verified":False,"publication_approved":False}]}
    path.write_text(json.dumps(d))
    return path


class MixkitOfficialAuditionTests(unittest.TestCase):
    def test_explicit_official_download_anchor(self):
        page="https://mixkit.co/free-stock-video/girl-doing-tricks-with-dog-101230/"
        html=free_html('<a download href="https://assets.mixkit.co/videos/download/dog-101230.mp4">Download Free Video</a>')
        self.assertEqual(select_explicit_download_link(page,html),
                         "https://assets.mixkit.co/videos/download/dog-101230.mp4")
        for bad in ('https://evil.invalid/dog-101230.mp4',
                    'https://assets.mixkit.co/videos/preview/dog-101230.mp4',
                    'https://assets.mixkit.co/video-101230.html'):
            with self.subTest(bad=bad):
                self.assertIsNone(select_explicit_download_link(
                    page,free_html('<a download href="'+bad+'">Download Free Video</a>')))

    def test_free_requires_static_official_link_else_browser_action(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);catalog=sample_catalog(root/"manifest.json")
            calls=[]
            def html(url):
                calls.append(url)
                return free_html("<button>Download Free Video</button>")
            r=audit_mixkit(catalog,root/"output",reader=html,
                           downloader=lambda *_:self.fail("No static media link"))
            self.assertEqual(r["status"],"NO_PREVIEW")
            self.assertEqual(r["candidates"][0]["status"],"OFFICIAL_BROWSER_DOWNLOAD_REQUIRED")
            self.assertEqual(len(calls),1)
            self.assertEqual(r["restricted_ids_blocked"],["MK-36528"])
            self.assertFalse(r["publication_approved"])

    def test_public_page_mismatch_reports_actionable_safe_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=sample_catalog(root/"manifest.json")
            def fail(_):
                raise ValueError("MIXKIT_OFFICIAL_PAGE_REDIRECT")
            r=audit_mixkit(manifest,root/"out",reader=fail)
            self.assertEqual(r["candidates"][0]["failure_code"],
                             "MIXKIT_OFFICIAL_PAGE_REDIRECT")
            self.assertEqual(r["status"],"NO_PREVIEW")
            self.assertFalse(r["publication_approved"])

    def test_download_one_explicit_link_with_review_only_and_delete_raw_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);catalog=sample_catalog(root/"manifest.json")
            media="https://assets.mixkit.co/videos/download/dog-101230.mp4"
            def page(_):
                return free_html(f'<a download href="{media}">Download Free Video</a>')
            def save(url,path):
                self.assertEqual(url,media)
                path.write_bytes(b"original"*1000)
            def preview(src,start,target):
                target.write_bytes(b"clip"*600)
            def image(src,pos,target):
                target.write_bytes(b"jpg")
            r=audit_mixkit(catalog,root/"out",reader=page,downloader=save,
                           probe=lambda _p:11.0,previewer=preview,image_maker=image)
            self.assertEqual(r["status"],"PREVIEW_READY")
            self.assertEqual(r["candidates"][0]["status"],"PREVIEW_READY_REVIEW_REQUIRED")
            self.assertFalse(r["publication_approved"])
            self.assertFalse((root/"out"/"MK-101230_temp_original.mp4").exists())
            self.assertTrue((root/"out"/"MK-101230_preview.mp4").exists())


if __name__=="__main__":
    unittest.main()
