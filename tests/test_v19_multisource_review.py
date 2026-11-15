"""V19 mixed-source licensing and safe audition regression tests (offline)."""
import sys
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from v19_multisource_review import (
    validate_catalog, make_board, MIXKIT_RESTRICTED_EXAMPLES,
    ALLOWED_PEXELS_IDS
)

CATALOG=Path(__file__).resolve().parents[1]/"sample/v19-curated-external.json"


class V19SourceReviewTests(unittest.TestCase):
    def originals(self):
        return json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_exact_curated_pages_only_and_three_pexels(self):
        rows=validate_catalog(self.originals())
        self.assertEqual(len(rows),7)
        self.assertEqual({x['provider'] for x in rows},
                         {'pexels','mixkit','pixabay'})
        self.assertEqual(sum(x['audit_action']=='pexels_official_single_video_preview'
                             for x in rows),3)
        self.assertTrue(all(x['publication_approved'] is False for x in rows))
        self.assertTrue(all(x['actual_video_watched'] is False for x in rows))
        self.assertTrue(all(x['source_audio_approved'] is False for x in rows))

    def test_mixkit_restricted_free_download_is_not_commercial_approval(self):
        rows=self.originals()
        rows[-1]['provider']='mixkit'
        rows[-1]['id']='MK-6999'
        rows[-1]['page_url']='https://mixkit.co/free-stock-video/kitten-playing-with-ball-6999/'
        rows[-1]['license_label']='Mixkit Stock Video Free License'
        rows[-1]['license_url']='https://mixkit.co/license/modal/videoFree/'
        self.assertIn(rows[-1]['page_url'],MIXKIT_RESTRICTED_EXAMPLES)
        with self.assertRaisesRegex(ValueError,"MIXKIT_RESTRICTED_LICENSE"):
            validate_catalog(rows)

    def test_no_cross_provider_license(self):
        rows=self.originals()
        rows[0]['license_url']='https://pixabay.com/service/license-summary/'
        with self.assertRaises(ValueError):
            validate_catalog(rows)

    def test_no_mismatched_provider_page_id(self):
        rows=self.originals()
        rows[0]['id']='PX-999999'
        with self.assertRaisesRegex(ValueError,"ID"):
            validate_catalog(rows)

    def test_no_rights_approval_via_catalog(self):
        rows=self.originals()
        rows[0]['publication_approved']=True
        with self.assertRaises(ValueError):
            validate_catalog(rows)
        rows=self.originals()
        rows[0]['source_audio_approved']=True
        with self.assertRaises(ValueError):
            validate_catalog(rows)

    def test_unknown_video_download_attempt_blocked(self):
        rows=self.originals()
        rows[3]['audit_action']='pexels_official_single_video_preview'
        self.assertNotIn(rows[3]['id'],ALLOWED_PEXELS_IDS)
        with self.assertRaisesRegex(ValueError,"Only three"):
            validate_catalog(rows)

    def test_board_does_not_falsify_video_review(self):
        rows=validate_catalog(self.originals())
        with TemporaryDirectory() as td:
            report=make_board(rows,[],Path(td),audition_enabled=False)
            self.assertEqual(report['candidate_page_count'],7)
            self.assertEqual(report['actual_pexels_source_previews_created'],0)
            self.assertEqual(report['video_previews_created'],0)
            self.assertFalse(report['publication_approved'])
            self.assertTrue((Path(td)/'V19_PHONE_REVIEW.html').exists())
            self.assertTrue((Path(td)/'V19_REVIEW_QUEUE.csv').exists())

    def test_previews_are_only_previews_not_content_approval(self):
        rows=validate_catalog(self.originals())
        fake=[{"id":rows[0]['id'],
               "editorial_status":"VIDEO_READY_FOR_HUMAN_REVIEW",
               "windows":[{"source_time_sec":1.2,
                           "preview_file":"V19_PEXELS/preview_1.mp4"}]}]
        with TemporaryDirectory() as td:
            report=make_board(rows,fake,Path(td),audition_enabled=True)
            self.assertEqual(report['actual_pexels_source_previews_created'],1)
            self.assertEqual(report['video_previews_created'],1)
            self.assertFalse(report['candidates'][0]['actual_video_watched'])
            self.assertFalse(report['all_rights_approved'])
            self.assertFalse(report['publication_approved'])


if __name__ == '__main__':
    unittest.main()
