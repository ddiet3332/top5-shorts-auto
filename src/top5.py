#!/usr/bin/env python3
"""Build a review-only 30 second TOP5 draft from Wikimedia Commons CC BY/CC0 videos.
No automated publication. Licenses are metadata claims, NOT independently verified rights.
"""
from __future__ import annotations
import argparse
import csv
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
DEFAULT_QUERIES = ['cat playing', 'kitten playing', 'dog playing', 'puppy playing', 'funny animals', 'goat jumping', 'pet playing']
VIDEO_EXTS = ('.webm', '.ogv', '.ogg', '.mp4', '.mov', '.m4v')
MAX_MB = 60
MAX_REQUEST_BYTES = 60 * 1024 * 1024
MAX_TOTAL_BYTES = 220 * 1024 * 1024
CLIP_MIN_SEC = 5.25
CLIP_MAX_SEC = 600
SEGMENTS = [('hook', 2), ('rank5', 5), ('rank4', 5), ('rank3', 5), ('rank2', 5), ('rank1', 5), ('outro', 3)]
DEFAULT_CAPTIONS = {
    'hook': '여러분이라면 어떤 장면이 1위인가요?',
    'rank5': '5위 — 어떤 행동이 나올까요?',
    'rank4': '4위 — 예상과 다른 반응입니다',
    'rank3': '3위 — 순간을 자세히 보세요',
    'rank2': '2위 — 다음 장면과 비교해 보세요',
    'rank1': '1위 — 여러분의 선택은?',
    'outro': '여러분의 1위는 무엇인가요?',
}

class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_entityref(self, name):
        self.parts.append(html.unescape('&'+name+';'))
    def handle_charref(self, name):
        self.parts.append(html.unescape('&#'+name+';'))

def clean_html(value):
    if not value:
        return ''
    parser = PlainHTML()
    parser.feed(str(value))
    return re.sub(r'\s+', ' ', html.unescape(''.join(parser.parts))).strip()

def short_meta(ext, key):
    v = ext.get(key, {})
    return clean_html(v.get('value', '') if isinstance(v, dict) else v)

def supported_license(license_url, short_name=''):
    """Whitelist CC BY and CC0 only. Excludes BY-SA, NC, ND, or ambiguous labels."""
    url = (license_url or '').strip().lower().replace('http://', 'https://')
    url = url.split('?')[0].split('#')[0].rstrip('/')
    if re.fullmatch(r'https://creativecommons\.org/licenses/by/(?:2\.0|2\.5|3\.0|4\.0)', url):
        return 'CC BY'
    if url == 'https://creativecommons.org/publicdomain/zero/1.0':
        return 'CC0'
    return None

def user_agent():
    repo = os.environ.get('GITHUB_REPOSITORY', 'WikimediaCommons')
    return f'TOP5ShortsDraft/1.0 (https://github.com/{repo}; review-only video prototype)'

def fetch_json(params, tries=3):
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': user_agent(), 'Accept': 'application/json'})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            if i == tries - 1:
                raise RuntimeError(f'Wikimedia API 실패: {e}') from e
            time.sleep(1.4 * (i + 1))
    raise RuntimeError('API request failed')

def file_page_for_title(title):
    return 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_'), safe=':/()')

def query_candidates(term, per_query=100):
    # Restrict the Commons full-text search to video files rather than images.
    params = {
        'action': 'query', 'format': 'json', 'formatversion': '2',
        'generator': 'search', 'gsrsearch': f'{term} filetype:video',
        'gsrnamespace': '6', 'gsrlimit': str(per_query),
        'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata',
    }
    yield from extract_candidates(fetch_json(params))

def category_candidates(category, per_query=100):
    # Commons has curated categories of actual video files; use these as fallback.
    params = {
        'action': 'query', 'format': 'json', 'formatversion': '2',
        'generator': 'categorymembers', 'gcmtitle': 'Category:' + category,
        'gcmtype': 'file', 'gcmlimit': str(per_query),
        'prop': 'imageinfo', 'iiprop': 'url|size|mime|extmetadata',
    }
    yield from extract_candidates(fetch_json(params))

