#!/usr/bin/env python3
"""V12 single-item Pexels editorial audition via the official free download action.

- Curated Pexels video IDs only; no scraping, bulk indexing or access bypass.
- One HTTP download per chosen page, capped by duration / file size.
- Never infer permission for music, faces, logos or YouTube monetization.
- Do not automatically promote clips to the final TOP5.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request
import urllib.error
from v8_moments import window_candidates, moment_photo
from v12_sources import allowed_page


def official_video_id(item):
    if not allowed_page(item) or item['provider'] != 'pexels':
        raise ValueError('Only curated Pexels video pages are accepted')
    path=urllib.parse.urlsplit(item['page_url']).path
    match=re.fullmatch(r'/video/[^/]+-([0-9]+)/?',path)
    if not match:
        raise ValueError('Invalid official video link')
    return int(match.group(1))


def safe_failure_code(exc):
    """Machine-readable cause with no secret URL, token or response body."""
    if isinstance(exc, (urllib.error.HTTPError,)):
        return "HTTP_REJECTED_OR_UNAVAILABLE"
    if isinstance(exc, (urllib.error.URLError, TimeoutError)):
        return "NETWORK_UNAVAILABLE_OR_TIMEOUT"
    if isinstance(exc, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
        return "MEDIA_DECODING_OR_PREVIEW_FAILED"
    message=str(exc)
    if "Redirect outside official Pexels video delivery host" in message:
        return "UNTRUSTED_REDIRECT_REJECTED"
    if "Official URL did not return a video file" in message:
        return "NOT_A_VIDEO_RESPONSE"
    if "size limit" in message or "size exceeds" in message:
        return "SOURCE_OVER_FILE_SIZE_LIMIT"
    if "Unsupported duration" in message:
        return "SOURCE_DURATION_UNSUPPORTED"
    if "Response too small for a video" in message:
        return "EMPTY_OR_INVALID_FILE"
    if isinstance(exc, ValueError):
        return "INVALID_METADATA_OR_MEDIA"
    return "OTHER_FILE_OR_DOWNLOAD_ERROR"


def download_single_pexels(item,filename,max_bytes=50*1024*1024):
    video_id=official_video_id(item)
    official_url=f'https://www.pexels.com/download/video/{video_id}/'
    request=urllib.request.Request(official_url,headers={
        'User-Agent':'TOP5-Editorial-Rights-Review/1.0',
        'Accept':'video/mp4,application/octet-stream;q=0.8,*/*;q=0.2',
    })
    with urllib.request.urlopen(request,timeout=45) as response:
        final=urllib.parse.urlsplit(response.geturl())
        if final.scheme!='https' or final.hostname not in (
                'www.pexels.com','videos.pexels.com'):
            raise RuntimeError('Redirect outside official Pexels video delivery host')
        declared=response.headers.get('Content-Length')
        if declared and int(declared)>max_bytes:
            raise RuntimeError('Video exceeds safe single-asset size limit')
        media_type=response.headers.get('Content-Type','').lower()
        if ('video/' not in media_type and
            'application/octet-stream' not in media_type):
            raise RuntimeError('Official URL did not return a video file')
        total=0
        with open(filename,'wb') as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:
                    break
                total+=len(chunk)
                if total>max_bytes:
                    raise RuntimeError('Video exceeded safe size limit while downloading')
                output.write(chunk)
        if total<4096:
            raise RuntimeError('Response too small for a video')
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                          '-of','default=noprint_wrappers=1:nokey=1',str(filename)],
                         capture_output=True,text=True,timeout=25,check=True)
    duration=float(probe.stdout.strip())
    if not 5.25<=duration<=240:
        raise RuntimeError('Unsupported duration')
    return {'duration_sec':round(duration,2),'size_bytes':total,
            'download_host':final.hostname,'video_id':video_id}


def make_five_second_preview(source,start,output):
    filter_graph=(
        "scale=360:600:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=360:600:(ow-iw)/2:(oh-ih)/2:color=black,"
        "drawbox=x=0:y=0:w=iw:h=46:color=black@0.85:t=fill,"
        "drawtext=text='EDITORIAL REVIEW ONLY':x=10:y=15:"
        "fontsize=18:fontcolor=white,"
        "fps=12,setsar=1,format=yuv420p"
    )
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
        '-ss',f'{start:.2f}','-i',str(source),'-t','5',
        '-vf',filter_graph,'-an','-c:v','libx264','-preset','veryfast',
        '-crf','31','-movflags','+faststart',str(output)],
        check=True,stdout=subprocess.DEVNULL,timeout=85)


def audition(records,dest,max_candidates=3):
    out=Path(dest)
    out.mkdir(parents=True,exist_ok=True)
    thumbs=out/'V12_PEXELS_FRAMES'
    thumbs.mkdir(exist_ok=True)
    clips=out/'V12_PEXELS_PREVIEWS'
    clips.mkdir(exist_ok=True)
    data=[]
    for item in [x for x in records if x.get('provider')=='pexels'][:max_candidates]:
        row={'id':item['id'],'title':item['title'],'source':item['page_url'],
             'creator':item.get('creator',''),'license':item['license_label'],
             'license_url':item['license_url'],
             'third_party_rights_verified':False,
             'audio_approved':False,'publication_approved':False,
             'editorial_status':'NOT_REVIEWED','windows':[]}
        source=out/f'temporary_{item["id"]}.mp4'
        try:
            info=download_single_pexels(item,source)
            row.update(info)
            wins=window_candidates(source,info['duration_sec'],seconds=5.0,count=3,max_scan=60)
            for moment,window in enumerate(wins,1):
                t=float(window['start'])
                video=clips/f'{item["id"]}_moment{moment}.mp4'
                still=thumbs/f'{item["id"]}_moment{moment}.jpg'
                make_five_second_preview(source,t,video)
                moment_photo(source,min(info['duration_sec']-0.2,t+2.4),still)
                row['windows'].append({
                    'source_time_sec':t,'preview_file':str(video.relative_to(out)),
                    'still_file':str(still.relative_to(out)),
                    'motion_score':window['motion'],
                    'funny_action_verified':False
                })
            row['editorial_status']='VIDEO_READY_FOR_HUMAN_REVIEW'
        except Exception as e:
            row['editorial_status']='DOWNLOAD_UNAVAILABLE_OR_NOT_LICENSE_CLEARED'
            row['failure_type']=type(e).__name__
            row['failure_code']=safe_failure_code(e)
            print('[V12 source unavailable]',item['id'],row['failure_code'],flush=True)
        finally:
            source.unlink(missing_ok=True)
        data.append(row)
    (out/'V12_PEXELS_AUDITION.json').write_text(
        json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    count=sum(x['editorial_status']=='VIDEO_READY_FOR_HUMAN_REVIEW' for x in data)
    lines=[
        '# V12 실제 장면 검수',
        f'검수용 미리보기 생성: {count}/{len(data)}개',
        '접근 제한을 우회하지 않았으며 공식 다운로드가 불가능한 원본은 제외합니다.',
        '미리보기는 사용권과 유튜브 게시의 승인을 의미하지 않습니다.',
        '프레임 차분은 재미를 이해하지 못합니다. 실제 5초 영상을 재생해야 합니다.',
        ''
    ]
    for item in data:
        lines.extend([
            f"## {item['title']}",
            f"원본: {item['source']}",
            f"상태: {item['editorial_status']}",
            f"창작자 표기: {item['creator']}",
            "제3자 권리/원본 음원: 미승인",
            "미리보기: "+", ".join(w['preview_file'] for w in item['windows']),
            ''
        ])
    (out/'V12_PEXELS_AUDITION.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'V12 official Pexels audition: {count}/{len(data)} preview sets; 0 approved to publish',flush=True)
    return data


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--catalog',default='sample/v12-sources.json')
    ap.add_argument('--output',default='output')
    ap.add_argument('--ids',default='',help='Comma-separated exact curated video IDs for small review')
    args=ap.parse_args()
    items=json.loads(Path(args.catalog).read_text(encoding='utf-8'))
    if args.ids:
        ids={x.strip() for x in args.ids.split(',') if x.strip()}
        if not 1<=len(ids)<=3:
            raise ValueError('At most 3 explicitly selected items per review')
        existing={x['id'] for x in items if x.get('provider')=='pexels'}
        if not ids.issubset(existing):
            raise ValueError('Only listed curated source IDs can be auditioned')
        items=[x for x in items if x.get('id') in ids]
    audition(items,args.output)


if __name__=='__main__':
    main()
