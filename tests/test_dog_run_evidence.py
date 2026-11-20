"""Failure paths must not corrupt an earlier verified run."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import dog_run_evidence as evidence


class DogRunEvidenceTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name)
        self.output, self.review = path/"output",path/"review"
        self.output.mkdir()

    def finalize(self, run=100, attempt=1, install="success", render="success"):
        archive, report = evidence.finalize(self.output,self.review,run,attempt,"abc",install,render)
        evidence.record(archive,self.review)
        return report

    def pointer(self, name):
        return evidence.read_json(self.review/name/evidence.MANIFEST)

    def prepare(self):
        video = self.output/evidence.VIDEO
        video.write_bytes(b"video fixture")
        originals = self.output/"originals"
        originals.mkdir()
        rows = []
        for i in range(1,7):
            local = originals/f"PX-{i}.mp4"
            local.write_bytes(bytes([i]))
            rows.append({"source_page":f"https://www.pexels.com/video/dog-{i}/",
                         "sha256":evidence.digest(local),"action_family":str(i)})
        evidence.write_json(self.output/evidence.INVENTORY,{"status":"SELECTED","selected":rows[:5]})
        evidence.write_json(self.output/evidence.HOOK,{
            **rows[-1],"independent_hook":True,"rendered_video_sha256":evidence.digest(video)})
        return video

    def test_install_cancelled_and_no_mp4_never_invoke_media_tools(self):
        with patch.object(evidence,"verify_streams") as verify, patch.object(evidence,"contact_sheet") as sheet:
            attempt = self.finalize(install="cancelled",render="skipped")
            self.assertEqual(attempt["reason"],"INSTALL_CANCELLED")
            self.assertEqual(attempt["contact_sheet"],"NOT_RUN_NO_MP4")
            self.assertEqual(self.finalize(run=101)["reason"],"RENDER_DID_NOT_CREATE_MP4")
            verify.assert_not_called()
            sheet.assert_not_called()
        self.assertFalse((self.review/"latest_success").exists())

    def test_shortage_retains_candidate_inventory(self):
        candidates = {"status":"SOURCE_SHORTAGE","rejections":[{"reason":"NETWORK_UNAVAILABLE"}]}
        evidence.write_json(self.output/evidence.INVENTORY,candidates)
        self.assertEqual(self.finalize(render="failure")["status"],"SOURCE_SHORTAGE")
        saved = self.review/"runs/100/attempt-1"/evidence.INVENTORY
        self.assertEqual(evidence.read_json(saved),candidates)

    def test_missing_ffmpeg_and_wrong_hash_reject_output(self):
        self.prepare()
        with patch.object(evidence.shutil,"which",return_value=None):
            self.assertEqual(self.finalize()["reason"],"FFMPEG_OR_FFPROBE_MISSING")
        (self.output/"originals/PX-2.mp4").write_bytes(b"changed")
        with patch.object(evidence.shutil,"which",return_value="/bin/ffmpeg"):
            self.assertEqual(self.finalize(run=101)["reason"],"SOURCE_HASH_MISMATCH")

    def test_success_pointer_survives_later_failure_and_old_rerun(self):
        video = self.prepare()
        with patch.object(evidence.shutil,"which",return_value="/bin/ffmpeg"), \
             patch.object(evidence,"verify_streams") as verify, patch.object(evidence,"contact_sheet") as sheet:
            success = self.finalize()
            verify.assert_called_once_with(video)
            sheet.assert_called_once()
        video.unlink()
        self.finalize(run=101,install="cancelled",render="skipped")
        self.finalize(run=99,attempt=3)
        self.assertEqual(self.pointer("latest_success")["video_sha256"],success["video_sha256"])
        self.assertEqual(self.pointer("latest_attempt")["run_id"],101)
        self.assertTrue((self.review/"runs/100/attempt-1"/evidence.MANIFEST).is_file())
        self.assertTrue((self.review/"runs/101/attempt-1"/evidence.MANIFEST).is_file())


if __name__ == "__main__":
    unittest.main()