def extract_candidates(data):
    for page in data.get('query', {}).get('pages', []):
        title = page.get('title', '')
        if not title.lower().endswith(VIDEO_EXTS):
            continue
        ii_list = page.get('imageinfo', [])
        if not ii_list:
            continue
        ii = ii_list[0]
        if not str(ii.get('mime', '')).startswith('video/') and not title.lower().endswith(('.webm', '.ogv', '.mp4')):
            continue
        filesize = int(ii.get('size', 0))
        if not 50000 < filesize <= MAX_REQUEST_BYTES:
            continue
        ext = ii.get('extmetadata', {})
        licurl = short_meta(ext, 'LicenseUrl')
        license_type = supported_license(licurl, short_meta(ext, 'LicenseShortName'))
        if not license_type:
            continue
        author = short_meta(ext, 'Artist') or short_meta(ext, 'Credit')
        if license_type == 'CC BY' and (not author or author.lower() in ('unknown', 'anonymous', 'n/a')):
            continue
        src_url = ii.get('url', '')
        if not src_url.startswith('https://upload.wikimedia.org/'):
            continue
        source_claim = short_meta(ext, 'Source')
        flags = []
        if re.search(r'youtube|tiktok|instagram|facebook|vimeo|flickr', source_claim, re.I):
            flags.append('외부 재게시 원본 권리 확인 필요')
        if not source_claim:
            flags.append('원 촬영·출처 확인 필요')
        flags.extend(['영상 속 인물/음악/상표 등 제3자 권리 확인 필요', '직접 장면 확인 필요'])
        yield {
            'title': title, 'source_page': page.get('canonicalurl') or file_page_for_title(title),
            'download_url': src_url, 'author': author,
            'license': short_meta(ext, 'LicenseShortName') or license_type,
            'license_url': licurl,
            'source_claim': source_claim,
            'size_bytes': filesize,
            'review_flags': flags,
            'license_status': 'metadata_only_unverified',
            'approved_for_publication': False,
        }

def discover(query, count=30):
    words = []
    if query and query.strip():
        words.append(query.strip())
    words += DEFAULT_QUERIES
    seen_q = set()
    picked = {}
    errors = []
    for phrase in words:
        if phrase.lower() in seen_q:
            continue
        seen_q.add(phrase.lower())
        try:
            for c in query_candidates(phrase, 100):
                if c['source_page'] not in picked:
                    picked[c['source_page']] = c
            print(f'[검색] {phrase}: 총 {len(picked)}개 후보 확보', flush=True)
        except RuntimeError as e:
            errors.append(str(e))
        if len(picked) >= count:
            break
        time.sleep(0.3)
    # Media-specific categories are more reliable than keyword searches on Commons.
    # Category names are verified existing Wikimedia Commons categories.
    if len(picked) < count:
        lower = (query or '').lower()
        cat_categories = ['Videos of playing cats', 'Videos of cats', 'Videos of kittens']
        dog_categories = ['Videos of dogs']
        if 'dog' in lower or 'puppy' in lower:
            categories = dog_categories + cat_categories
        else:
            categories = cat_categories + dog_categories
        for category in categories:
            try:
                for c in category_candidates(category, 100):
                    if c['source_page'] not in picked:
                        picked[c['source_page']] = c
                print(f'[카테고리] {category}: 총 {len(picked)}개 후보 확보', flush=True)
            except RuntimeError as e:
                errors.append(str(e))
            if len(picked) >= count:
                break
            time.sleep(0.3)
    if not picked and errors:
        raise RuntimeError('; '.join(errors[:2]))
    return list(picked.values())

def save_candidates(cands, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / 'candidates.json', 'w', encoding='utf-8') as f:
        json.dump(cands, f, ensure_ascii=False, indent=2)
    with open(dest / 'candidates.csv', 'w', newline='', encoding='utf-8-sig') as f:
        fields = ['title', 'source_page', 'author', 'license', 'license_url', 'source_claim', 'size_bytes', 'license_status', 'approved_for_publication', 'review_flags']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in cands:
            writer.writerow({k: ' / '.join(c[k]) if isinstance(c.get(k), list) else c.get(k, '') for k in fields})

def probe_duration(path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=25).decode().strip()
        return float(out)
    except Exception:
        return 0

