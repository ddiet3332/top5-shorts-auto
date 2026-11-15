"""V25 user-required situation captions only, no narration or raw source audio."""
import json,sys,unittest
from tempfile import TemporaryDirectory
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from v25_original_audio_audit import inspect,run
from v25_qa import validate_selection
from top5 import create_subtitles,V16_SEGMENTS,DEFAULT_CAPTIONS

class V25CaptionOnly(unittest.TestCase):
    def test_v25_has_no_tts_or_narration(self):
        d=json.loads((ROOT/"sample/v25-render-script.json").read_text(encoding="utf-8"))
        self.assertTrue(d["no_narration"])
        self.assertTrue(d["no_tts"])
        self.assertFalse(d["allow_original_sound"])
        self.assertTrue(d["sfx_synthesized_only"])
        self.assertFalse(d["publication_approved"])
        self.assertEqual(len(d["phases"]),5)
        self.assertTrue(all(len(x)==2 for x in d["phases"].values()))

    def test_timeline_complete_and_real_cats_have_evidence(self):
        d=json.loads((ROOT/"sample/v25-situation-captions.json").read_text(encoding="utf-8"))
        cues=d["cues"]
        self.assertEqual(cues[0]["start_sec"],0)
        self.assertEqual(cues[-1]["end_sec"],30)
        for i in range(1,len(cues)):
            self.assertEqual(cues[i-1]["end_sec"],cues[i]["start_sec"])
        self.assertTrue(all(bool(c["evidence"]) for c in cues))
        self.assertEqual(d["target"]["speech_files_expected"],0)

    def test_same_five_unique_video_sources_are_preserved(self):
        d=json.loads((ROOT/"sample/v22-mixed-selection.json").read_text(encoding="utf-8"))
        self.assertEqual(len(validate_selection(d)),5)
        self.assertTrue(all(row["audio_approved"] is False for row in d))

    def test_caption_payoff_timing_uses_actual_moment_not_midpoint(self):
        d=json.loads((ROOT/"sample/v25-render-script.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(d["phase_offsets"]["rank5"],0.4)
        self.assertAlmostEqual(d["phase_offsets"]["rank4"],1.1)
        with TemporaryDirectory() as td:
            ass=Path(td)/"situational.ass"
            create_subtitles(ass,"고양이 상황 TOP5",d["captions"],
                caption_phases=d["phases"],
                caption_phase_offsets=d["phase_offsets"],
                segments=V16_SEGMENTS)
            content=ass.read_text(encoding="utf-8")
            self.assertIn("일단 들어가고 생각하자!",content)
            self.assertIn("점프 한 번! 다시 대기!",content)
            self.assertIn("저 틈, 그대로 날아간다!",content)
            # For rank5 2.0-6.0, 2.40 must be the payoff start.
            self.assertRegex(content,r"0:00:02[.]40.*일단 들어가고 생각하자!")
            # For rank4 6.0-11.0, 7.10 must be its payoff.
            self.assertRegex(content,r"0:00:07[.]10.*점프 한 번! 다시 대기!")

    def test_source_audio_absence_does_not_imply_reuse_permission(self):
        with TemporaryDirectory() as td:
            status=inspect(Path(td)/"missing.webm","wikimedia",
                          "File:Cat Jumpscare.webm","CC0")
            self.assertFalse(status["original_audio_used_in_v25"])
            self.assertFalse(status["editorial_audio_verified"])
            self.assertFalse(status["third_party_music_and_voices_cleared"])
            self.assertEqual(status["audio_tracks"],0)

if __name__=="__main__":
    unittest.main()
