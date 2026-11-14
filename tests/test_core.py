import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from top5 import supported_license, clean_html, ass_timestamp, create_subtitles, DEFAULT_CAPTIONS, source_label, candidate_relevance, create_transition_sfx, voiceover_timeline, verify_editorial_selections, stage_geometry, render_segment, probe_dimensions, original_audio_available, make_approved_source_audio

class BasicTests(unittest.TestCase):
    def test_license_positive(self):
        self.assertEqual(supported_license('https://creativecommons.org/licenses/by/4.0/'), 'CC BY')
        self.assertEqual(supported_license('http://creativecommons.org/licenses/by/3.0'), 'CC BY')
        self.assertEqual(supported_license('https://creativecommons.org/publicdomain/zero/1.0/'), 'CC0')
    def test_license_negative(self):
        for x in ('https://creativecommons.org/licenses/by-sa/4.0/',
                  'https://creativecommons.org/licenses/by-nc/4.0/',
                  'https://creativecommons.org/licenses/by-nd/4.0/',
                  'https://example.org/by/4.0', ''):
            self.assertIsNone(supported_license(x))
    def test_html(self):
        self.assertEqual(clean_html('<a href="/">Kim</a> &amp; Jane'), 'Kim & Jane')
    def test_source_names(self):
        self.assertEqual(source_label("File:Cat playing in Taiwan.webm", {"File:Cat playing in Taiwan.webm": "대만 고양이"}), "대만 고양이")
        self.assertTrue(source_label("File:Cat playing in Taiwan.webm").startswith("Cat playing"))

    def test_v3_relevance(self):
        self.assertEqual(candidate_relevance("Magician's Cat (2012).webm"), -100)
        self.assertGreater(candidate_relevance("Funny kitten jumping and playing.webm"), 0)
        self.assertEqual(candidate_relevance("Kenan Thompson playing every character on All That.webm"), -100)
        self.assertEqual(candidate_relevance("Fractal and DogPlayingTetris during CTWC.webm"), -100)
        self.assertEqual(candidate_relevance("This is what plays in my mind - Victorious.webm"), -100)
        self.assertGreaterEqual(candidate_relevance("Cat in a Bag.webm"), 0)

    def test_v3_audio_and_timeline(self):
        import tempfile
        import wave
        import json
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            create_transition_sfx(out/'effects.wav',seconds=30)
            with wave.open(str(out/'effects.wav')) as audio:
                self.assertEqual(audio.getframerate(),48000)
                self.assertEqual(audio.getnframes(),30*48000)
            lines=voiceover_timeline(out,DEFAULT_CAPTIONS)
            self.assertEqual(len(lines),7)
            self.assertEqual(lines[-1]['end'],30)
            self.assertTrue((out/'NARRATION_REQUIRED.md').exists())

    def test_editorial_selection_validation(self):
        rows=[{'title':f'File:Clip_{i:02}.webm','start_sec':3,'focus_x':0.5} for i in range(5)]
        self.assertEqual(len(verify_editorial_selections(rows)),5)
        with self.assertRaises(ValueError):
            verify_editorial_selections(rows[:4])
        with self.assertRaises(ValueError):
            verify_editorial_selections(rows[:4]+[rows[0]])
        with self.assertRaises(ValueError):
            verify_editorial_selections(rows[:4]+[{'title':'File:new.webm','focus_x':1.1}])

    def test_v5_stage_geometry(self):
        frame=stage_geometry(1080,1920)
        self.assertEqual(frame['x']%2,0)
        self.assertEqual(frame['height']%2,0)
        self.assertGreater(frame['x'],200)
        self.assertLessEqual(frame['x']+frame['width'],1080)
        self.assertLessEqual(frame['y']+frame['height'],1920)
        with self.assertRaises(ValueError):
            stage_geometry(1080,1080)

    def test_v5_fit_wide_and_portrait_sources_without_cropping(self):
        import subprocess
        import tempfile
        # Synthetic full-frame yellow clip allows exact checks of black matte
        # and preserved source aspect without needing real CC assets.
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for source_w,source_h in [(320,180),(180,320)]:
                src=d/f'{source_w}x{source_h}.mp4'
                out=d/f'{source_w}x{source_h}_out.mp4'
                subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                                '-f','lavfi','-i',f'color=c=yellow:s={source_w}x{source_h}:d=1.2:r=24',
                                '-c:v','libx264','-pix_fmt','yuv420p',str(src)],check=True,timeout=30)
                render_segment(src,out,0,1,width=360,height=640,fps=24)
                self.assertEqual(probe_dimensions(out),(360,640))
                frame=subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error',
                                               '-i',str(out),'-frames:v','1',
                                               '-vf','format=gray','-f','rawvideo','-'],timeout=35)
                self.assertEqual(len(frame),360*640)
                self.assertLess(frame[50*360+10],20)
                self.assertLess(frame[610*360+200],20)
                coords=[(x,y) for y in range(80,560,2) for x in range(65,356,2) if frame[y*360+x]>90]
                self.assertTrue(coords)
                xs=[p[0] for p in coords];ys=[p[1] for p in coords]
                aspect=(max(xs)-min(xs)+2)/(max(ys)-min(ys)+2)
                self.assertAlmostEqual(aspect,source_w/source_h,delta=0.09)

    def test_v6_caption_is_65_percent_and_wider_video(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'caption.ass'
            create_subtitles(file,'고양이 TOP5',DEFAULT_CAPTIONS)
            contents=file.read_text(encoding='utf-8')
            self.assertIn(r'\pos(540,1248)',contents)   # 65% of 1920
            geometry=stage_geometry(1080,1920)
            self.assertGreaterEqual(geometry['width'],850)
            self.assertGreaterEqual(geometry['x'],195)

    def test_v6_original_audio_requires_explicit_approval(self):
        import subprocess
        import tempfile
        import wave
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            src=d/'sample.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                '-f','lavfi','-i','color=c=blue:s=320x180:d=2:r=24',
                '-f','lavfi','-i','sine=frequency=440:duration=2:sample_rate=48000',
                '-shortest','-c:v','libx264','-c:a','aac',str(src)],
                check=True,timeout=35)
            self.assertTrue(original_audio_available(src))
            silent=d/'silent.wav'
            played=d/'played.wav'
            self.assertEqual(make_approved_source_audio(
                {'local_path':str(src),'audio_approved':False},0.0,1,silent),
                'silent_no_approved_audio')
            self.assertEqual(make_approved_source_audio(
                {'local_path':str(src),'audio_approved':True},0.0,1,played),
                'original_audio_rights_confirmed')
            with wave.open(str(silent)) as w:
                data_s=w.readframes(w.getnframes())
                self.assertEqual(w.getnframes(),48000)
            with wave.open(str(played)) as w:
                data_p=w.readframes(w.getnframes())
                self.assertEqual(w.getnframes(),48000)
            self.assertEqual(max(data_s),0)
            self.assertNotEqual(data_p,data_s)

    def test_ass(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.ass'
            create_subtitles(p,'재미있는 TOP5',DEFAULT_CAPTIONS)
            content=p.read_text(encoding='utf-8')
            self.assertEqual(content.count('Dialogue:'),1+1+7*11)
            self.assertIn('0:00:30.00',content)
            self.assertIn('ActiveName',content)
            self.assertIn('RankName',content)
if __name__=='__main__': unittest.main()