def download_video(cand, path):
    url = cand['download_url']
    if not url.startswith('https://upload.wikimedia.org/'):
        raise ValueError('신뢰된 Wikimedia 업로드 도메인이 아닙니다.')
    request = urllib.request.Request(url, headers={'User-Agent': user_agent()})
    temp = Path(str(path) + '.part')
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=80) as response, open(temp, 'wb') as out:
            for chunk in iter(lambda: response.read(1024*1024), b''):
                size += len(chunk)
                if size > MAX_REQUEST_BYTES:
                    raise ValueError('다운로드 용량 초과')
                out.write(chunk)
        if size < 50000:
            raise ValueError('동영상 파일이 너무 작습니다.')
        temp.replace(path)
        return size
    except Exception:
        temp.unlink(missing_ok=True)
        raise

def collect_media(cands, out, count=5):
    clips = Path(out)/'clips'
    clips.mkdir(parents=True, exist_ok=True)
    selected=[]
    downloaded_bytes=0
    rejects=[]
    for i,c in enumerate(cands):
        if len(selected)>=count:
            break
        if downloaded_bytes + c['size_bytes'] > MAX_TOTAL_BYTES:
            rejects.append({'title':c['title'],'reason':'총 다운로드 한도 초과'})
            continue
        suffix=Path(urllib.parse.urlparse(c['download_url']).path).suffix.lower()
        file = clips / f'clip_{len(selected)+1:02}{suffix}'
        try:
            size=download_video(c,file)
            length=probe_duration(file)
            if not (CLIP_MIN_SEC <= length <= CLIP_MAX_SEC):
                file.unlink(missing_ok=True)
                rejects.append({'title':c['title'],'reason':f'영상 길이 미지원: {length:.2f}초'})
                continue
            entry = {**c, 'local_path': str(file), 'duration': length}
            selected.append(entry)
            downloaded_bytes += size
            print(f'[확보 {len(selected)}/{count}] {c["title"]} ({length:.1f}s)',flush=True)
        except Exception as ex:
            file.unlink(missing_ok=True)
            rejects.append({'title':c['title'],'reason':str(ex)[:140]})
            print(f'[건너뜀] {c["title"]}: {str(ex)[:140]}',flush=True)
    (Path(out)/'rejected.json').write_text(json.dumps(rejects,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(selected)!=count:
        raise RuntimeError(f'동영상 {count}개 필요하지만 {len(selected)}개만 확보했습니다. 후보와 rejected.json 확인 후 다른 주제로 재실행하세요.')
    return selected

def ass_escape(s):
    return str(s).replace('\\','\\\\').replace('{','(').replace('}',')').replace('\n',' ')

def ass_timestamp(sec):
    hh=int(sec//3600); mm=int(sec//60)%60; ss=sec%60
    return f'{hh}:{mm:02}:{ss:05.2f}'

def create_subtitles(path, title, captions):
    """Positioned ASS overlays; include caption in lower central area and fixed ranking column."""
    header='''[Script Info]
Title: TOP5 ranking draft
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,NanumSquare,85,&H0000DDFF,&H0000DDFF,&H00191919,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,8,20,20,20,1
Style: Rank,NanumSquare,60,&H00FFFFFF,&H00FFFFFF,&H00101010,&H60000000,-1,0,0,0,100,100,0,0,1,5,2,7,15,10,10,1
Style: Active,NanumSquare,68,&H0000A5FF,&H0000A5FF,&H00101010,&H60000000,-1,0,0,0,100,100,0,0,1,6,2,7,15,10,10,1
Style: Caption,NanumSquare,62,&H00FFFFFF,&H00FFFFFF,&H00111111,&H88000000,-1,0,0,0,100,100,0,0,3,3,1,5,35,35,0,1
Style: Brand,NanumSquare,42,&H00FFFFFF,&H00FFFFFF,&H00181818,&H40000000,-1,0,0,0,100,100,0,0,1,4,1,7,15,15,15,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    current=0
    lines = [header]
    def event(start,end,style,txt,extra='',layer=3):
        lines.append(f'Dialogue: {layer},{ass_timestamp(start)},{ass_timestamp(end)},{style},,0,0,0,,{extra}{ass_escape(txt)}\n')
    event(0,30,'Title', title,'{\\an8\\pos(540,130)}',5)
    event(0,30,'Brand','TOP5 · DRAFT / RIGHTS REVIEW REQUIRED','{\\an7\\pos(40,1830)}',2)
    for name,length in SEGMENTS:
        end=current+length
        ranking = int(name[-1]) if name.startswith('rank') else 0
        for r in range(1,6):
            event(current,end,'Active' if r==ranking else 'Rank',f'{r}위','{\\an7\\pos(44,'+str(350+(r-1)*112)+')}',3)
        event(current,end,'Caption',captions.get(name,DEFAULT_CAPTIONS[name]),'{\\an5\\pos(540,1260)}',5)
        current=end
    Path(path).write_text(''.join(lines),encoding='utf-8')

def run(cmd, timeout=300):
    print('[ffmpeg]', ' '.join(cmd[:9]), '...',flush=True)
    subprocess.run(cmd, check=True, timeout=timeout, stdout=subprocess.DEVNULL)

def render_segment(input_path, output_path, start, seconds, width=1080, height=1920, fps=24):
    # Blurred filling prevents destructive crop of landscape source while keeping action visible.
    # Top5 landscape foreground may be letterboxed over defocused scene; a human crop check is required.
    filter_graph=(
        '[0:v]split=2[bgsrc][fgsrc];'
        f'[bgsrc]scale={width}:{height}:force_original_aspect_ratio=increase,'
        f'crop={width}:{height},boxblur=20:2[bg];'
        f'[fgsrc]scale={width}:{int(height*.80)}:force_original_aspect_ratio=decrease[fg];'
        '[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1,'
        f'fps={fps},setsar=1,format=yuv420p[outv]'
    )
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{start:.3f}','-i',str(input_path),
         '-filter_complex',filter_graph,'-map','[outv]','-an','-frames:v',str(round(seconds*fps)),
         '-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(output_path)],timeout=240)
    # ffmpeg may terminate before target if source is shorter than segment. Fail rather than publish broken video.
    dur=probe_duration(output_path)
    if dur < seconds-0.12:
        raise RuntimeError(f'잘린 렌더 구간: {output_path}, {dur:.2f}초 / {seconds}초')

def render_video(selected, dest, title, captions, narration=None, size='1080x1920'):
    width,height=map(int,size.lower().split('x'))
    if width <= 0 or height <= 0 or width*16!=height*9:
        raise ValueError('9:16 해상도만 허용')
    dest=Path(dest); tmp=dest/'render_tmp'; tmp.mkdir(parents=True,exist_ok=True)
    # Actual 5-ranked segments are in rank5...rank1 order. The 1st-ranked clip is the final element.
    lookup={'hook':selected[-1], 'outro':selected[-1]}
    for number,item in zip([5,4,3,2,1],selected):
        lookup[f'rank{number}']=item
    videos=[]
    for ix,(name,length) in enumerate(SEGMENTS):
        clip=lookup[name]
        duration=clip['duration']
        if name=='hook': start=max(0.0,duration-2.25)
        elif name=='outro': start=max(0.0,duration-3.15)
        else: start=max(0.0,min(duration-length-0.2,(duration-length)*0.43))
        seg=tmp/f'segment_{ix:02}.mp4'
        render_segment(clip['local_path'],seg,start,length,width,height)
        videos.append(seg)
    concat=tmp/'concat.txt'
    concat.write_text(''.join("file '"+str(f.resolve()).replace("'", "'\\''")+"'\n" for f in videos),encoding='utf-8')
    joined=tmp/'joined.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(joined)])
    ass=tmp/'ranking.ass'
    create_subtitles(ass,title,captions)
    # Uses libass subtitles; fonts-nanum package installed in GitHub Actions.
    # libass path escaping: fixed working directory with no colon/special characters.
    final=dest/f'TOP5_DRAFT_REVIEW_ONLY_{width}x{height}.mp4'
    input_audio=(['-i',str(narration)] if narration else ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo'])
    audio_filter=('[1:a]apad,atrim=0:30,asetpts=N/SR/TB[aout]' if narration else '[1:a]atrim=0:30,asetpts=N/SR/TB[aout]')
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(joined),*input_audio,
         '-filter_complex',f'[0:v]subtitles={ass}[vout];{audio_filter}',
         '-map','[vout]','-map','[aout]','-t','30',
         '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-r','24',
         '-c:a','aac','-b:a','128k','-movflags','+faststart',str(final)],timeout=350)
    final_duration=probe_duration(final)
    if abs(final_duration-30)>0.3:
        raise RuntimeError(f'최종 영상 길이 오류: {final_duration:.2f}초')
    return final

def write_rights_docs(selected,out):
    out=Path(out)
    lines=['# YouTube 설명란 출처 표기 초안','', '원본을 발췌·재편집하고 한국어 순위와 자막을 추가했습니다.',
           '이 문서는 라이선스 메타데이터 기반 초안입니다. 게시 전 원권리자·음악·출연자 검토가 필요합니다.','']
    report=['# 게시 전 검토 (자동 통과 아님)','', '- [ ] 5개 원본의 원제작자 및 라이선스 검증',
            '- [ ] 원본에 삽입된 음악·음성·영상에 별도 권리 침해가 없는지 확인',
            '- [ ] 인물 초상·개인정보·동물 안전·브랜드 문제 검토',
            '- [ ] 실제 영상 30초 전체를 보고 오동작·유해 장면 검수',
            '- [ ] 자신만의 해설, 상황 분석과 새 스토리로 실질적 변형 추가',
            '- [ ] 유튜브 재사용/비진정성 콘텐츠 정책 검토','', '## 원본별 목록','']
    for rank,item in zip([5,4,3,2,1],selected):
        title=item['title']
        lines += [f'{rank}위: {title}', f'창작자: {item["author"] or "정보 없음"}',
                  f'원본: {item["source_page"]}', f'라이선스: {item["license"]} ({item["license_url"]})',
                  '변경사항: 원본 영상 일부 발췌, 리프레이밍, 순위 그래픽과 자막 추가','']
        report += [f'### {rank}위 {title}', f'- 원본: {item["source_page"]}',
                   f'- 메타데이터 라이선스: {item["license"]} ({item["license_url"]})',
                   f'- 출처 표기명: {item["author"]}',
                   f'- 점검: {" / ".join(item["review_flags"])}','']
    (out/'YOUTUBE_CREDITS.txt').write_text('\n'.join(lines),encoding='utf-8')
    (out/'RIGHTS_CHECKLIST.md').write_text('\n'.join(report),encoding='utf-8')
    with open(out/'selected_sources.json','w',encoding='utf-8') as f:
        # Avoid exposing runner local paths and ephemeral download URLs in public logs.
        json.dump([{k:v for k,v in item.items() if k not in ('local_path','download_url')} for item in selected],f,ensure_ascii=False,indent=2)

def cli(argv=None):
    parser=argparse.ArgumentParser(description='Wikimedia Commons CC BY/CC0 TOP5 ranking shorts draft builder')
    parser.add_argument('--mode',choices=['discover','draft','local-test'],default=os.environ.get('MODE','draft'))
    parser.add_argument('--topic',default=os.environ.get('TOPIC','cat playing'))
    parser.add_argument('--title',default=os.environ.get('TITLE','황당한 동물들의 순간 TOP5'))
    parser.add_argument('--output',default='output')
    parser.add_argument('--script',default='sample/script.json')
    parser.add_argument('--narration',default='')
    parser.add_argument('--local-manifest',default='')
    parser.add_argument('--size',default='1080x1920')
    args=parser.parse_args(argv)
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    captions=dict(DEFAULT_CAPTIONS)
    if Path(args.script).exists():
        settings=json.loads(Path(args.script).read_text(encoding='utf-8'))
        captions.update({str(k):str(v)[:85] for k,v in settings.get('captions',{}).items() if k in captions})
    if args.mode=='local-test':
        if not args.local_manifest:
            parser.error('--local-manifest required for local-test')
        selected=json.loads(Path(args.local_manifest).read_text(encoding='utf-8'))
        if len(selected)!=5:
            raise RuntimeError('로컬 테스트는 영상 5개가 필요합니다.')
    else:
        cands=discover(args.topic,count=35 if args.mode=='draft' else 25)
        save_candidates(cands,out)
        if args.mode=='discover':
            print(f'검색 완료: 후보 {len(cands)}개. 출처·라이선스 검토하세요.',flush=True)
            return 0
        if len(cands)<5:
            raise RuntimeError('CC BY/CC0 영상 후보 5개 미만입니다. 주제를 변경해 다시 실행하세요.')
        selected=collect_media(cands,out)
    write_rights_docs(selected,out)
    narration=Path(args.narration) if args.narration else None
    if narration and not narration.exists():
        raise FileNotFoundError(str(narration))
    final=render_video(selected,out,args.title,captions,narration,args.size)
    print(f'렌더 완료: {final} ({probe_duration(final):.2f}초)',flush=True)
    return 0

if __name__=='__main__':
    try:
        sys.exit(cli())
    except Exception as e:
        print(f'오류: {e}',file=sys.stderr)
        sys.exit(1)