import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from top5_public_video_discovery import commons,archive,discover,license_flag
class PublicDiscoveryTests(unittest.TestCase):
 def test_license_not_auto_approved(self):
  self.assertEqual(license_flag("CC BY-SA 4.0"),"LICENSE_CANDIDATE_REVIEW_REQUIRED")
  self.assertEqual(license_flag("All rights reserved"),"LICENSE_UNKNOWN_OR_RESTRICTED")
 def test_commons_video_only(self):
  def fetch(url):
   return {"query":{"pages":{"1":{"pageid":1,"title":"File:Clip.webm","imageinfo":[{"url":"https://upload.wikimedia.org/clip.webm","mime":"video/webm","extmetadata":{"LicenseShortName":{"value":"CC BY 4.0"}}}]},"2":{"pageid":2,"title":"File:Photo.jpg","imageinfo":[{"url":"https://upload.wikimedia.org/photo.jpg"}]}}}}
  rows=commons("dance",fetch);self.assertEqual(len(rows),1);self.assertFalse(rows[0]["rights_verified"])
 def test_archive_requires_license_review(self):
  def fetch(url):
   if "advancedsearch" in url:return {"response":{"docs":[{"identifier":"demo","title":"Demo"}]}}
   return {"metadata":{},"files":[{"name":"clip.mp4","source":"original"}]}
  rows=archive("dance",fetch);self.assertEqual(len(rows),1);self.assertEqual(rows[0]["license_gate"],"LICENSE_UNKNOWN_OR_RESTRICTED")
 def test_discovery_errors_not_fabricated(self):
  def broken(url):raise TimeoutError()
  result=discover(["dance"],broken);self.assertEqual(result["candidate_count"],0);self.assertEqual(len(result["errors"]),2)
if __name__=="__main__":unittest.main()
