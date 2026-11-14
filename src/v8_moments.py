"""V8 alternative-action windows for CC video editorial review.

A frame-difference heuristic supplies three *candidate* five-second moments.
It cannot infer humor, verify filming rights, or approve publication.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess

def window_candidates(video_path, duration, seconds=5.0, count=3, max_scan=100.0):
    """Rank non-overlapping video action windows using 2fps gray frame differences."""
    scan=min(float(duration),max_scan)
    if scan<seconds+0.3:
        return [{'start':0.0,'motion':0.0,'algorithm':'short_source'}]
    w,h,fps=96,54,2
    try:
        raw=subprocess.check_output([
            'ffmpeg','-hide_banner','-loglevel','error','-i',str(video_path),
            '-t',f'{scan:.3f}','-vf',f'fps={fps},scale={w}:{h},format=gray',
            '-f','rawvideo','-pix_fmt','gray','-'
        ],stderr=subprocess.DEVNULL,timeout=100)
        step=w*h
        n=len(raw)//step
        if n<round(seconds*fps)+2:
            return [{'start':0.0,'motion':0.0,'algorithm':'too_few_frames'}]
        frames=[memoryview(raw)[i*step:(i+1)*step] for i in range(n)]
        diffs=[]
        for a,b in zip(frames,frames[1:]):
            diffs.append(sum(abs(a[i]-b[i]) for i in range(0,step,9))/((step+8)//9))
        points=[]
        length=int(seconds*fps)
        for frame in range(0,len(diffs)-length+2,4):
            sample=diffs[frame:frame+length-1]
            if not sample: continue
            # Sustained actions take precedence over isolated camera cuts.
            sample=sorted(sample)
            trimmed=sample[1:-1] or sample
            score=sum(trimmed)/len(trimmed)
            points.append((round(score,3),frame/fps))
        picked=[]
        for score,at in sorted(points,reverse=True):
            if all(abs(at-p['start'])>=seconds+0.5 for p in picked):
                picked.append({'start':round(min(at,max(0.0,duration-seconds-0.1)),2),
                              'motion':score,'algorithm':'frame_motion_not_humor'})
            if len(picked)>=count:
                break
        if not picked:
            return [{'start':0.0,'motion':0.0,'algorithm':'no_motion'}]
        return sorted(picked,key=lambda x:x['motion'],reverse=True)
    except (subprocess.SubprocessError,OSError,ValueError):
        return [{'start':0.0,'motion':0.0,'algorithm':'analysis_error'}]


def moment_photo(video_path, at, output_file, width=320, height=568):
    """Extract a phone-friendly uncropped frame from a candidate moment."""
    Path(output_file).parent.mkdir(parents=True,exist_ok=True)
    vf=(f'scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,'
        f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                    '-ss',f'{at:.3f}','-i',str(video_path),'-vf',vf,
                    '-frames:v','1','-q:v','4',str(output_file)],
                   check=True,timeout=55,stdout=subprocess.DEVNULL)


def publish_moment_review(items, out):
    """Write 9x3 moment screenshot contact sheets and structured source notes.

    Editorial status remains unreviewed; footage is not published.
    """
    out=Path(out)
    folder=out/'V8_MOMENT_FRAMES'
    folder.mkdir(parents=True,exist_ok=True)
    reports=[]
    for number,source in enumerate(items,1):
        wins=window_candidates(source['local_path'],source['duration'])
        expanded=[]
        for slot in range(3):
            candidate=wins[min(slot,len(wins)-1)]
            point=min(source['duration']-0.2,candidate['start']+2.5)
            jpg=folder/f'{number:02d}_{slot+1}.jpg'
            moment_photo(source['local_path'],point,jpg)
            expanded.append({**candidate,'slot':slot+1,'image_file':str(jpg.relative_to(out)),
                             'screen_action_verified':False,
                             'has_visible_payoff':'UNREVIEWED'})
        reports.append({'source_number':number,'title':source['title'],
                        'source_url':source['source_page'],
                        'license_metadata':source['license'],
                        'moments':expanded,'approved_for_publication':False})
    for slot in range(1,4):
        # One 3x3 sheet for each possible moment, numbered by source.
        concat=folder/f'moment_{slot}_frames.txt'
        concat.write_text(''.join("file '"+str((folder/f'{i:02d}_{slot}.jpg').resolve()).replace("'","'\\''")+"'\n" for i in range(1,len(items)+1)),encoding='utf-8')
        grid=out/f'V8_MOMENT_{slot}_GRID.jpg'
        # Input numbered files form a contiguous image sequence, no timing assumptions.
        import os
        syms=folder/f'moment_{slot:01d}_%02d.jpg'
        for i in range(1,len(items)+1):
            target=folder/f'moment_{slot}_{i:02d}.jpg'
            original=folder/f'{i:02d}_{slot}.jpg'
            target.write_bytes(original.read_bytes())
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                        '-framerate','1','-start_number','1','-i',str(syms),
                        '-vf','tile=3x3:padding=6:margin=6:color=black',
                        '-frames:v','1','-q:v','3',str(grid)],
                       check=True,timeout=55,stdout=subprocess.DEVNULL)
    (out/'V8_MOMENTS_REVIEW.json').write_text(
        json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'V8_EDITORIAL_GUIDE.md').write_text(
        '# V8 장면 검수\n\n'
        '동물 움직임 점수는 개그·반전·저작권의 판정이 아닙니다.\n'
        'V8_MOMENT_1_GRID~3_GRID를 비교하고 각 후보의 실제 움직이는 '
        'REVIEW_PREVIEWS도 함께 확인하세요.\n\n'
        '1. 5초 안에 웃음/반전/귀여움의 분명한 순간이 있는가?\n'
        '2. 시작과 끝이 연결되며 특정 대상에게 위험하지 않은가?\n'
        '3. 오디오에 별도의 음악, 대사, 타인 음원이 들어 있는가?\n'
        '4. 원작자/권리자/CC 조건을 실제로 확인했는가?\n'
        '5. 상황에 맞는 독창적 한국어 코멘트를 쓸 수 있는가?\n\n'
        '5개 모두 실제 편집 검수 통과 전에는 공개용 MP4로 취급하지 않습니다.\n',
        encoding='utf-8')
    return reports
