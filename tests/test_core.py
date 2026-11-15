import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from v8_moments import window_candidates
from v12_sources import allowed_page, validate_catalog, parse_pexels_results, make_report
from v12_pexels_audition import official_video_id
from v12_mixed_draft import validate_mixed_selection
from v17_discovery import sufficient_resolution, is_external_reupload, action_group, editorial_priority
from v11_candidate_review import validate_titles
from top5 import supported_license, clean_html, ass_timestamp, create_subtitles, DEFAULT_CAPTIONS, source_label, candidate_relevance, create_transition_sfx, voiceover_timeline, verify_editorial_selections, stage_geometry, render_segment, probe_dimensions, original_audio_available, make_approved_source_audio

class BasicTests(unittest.TestCase):
    def test_license_positive(self):
        self.assertEqual(supported_license('https://creativecommons.org/licenses/by/4.0/'), 'CC BY')
        self.assertEqual(supported_license('http://creativecommons.org/licenses/by/3.0'), 'CC BY')
        self.assertEqual(supported_license('https://creativecommons.org/publicdomain/zero/1.0/'), 'CC0')
        self.assertEqual(supported_license('http://creativecommons.org/publicdomain/zero/1.0/deed.en'), 'CC0')
        self.assertIsNone(supported_license('http://creativecommons.org/publicdomain/zero/1.0/deed.en/fake'))
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
        self.assertEqual(frame['x'],0)
        self.assertEqual(frame['width'],1080)
        self.assertGreater(frame['height'],1300)
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
                coords=[(x,y) for y in range(70,570,2) for x in range(0,360,2) if frame[y*360+x]>80]
                self.assertTrue(coords)
                xs=[p[0] for p in coords];ys=[p[1] for p in coords]
                aspect=(max(xs)-min(xs)+2)/(max(ys)-min(ys)+2)
                self.assertAlmostEqual(aspect,source_w/source_h,delta=0.09)
                if source_w>source_h:
                    self.assertGreater(max(xs)-min(xs),345)

    def test_v6_caption_is_65_percent_and_wider_video(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'caption.ass'
            create_subtitles(file,'고양이 TOP5',DEFAULT_CAPTIONS)
            contents=file.read_text(encoding='utf-8')
            self.assertIn(r'\pos(540,1248)',contents)   # 65% of 1920
            geometry=stage_geometry(1080,1920)
            self.assertGreaterEqual(geometry['width'],850)
            self.assertEqual(geometry['x'],0)

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

    def test_v8_action_windows_are_editorial_candidates(self):
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'v8_moving.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                '-f','lavfi','-i','testsrc2=s=192x108:r=12:d=12',
                '-c:v','libx264','-preset','ultrafast',str(p)],
                check=True,timeout=40)
            windows=window_candidates(p,12.0)
            self.assertGreaterEqual(len(windows),1)
            self.assertLessEqual(len(windows),3)
            self.assertTrue(all(0 <= c['start'] <= 7.0 for c in windows))
            self.assertTrue(all(c['motion']>=0 for c in windows))
            self.assertTrue(all(c.get('algorithm')!='humor_ai' for c in windows))

    def test_v11_candidate_audition_requires_distinct_commons_titles(self):
        names=["File:Sammy springt.webm", "File:Moomin1.webm"]
        self.assertEqual(validate_titles(names),names)
        with self.assertRaises(ValueError):
            validate_titles(names + ["File:MOOMIN1.webm"])
        with self.assertRaises(ValueError):
            validate_titles(["https://www.youtube.com/watch?v=dummy"])
        with self.assertRaises(ValueError):
            validate_titles([])

    def test_v11_reaction_audio_changes_only_when_cue_set(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'base.wav'
            b=Path(d)/'cue.wav'
            create_transition_sfx(a,seconds=6)
            create_transition_sfx(b,seconds=6,reactions=[(4.7,'boing')])
            self.assertNotEqual(a.read_bytes(),b.read_bytes())
            import wave
            with wave.open(str(b)) as w:
                self.assertEqual(w.getnframes(),6*48000)
                self.assertEqual(w.getnchannels(),2)

    def test_v12_source_page_licensing_and_domains(self):
        sample={'id':'PX-1','provider':'pexels','title':'Example cat video',
                'page_url':'https://www.pexels.com/video/example-cat-1234/',
                'license_url':'https://www.pexels.com/license/',
                'license_label':'Pexels License','creator':'Example',
                'action_description':'cat jumps','review_target':'confirm jump'}
        self.assertTrue(allowed_page(sample))
        items=validate_catalog([sample])
        self.assertFalse(items[0]['publication_approved'])
        self.assertFalse(items[0]['actual_video_watched'])
        self.assertFalse(items[0]['source_audio_approved'])
        bad=dict(sample,page_url='https://evil.pexels.com/video/example-cat-1234/')
        self.assertFalse(allowed_page(bad))
        with self.assertRaises(ValueError):
            validate_catalog([bad])
        with self.assertRaises(ValueError):
            validate_catalog([sample,sample])
        restricted=dict(sample,provider='mixkit',
                        page_url='https://mixkit.co/free-stock-video/example-1234/',
                        license_label='Mixkit Stock Video Restricted License',
                        license_url='https://mixkit.co/license/modal/videoRestricted/')
        self.assertFalse(allowed_page(restricted))

    def test_v12_optional_pexels_search_metadata_never_approved(self):
        sample={'videos':[{'id':1234,'duration':10,
                           'url':'https://www.pexels.com/video/example-cat-1234/',
                           'user':{'name':'Contributor'}},
                          {'id':10,'duration':2,
                           'url':'https://www.pexels.com/video/short-cat-10/'},
                          {'id':23,'duration':7,
                           'url':'https://not-pexels.example/video/cat-23/'}]}
        out=parse_pexels_results(sample)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['id'],'PEXELS-API-1234')
        self.assertFalse(out[0]['publication_approved'])

    def test_v12_mobile_board_no_video_reuse_claims(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            catalog=validate_catalog([{
                'id':'PB-2','provider':'pixabay','title':'Cat jumping',
                'page_url':'https://pixabay.com/videos/cat-jumping-123/',
                'creator':'Creator','license_url':'https://pixabay.com/service/license-summary/',
                'license_label':'Pixabay Content License',
                'action_description':'Jumping cat','review_target':'confirm joke'}])
            make_report(catalog,d,'NOT_CONFIGURED_NEW_KEYS_PAUSED')
            self.assertTrue((Path(d)/'V12_MOBILE_REVIEW.html').exists())
            report=(Path(d)/'V12_SOURCE_REPORT.json').read_text(encoding='utf-8')
            self.assertIn('NOT_APPROVED',report)
            self.assertIn('false',report)

    def test_v12_real_video_download_allowlist(self):
        item={'id':'PX-5495527','provider':'pexels',
              'page_url':'https://www.pexels.com/video/a-cat-jumping-in-the-box-5495527/',
              'license_url':'https://www.pexels.com/license/',
              'license_label':'Pexels License'}
        self.assertEqual(official_video_id(item),5495527)
        bad=dict(item,page_url='https://evil.pexels.com/video/example-5495527/')
        with self.assertRaises(ValueError):
            official_video_id(bad)
        bad=dict(item,provider='mixkit')
        with self.assertRaises(ValueError):
            official_video_id(bad)

    def test_v12_mixed_rank_list_never_approves_unreviewed_audio(self):
        catalog=[{'id':'PX-23','provider':'pexels',
                  'page_url':'https://www.pexels.com/video/a-cat-23/',
                  'license_url':'https://www.pexels.com/license/',
                  'license_label':'Pexels License'}]
        rows=[{'provider':'pexels','id':'PX-23','start_sec':0,
               'display_name':'고양이'},
              *[{'provider':'wikimedia','title':f'File:Cat_{i}.webm',
                'start_sec':1,'display_name':'고양이'} for i in range(4)]]
        self.assertEqual(len(validate_mixed_selection(rows,catalog)),5)
        with self.assertRaises(ValueError):
            validate_mixed_selection(rows[:4],catalog)
        with self.assertRaises(ValueError):
            validate_mixed_selection(rows[:4]+[rows[0]],catalog)
        audio=[dict(x) for x in rows]
        audio[0]['audio_approved']=True
        with self.assertRaises(ValueError):
            validate_mixed_selection(audio,catalog)
        bad=[dict(x) for x in rows]
        bad[0]['id']='PX-999'
        with self.assertRaises(ValueError):
            validate_mixed_selection(bad,catalog)

    def test_v14_setup_payoff_caption_timing_and_fixed_65pct(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'v14.ass'
            phrases={'rank5':['면봉을 보여줬더니…','갑자기 점프!'],
                     'rank4':['건반을 밟고','훌쩍 사라짐!']}
            create_subtitles(target,'고양이 돌발행동 TOP5',DEFAULT_CAPTIONS,
                             caption_phases=phrases)
            data=target.read_text(encoding='utf-8')
            self.assertIn('면봉을 보여줬더니',data)
            self.assertIn('갑자기 점프!',data)
            self.assertIn(r'\pos(540,1248)',data)
            self.assertEqual(data.count('Dialogue:'),1+1+7*11+2)
            self.assertIn('0:00:04.45',data)
            with self.assertRaises(ValueError):
                create_subtitles(target,'제목',DEFAULT_CAPTIONS,
                                 caption_phases={'rank3':['단 하나']})

    def test_v15_duration_redistribution_and_transition_synchronization(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            from top5 import V15_SEGMENTS
            self.assertEqual(sum(duration for _,duration in V15_SEGMENTS),30)
            self.assertEqual(dict(V15_SEGMENTS)['rank3'],3)
            self.assertEqual(dict(V15_SEGMENTS)['rank2'],6)
            self.assertEqual(dict(V15_SEGMENTS)['rank1'],6)
            ass=root/'v15.ass'
            phases={'rank3':['달려오는 중','앗 가까워졌어!'],
                    'rank2':['연못 앞에','바로 점프!']}
            create_subtitles(ass,'돌발행동 TOP5',DEFAULT_CAPTIONS,
                             caption_phases=phases,segments=V15_SEGMENTS)
            content=ass.read_text(encoding='utf-8')
            self.assertIn('0:00:12.00,0:00:15.00,Active',content)
            self.assertIn('0:00:15.00,0:00:21.00,Active',content)
            self.assertIn('0:00:21.00,0:00:27.00,Active',content)
            self.assertIn('pos(540,1248)',content)
            marks=[0.04,2,7,12,15,21,27]
            sfx=root/'custom.wav'
            create_transition_sfx(sfx,seconds=30,transitions=marks)
            import wave
            with wave.open(str(sfx)) as wav:
                self.assertEqual(wav.getnframes(),1440000)
            with self.assertRaises(ValueError):
                create_transition_sfx(root/'invalid.wav',transitions=[31])

    def test_v16_two_cuts_dynamic_timecodes(self):
        import tempfile
        from top5 import V16_SEGMENTS
        self.assertEqual(sum(d for _,d in V16_SEGMENTS),30)
        self.assertEqual(dict(V16_SEGMENTS)['rank5'],4)
        self.assertEqual(dict(V16_SEGMENTS)['rank3'],4)
        self.assertEqual(dict(V16_SEGMENTS)['rank2'],6)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'v16.ass'
            create_subtitles(out,'고양이 돌발행동 TOP5',DEFAULT_CAPTIONS,
                             segments=V16_SEGMENTS,caption_phases={
                                 'rank5':['면봉을 보자','훌쩍 뛰네!'],
                                 'rank3':['어깨에서 출발','고양이 착지!']})
            t=out.read_text(encoding='utf-8')
            self.assertIn('pos(540,1248)',t)
            self.assertIn('0:00:02.00,0:00:06.00,Active',t)
            self.assertIn('0:00:11.00,0:00:15.00,Active',t)
            self.assertIn('0:00:15.00,0:00:21.00,Active',t)
            self.assertIn('0:00:21.00,0:00:27.00,Active',t)
            self.assertIn('0:00:30.00',t)

    def test_v17_low_resolution_and_risky_external_sources_rejected(self):
        self.assertFalse(sufficient_resolution(320,240))
        self.assertFalse(sufficient_resolution(720,360))
        self.assertTrue(sufficient_resolution(720,480))
        self.assertTrue(sufficient_resolution(1080,1920))
        self.assertEqual(action_group("File:Cat jumping backwards.webm"),"leap")
        self.assertEqual(action_group("File:Cat opening door.webm"),"object")
        external={'title':'File:Cat opening door.webm',
                  'source_claim':'YouTube: some channel',
                  'review_flags':['외부 재게시 원본 권리 확인 필요']}
        original=dict(external,source_claim='Own work',review_flags=[])
        self.assertTrue(is_external_reupload(external))
        self.assertFalse(is_external_reupload(original))
        self.assertLess(editorial_priority(external),editorial_priority(original))

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
