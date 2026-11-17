"""Automated objective defects on actual selected MP4. NOT a subjective 80-point score."""
import argparse, json, re, subprocess
from pathlib import Path

def run(video):
    video=str(video)
    p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height',
                      '-of','json',video],capture_output=True,text=True,timeout=30)
    if p.returncode: return {'technical_pass':False,'error':'ffprobe_failed'}
    info=json.loads(p.stdout)
    streams=info.get('streams',[])
    video_stream=next((s for s in streams if s.get('codec_type')=='video'),{})
    has_audio=any(s.get('codec_type')=='audio' for s in streams)
    duration=float(info.get('format',{}).get('duration',0))
    filters={'freeze':'freezedetect=n=-50dB:d=0.7','black':'blackdetect=d=0.25:pix_th=0.08'}
    findings={}
    for name, filt in filters.items():
        p=subprocess.run(['ffmpeg','-hide_banner','-i',video,'-vf',filt,'-an','-f','null','-'],
                         capture_output=True,text=True,timeout=150)
        findings[name]={'pass':p.returncode==0,'events':[
            line.strip() for line in p.stderr.splitlines()
            if ('freeze_start:' in line or 'freeze_end:' in line) if name=='freeze'
        ]} if name=='freeze' else {'pass':p.returncode==0,'events':[
            line.strip() for line in p.stderr.splitlines() if 'black_start:' in line]}
    audio_events=[]
    audio_filter_ok=True
    if has_audio:
        p=subprocess.run(['ffmpeg','-hide_banner','-i',video,'-af','silencedetect=noise=-42dB:d=0.6',
                          '-vn','-f','null','-'],capture_output=True,text=True,timeout=150)
        audio_filter_ok=(p.returncode==0)
        audio_events=[x.strip() for x in p.stderr.splitlines() if 'silence_start:' in x]
    flags=[]
    if duration<27 or duration>33: flags.append('duration_outside_27_to_33_seconds')
    if video_stream.get('width',0)<360 or video_stream.get('height',0)<640: flags.append('insufficient_review_resolution')
    if not has_audio: flags.append('audio_missing')
    if findings['freeze']['events']: flags.append('freeze_detected_requires_review')
    if findings['black']['events']: flags.append('black_frames_detected_requires_review')
    if not audio_filter_ok: flags.append('audio_filter_failed')
    if audio_events: flags.append('audio_silence_detected_requires_review')
    return {'technical_pass':not flags and all(x['pass'] for x in findings.values()),
            'objective_defect_flags':flags,'duration_sec':duration,'has_audio':has_audio,
            'audio_filter_pass':audio_filter_ok,
            'video_width':video_stream.get('width'),'video_height':video_stream.get('height'),
            'freeze_events':findings['freeze']['events'][:30],
            'black_events':findings['black']['events'][:30],
            'silence_events':audio_events[:30],
            'editorial_score_100':None,'rights_verified':False,'youtube_auto_upload':False}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--video',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    result=run(a.video)
    target=Path(a.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
