"""Offline regression tests: GitHub automatic review index."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from publish_review_index import manifest_from_audit, write_index


class ReviewIndexTests(TestCase):
    def test_successful_run_records_artifact_and_review_flags(self):
        audit = {'raw_license_filtered_pool': 81, 'cat_relevance_pool': 9,
                 'candidates': [{'title': 'File:Cat.webm',
                                 'source_page': 'https://example.test',
                                 'license': 'CC BY 4.0',
                                 'moments': [{}, {}]}]}
        m = manifest_from_audit(audit, repo='a/b', run_id=123456, run_number=44,
                                run_attempt=1, result='success', event='push')
        self.assertEqual(m['artifact_name'], 'TOP5-shorts-review-44')
        self.assertEqual(m['candidate_count'], 1)
        self.assertEqual(m['preview_file_count'], 2)
        self.assertFalse(m['approved_for_publication'])
        with TemporaryDirectory() as d:
            self.assertTrue(write_index(m, Path(d)))
            saved = json.loads((Path(d)/'latest.json').read_text())
            self.assertEqual(saved['run_id'], 123456)
            self.assertTrue((Path(d)/'runs/123456.json').exists())

    def test_old_run_cannot_overwrite_new_run(self):
        with TemporaryDirectory() as d:
            newer = manifest_from_audit(None, repo='a/b', run_id=900,
                run_number=47, run_attempt=1, result='failure', event='push')
            older = manifest_from_audit(None, repo='a/b', run_id=800,
                run_number=46, run_attempt=2, result='success', event='push')
            self.assertTrue(write_index(newer, Path(d)))
            self.assertFalse(write_index(older, Path(d)))
            self.assertEqual(
                json.loads((Path(d)/'latest.json').read_text())['run_number'], 47)

    def test_no_audit_never_becomes_approved(self):
        m = manifest_from_audit(None, repo='a/b', run_id=8,
            run_number=8, run_attempt=1, result='failure', event='push')
        self.assertEqual(m['review_status'], 'WORKFLOW_ERROR_OR_MISSING_AUDIT')
        self.assertEqual(m['candidate_count'], 0)
        self.assertFalse(m['approved_for_publication'])
