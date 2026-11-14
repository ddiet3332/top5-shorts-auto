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
import math
import wave
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
MAX_TOTAL_BYTES = 260 * 1024 * 1024
REVIEW_POOL = 9
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

def candidate_relevance(title):
    """Metadata prefilter only. It does not understand comedic quality."""
    t = str(title or '').lower()
    reject = ('animation', 'animated', 'cartoon', 'magician', 'movie', 'trailer',
              'music video', 'film', 'documentary', 'ai generated', 'vfx',
              'lecture', 'advert', 'compilation', 'gameplay', 'drawing',
              'tv show', 'nickelodeon', 'zoey 101', 'victorious', 'tetris',
              'ctwc', 'kenan thompson', 'interview', 'copyright free',
              'fox dark', 'soundtrack', 'netflix', 'disney', 'fox news')
    if any(word in t for word in reject):
        return -100
    # Without animal words, generic 'playing' searches include television and gaming.
    animals=('cat', 'kitten', 'dog', 'puppy', 'puppies', 'goat', 'hamster',
             'ferret', 'rabbit', 'parrot', 'peacock', 'elephant', 'gato',
             'кот', 'кошен', 'кошка', 'mačka', 'felis catus')
    if not any(word in t for word in animals):
        return -100
    terms = ('play', 'jump', 'chase', 'funny', 'surpris', 'curious', 'react',
             'climb', 'trick', 'roll', 'bounce', 'fall', 'run', 'fight', 'catch')
    return min(5, sum(2 for word in terms if word in t))


def motion_highlight(path, duration, seconds=5):
    """Pick energetic 5s window from 2fps gray frames, not a semantic fun detector."""
    sample_secs = min(48.0, float(duration) - 0.08)
    sample_secs = max(0.0, sample_secs)
    if sample_secs < seconds:
        return 0.0, 0.0
    w,h,fps = 96,54,2
    try:
        raw = subprocess.check_output([
            'ffmpeg','-hide_banner','-loglevel','error','-i',str(path),
            '-t',f'{sample_secs:.3f}','-vf',f'fps={fps},scale={w}:{h},format=gray',
            '-f','rawvideo','-pix_fmt','gray','-'],stderr=subprocess.DEVNULL,timeout=75)
        stride = w*h
        frames = [memoryview(raw)[i:i+stride] for i in range(0,len(raw)-stride+1,stride)]
        if len(frames)<12:
            return 0.0, 0.0
        changes=[]
        for a,b in zip(frames,frames[1:]):
            dist=sum(abs(a[i]-b[i]) for i in range(w*6,w*(h-6),6))
            changes.append(dist / max(1, len(range(w*6,w*(h-6),6))))
        window=max(2,round(seconds*fps)-1)
        best_start,best_score=0,0.0
        for ix in range(0,max(1,len(changes)-window+1),2):
            clip=changes[ix:ix+window]
            if not clip: continue
            ordered=sorted(clip)
            sustained=sum(ordered[1:-1] or ordered)/max(1,len(ordered[1:-1] or ordered))
            score=sustained*(0.4+0.6*min(1.0,sum(1 for n in clip if n>1.8)/max(1,len(clip))))
            if score>best_score:
                best_start,best_score=ix/fps,score
        return min(best_start,max(0.0,duration-seconds-0.2)), round(best_score,3)
    except (subprocess.SubprocessError, OSError, ValueError):
        return 0.0, 0.0


def crop_risk(path):
    """Fraction of original width cut for 9:16 crop. Used for review flag only."""
    w,h=probe_dimensions(path)
    if not w or not h:
        return 1.0
    return round(max(0.0,1.0-(9/16)/(w/h)),3)



def _preview_crop_fraction(path, start, seconds, width=330, height=580):
    focus=choose_focus_x(path,start,seconds,width,height)
    original_w,original_h=probe_dimensions(path)
    fraction=(width/height)/(original_w/original_h) if original_w and original_h else 1.0
    if fraction>=1:
        return 0.5
    return max(0.0,min(1.0,(focus-fraction/2)/(1-fraction)))


def create_review_gallery(items, out):
    """Produce original-aspect and proposed-vertical preview grids for mobile QA."""
    out=Path(out)
    thumbs=out/'REVIEW_THUMBNAILS'
    thumbs.mkdir(parents=True,exist_ok=True)
    previews=out/'REVIEW_PREVIEWS'
    previews.mkdir(parents=True,exist_ok=True)
    records=[]
    for ix,item in enumerate(items,1):
        file=item['local_path']
        sample=min(max(0.0,float(item['highlight_start'])+2.0),
                   max(0.0,item['duration']-0.3))
        focus_left=_preview_crop_fraction(file,sample,2.0)
        for mode in ('original','vertical'):
            if mode=='original':
                vf=('scale=330:580:force_original_aspect_ratio=decrease:flags=lanczos,'
                    'pad=330:580:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1')
            else:
                vf=('scale=330:580:force_original_aspect_ratio=increase:flags=lanczos,'
                    f'crop=330:580:x=(iw-ow)*{focus_left:.5f}:y=(ih-oh)/2,setsar=1')
            vf+=f",drawtext=text='{ix:02d}':x=15:y=15:fontsize=46:fontcolor=yellow:borderw=3:bordercolor=black"
            jpg=thumbs/f'{mode}_{ix:02d}.jpg'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                            '-ss',f'{sample:.2f}','-i',str(file),'-vf',vf,
                            '-frames:v','1','-q:v','4',str(jpg)],
                           check=True,timeout=55,stdout=subprocess.DEVNULL)
        # Both motion pictures appear side-by-side for action and framing QA.
        # Left = entire source, right = the proposed 9:16 fullscreen crop.
        full=(
            'scale=360:640:force_original_aspect_ratio=decrease,'
            'pad=360:640:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1'
        )
        vertical=(
            'scale=360:640:force_original_aspect_ratio=increase,'
            f'crop=360:640:x=(iw-ow)*{focus_left:.5f}:y=(ih-oh)/2,setsar=1'
        )
        side_by_side=f'[0:v]split=2[raw][crop];[raw]{full}[left];[crop]{vertical}[right];' + (
            '[left][right]hstack=inputs=2,fps=12,format=yuv420p[outv]')
        preview=previews/f'{ix:02d}.mp4'
        take=min(5.0,max(0.1,item['duration']-float(item['highlight_start'])-0.05))
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-ss',f"{item['highlight_start']:.2f}",'-i',str(file),
            '-t',f'{take:.2f}','-filter_complex',side_by_side,
            '-map','[outv]','-an','-c:v','libx264','-preset','veryfast',
            '-crf','28','-movflags','+faststart',str(preview)
        ],check=True,timeout=100,stdout=subprocess.DEVNULL)
        records.append({
            'number':ix,'title':item['title'],'source_page':item['source_page'],
            'author':item['author'],'license':item['license'],
            'license_url':item['license_url'],
            'sample_source_second':round(sample,2),
            'highlight_start':item['highlight_start'],
            'motion_score':item['motion_score'],
            'crop_risk':item['crop_risk'],
            'editorial_status':'NEEDS_HUMAN_REVIEW',
            'copyright_status':'UNVERIFIED_METADATA_ONLY',
            'rank_is_provisional':True,
            'preview_file':f'REVIEW_PREVIEWS/{ix:02d}.mp4',
            'crop_warning':item['crop_risk']>0.55,
        })
    for mode in ('original','vertical'):
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',
                        '-framerate','1','-start_number','1','-i',
                        str(thumbs/f'{mode}_%02d.jpg'),
                        '-vf','tile=3x3:padding=6:margin=6:color=black',
                        '-frames:v','1','-q:v','3',str(out/f'REVIEW_{mode.upper()}_GRID.jpg')],
                       check=True,timeout=65,stdout=subprocess.DEVNULL)
    (out/'REVIEW_SHORTLIST.json').write_text(
        json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# V4 TOP5 후보 검수표','',
           '이 순위는 동작량에 의한 임시 추천일 뿐 웃김이나 저작권 승인을 의미하지 않습니다.',
           'REVIEW_ORIGINAL_GRID.jpg와 REVIEW_VERTICAL_GRID.jpg를 같은 번호로 비교하세요.',
           'REVIEW_PREVIEWS의 01.mp4~09.mp4는 왼쪽 원본·오른쪽 9:16 제안 컷 5초를 동시에 보여줍니다.',
           '원본에서는 보이는 동물이 세로 화면에서 잘리면 탈락시키거나 초점을 조정해야 합니다.',
           '권리 검증 없이 유튜브에 게시하지 마세요.','']
    for c in records:
        lines.extend([f"## {c['number']:02d}. {c['title']}",
                      f"원본: {c['source_page']}",
                      f"라이선스 표기: {c['license']} ({c['license_url']})",
                      f"움직임 지표: {c['motion_score']}, 가로 크롭 손실 위험: {c['crop_risk']}",
                      '- [ ] 실제 재미/반전 존재',
                      '- [ ] 동물 또는 주된 장면이 잘리지 않음',
                      '- [ ] 원작자·음악·출연자 권리 확인',''])
    (out/'REVIEW_GUIDE.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'[V4 검수] 후보 {len(records)}개, 원본·세로 비교 이미지 생성 완료',flush=True)


def collect_media(cands, out, count=5, review_only=False, excluded_titles=None):
    clips = Path(out)/'clips'
    clips.mkdir(parents=True, exist_ok=True)
    pool=[]
    downloaded_bytes=0
    rejects=[]
    candidates = sorted(cands, key=lambda x: candidate_relevance(x['title']), reverse=True)
    excluded_titles=set(excluded_titles or [])
    for i,c in enumerate(candidates):
        if len(pool)>=max(count,REVIEW_POOL):
            break
        if c['title'] in excluded_titles:
            rejects.append({'title':c['title'],'reason':'수동 편집 검수에서 부적합으로 지정된 원본'})
            continue
        if candidate_relevance(c['title'])<=-100:
            rejects.append({'title':c['title'],'reason':'애니메이션/영화 등 비실사 콘텐츠 제목 제외'})
            continue
        if downloaded_bytes + c['size_bytes'] > MAX_TOTAL_BYTES:
            rejects.append({'title':c['title'],'reason':'총 다운로드 한도 초과'})
            continue
        suffix=Path(urllib.parse.urlparse(c['download_url']).path).suffix.lower()
        file = clips / f'clip_{len(pool)+1:02}{suffix}'
        try:
            size=download_video(c,file)
            length=probe_duration(file)
            if not (CLIP_MIN_SEC <= length <= CLIP_MAX_SEC):
                file.unlink(missing_ok=True)
                rejects.append({'title':c['title'],'reason':f'영상 길이 미지원: {length:.2f}초'})
                continue
            highlight,energy=motion_highlight(file,length)
            risk=crop_risk(file)
            entry={**c, 'local_path':str(file),'duration':length,
                   'highlight_start':highlight, 'motion_score':energy,
                   'crop_risk':risk, 'metadata_score':candidate_relevance(c['title'])}
            pool.append(entry)
            downloaded_bytes += size
            print(f'[후보 확보 {len(pool)}/{REVIEW_POOL}] {c["title"]} ({length:.1f}s, motion={energy:.2f}, crop={risk:.2f})',flush=True)
        except Exception as ex:
            file.unlink(missing_ok=True)
            rejects.append({'title':c['title'],'reason':str(ex)[:140]})
            print(f'[건너뜀] {c["title"]}: {str(ex)[:140]}',flush=True)
    (Path(out)/'rejected.json').write_text(json.dumps(rejects,ensure_ascii=False,indent=2),encoding='utf-8')
    if len(pool)<count:
        raise RuntimeError(f'동영상 {count}개 필요하지만 {len(pool)}개만 확보했습니다. 다른 주제를 사용하세요.')
    # Motion is a heuristic for preview order, NOT proof of humor.
    def scene_score(x):
        return min(x['motion_score'],22)*1.4 + x['metadata_score']*1.7 - x['crop_risk']*7
    ranked=sorted(pool,key=scene_score,reverse=True)
    if review_only:
        create_review_gallery(ranked,out)
        return []
    selected=list(reversed(ranked[:count]))
    for entry in selected:
        entry['selection_score']=round(scene_score(entry),2)
    kept={x['local_path'] for x in selected}
    for x in pool:
        if x['local_path'] not in kept:
            Path(x['local_path']).unlink(missing_ok=True)
            rejects.append({'title':x['title'], 'reason':'장면 움직임·크롭 위험 기반 후보 점수 미선정'})
    (Path(out)/'rejected.json').write_text(json.dumps(rejects,ensure_ascii=False,indent=2),encoding='utf-8')
    (Path(out)/'MOTION_RANKING_REPORT.json').write_text(json.dumps([
       {k:v for k,v in x.items() if k not in ('local_path','download_url')}
       for x in ranked],ensure_ascii=False,indent=2),encoding='utf-8')
    return selected

def ass_escape(s):
    return str(s).replace('\\','\\\\').replace('{','(').replace('}',')').replace('\n',' ')

def ass_timestamp(sec):
    hh=int(sec//3600); mm=int(sec//60)%60; ss=sec%60
    return f'{hh}:{mm:02}:{ss:05.2f}'

def source_label(title, overrides=None):
    """A source title or explicit, source-accurate nickname. Never invent an action."""
    title = str(title or '').strip()
    if overrides and title in overrides:
        label = str(overrides[title]).strip()
        if label:
            return label[:18]
    stem = re.sub(r'^File:', '', title, flags=re.I)
    stem = re.sub(r'\.(?:webm|ogv|ogg|mp4|mov|m4v)$', '', stem, flags=re.I)
    stem = re.sub(r'\s*\(\d{8,}\)', '', stem)
    stem = re.sub(r'[_\s]+', ' ', stem).strip(' .-_')
    return (stem or '원본 이름 확인')[:18]


def probe_dimensions(path):
    try:
        result = subprocess.check_output([
            'ffprobe','-v','error','-select_streams','v:0',
            '-show_entries','stream=width,height','-of','csv=p=0:s=x',str(path)
        ],timeout=20).decode().strip()
        w,h=map(int,result.split('x'))
        return w,h
    except Exception:
        return 0,0


def choose_focus_x(path, start, seconds, width=1080, height=1920):
    """Heuristic: center the most moving horizontal region; not an animal detector."""
    vw,vh=probe_dimensions(path)
    if not vw or not vh or vw/vh <= width/height*1.03:
        return 0.5
    frame_w,frame_h=160,90
    try:
        raw=subprocess.check_output([
            'ffmpeg','-hide_banner','-loglevel','error','-ss',f'{start:.3f}',
            '-i',str(path),'-t',str(min(seconds,5)),'-vf',
            f'fps=2,scale={frame_w}:{frame_h},format=gray',
            '-f','rawvideo','-pix_fmt','gray','-'
        ],stderr=subprocess.DEVNULL,timeout=22)
        stride=frame_w*frame_h
        frames=[raw[i:i+stride] for i in range(0,len(raw)-stride+1,stride)]
        if len(frames)<2:
            return 0.5
        energy=[0]*frame_w
        for previous,current in zip(frames,frames[1:]):
            for y in range(4,frame_h-4,3):
                off=y*frame_w
                for x in range(frame_w):
                    energy[x]+=abs(current[off+x]-previous[off+x])
        crop_w=min(frame_w,max(4,round(frame_w*(width/height)/(vw/vh))))
        total=sum(energy)
        if total < 1000:
            return 0.5
        best_x=0
        best_val=float('-inf')
        for x in range(frame_w-crop_w+1):
            # Mild centrality preference prevents unstable side jumps on noise.
            center=(x+crop_w/2)/frame_w
            value=sum(energy[x:x+crop_w]) - total*0.07*abs(center-0.5)
            if value>best_val:
                best_x,best_val=x,value
        return max(0.1,min(0.9,(best_x+crop_w/2)/frame_w))
    except (subprocess.SubprocessError, ValueError, OSError):
        return 0.5


def create_subtitles(path, title, captions, rank_names=None):
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
Style: RankName,NanumGothic,40,&H00FFFFFF,&H00FFFFFF,&H00101010,&H60000000,-1,0,0,0,100,100,0,0,1,4,1,7,15,10,10,1
Style: ActiveName,NanumGothic,44,&H0000A5FF,&H0000A5FF,&H00101010,&H60000000,-1,0,0,0,100,100,0,0,1,5,2,7,15,10,10,1
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
            label = (rank_names or {}).get(str(r), '이름 확인 필요')
            event(current,end,'ActiveName' if r==ranking else 'RankName',label,'{\\an7\\pos(175,'+str(356+(r-1)*112)+')}',3)
        event(current,end,'Caption',captions.get(name,DEFAULT_CAPTIONS[name]),'{\\an5\\pos(540,1260)}',5)
        current=end
    Path(path).write_text(''.join(lines),encoding='utf-8')

def run(cmd, timeout=300):
    print('[ffmpeg]', ' '.join(cmd[:9]), '...',flush=True)
    subprocess.run(cmd, check=True, timeout=timeout, stdout=subprocess.DEVNULL)

def render_segment(input_path, output_path, start, seconds, width=1080, height=1920, fps=24, focus_x=0.5):
    """Full-bleed 9:16 crop: no blur or smoky letterbox. Requires crop QA."""
    focus_x=max(0.0,min(1.0,float(focus_x)))
    video_w,video_h=probe_dimensions(input_path)
    viewport_fraction=(width/height)/(video_w/video_h) if video_w and video_h else 1.0
    left_frac=max(0.0,min(1.0,(focus_x-viewport_fraction/2)/(1-viewport_fraction))) if viewport_fraction < 1 else 0.5
    filter_graph=(
        f'[0:v]scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,'
        f'crop={width}:{height}:x=(iw-ow)*{left_frac:.4f}:y=(ih-oh)/2,'
        f'fps={fps},setsar=1,format=yuv420p[outv]'
    )
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',f'{start:.3f}','-i',str(input_path),
         '-filter_complex',filter_graph,'-map','[outv]','-an','-frames:v',str(round(seconds*fps)),
         '-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(output_path)],timeout=240)
    dur=probe_duration(output_path)
    if dur < seconds-0.12:
        raise RuntimeError(f'잘린 렌더 구간: {output_path}, {dur:.2f}초 / {seconds}초')

def create_transition_sfx(path, seconds=30, sample_rate=48000):
    """Original synthesized tick/pop/whoosh cues; no third-party sound samples."""
    from array import array
    import sys as _sys
    frames=array('h',[0])*(seconds*sample_rate*2)
    transitions=[0.04,2.0,7.0,12.0,17.0,22.0,27.0]
    for ix,at in enumerate(transitions):
        start=int(at*sample_rate)
        length=int((0.34 if ix in (0,6) else 0.14)*sample_rate)
        for n in range(length):
            t=n/sample_rate
            env=(1-n/length)**2
            hz=(500-280*n/length) if ix in (0,6) else (680 if n<length//2 else 920)
            val=int(5200*env*math.sin(2*math.pi*hz*t))
            j=2*(start+n)
            if j+1<len(frames):
                frames[j]=max(-32768,min(32767,frames[j]+val))
                frames[j+1]=max(-32768,min(32767,frames[j+1]+val))
    if _sys.byteorder!='little': frames.byteswap()
    with wave.open(str(path),'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(sample_rate)
        wav.writeframes(frames.tobytes())


def voiceover_timeline(dest, captions):
    """Per-shot Korean script for a licensed TTS tool; no unlicensed generated speech."""
    t=0
    lines=[]
    for name,length in SEGMENTS:
        lines.append({'segment':name,'start':t,'end':t+length,
                      'narration_suggestion':captions.get(name,DEFAULT_CAPTIONS[name]),
                      'voice_file_supplied':False})
        t+=length
    (Path(dest)/'VOICEOVER_TIMELINE.json').write_text(json.dumps(lines,ensure_ascii=False,indent=2),encoding='utf-8')
    (Path(dest)/'NARRATION_REQUIRED.md').write_text(
        '# 음성 및 게시 전 검수 안내\n\n현재 MP4에는 직접 합성한 전환 효과음만 들어 있습니다.\n'
        '한국어 TTS는 사용권이 명확한 음성 파일을 --narration 경로로 제공해야 합성됩니다.\n'
        '원본 클립의 오디오는 라이선스 불확실성을 피하려고 제거합니다.\n'
        'VOICEOVER_TIMELINE.json을 기준으로 실제 대사를 작성하고 타이밍을 검수하세요.\n'
        '모션 점수는 재미·저작권·초상권을 자동 판정하지 않습니다.\n',encoding='utf-8')
    return lines


def render_video(selected, dest, title, captions, narration=None, size='1080x1920', name_overrides=None, focus_overrides=None):
    width,height=map(int,size.lower().split('x'))
    if width <= 0 or height <= 0 or width*16!=height*9:
        raise ValueError('9:16 해상도만 허용')
    dest=Path(dest); tmp=dest/'render_tmp'; tmp.mkdir(parents=True,exist_ok=True)
    # Actual 5-ranked segments are in rank5...rank1 order. The 1st-ranked clip is the final element.
    lookup={'hook':selected[-1], 'outro':selected[-1]}
    for number,item in zip([5,4,3,2,1],selected):
        lookup[f'rank{number}']=item
    videos=[]
    shotlist=[]
    names={str(rank):source_label(item['title'],name_overrides) for rank,item in zip([5,4,3,2,1],selected)}
    for ix,(name,length) in enumerate(SEGMENTS):
        clip=lookup[name]
        duration=clip['duration']
        base=max(0.0,min(float(clip.get('highlight_start',0.0)),duration-5.2))
        if name=='hook': start=min(max(0,base+1.8),max(0,duration-2.1))
        elif name=='outro': start=min(max(0,base+1.0),max(0,duration-3.1))
        else: start=min(max(0,base),max(0,duration-length-0.1))
        seg=tmp/f'segment_{ix:02}.mp4'
        manual_focus=(focus_overrides or {}).get(clip['title'])
        focus=choose_focus_x(clip['local_path'],start,length,width,height) if manual_focus is None else float(manual_focus)
        render_segment(clip['local_path'],seg,start,length,width,height,focus_x=focus)
        shotlist.append({'segment':name,'source_title':clip['title'],'start_seconds':round(start,3),
                         'length_seconds':length,'focus_x':round(focus,3),'crop_mode':'full_bleed_no_blur',
                         'rank_label':names.get(name[-1],'') if name.startswith('rank') else '',
                         'crop_risk':clip.get('crop_risk'), 'motion_score':clip.get('motion_score'),
                         'selection_score':clip.get('selection_score'),
                         'requires_human_crop_and_action_review':True})
        videos.append(seg)
    concat=tmp/'concat.txt'
    concat.write_text(''.join("file '"+str(f.resolve()).replace("'", "'\\''")+"'\n" for f in videos),encoding='utf-8')
    joined=tmp/'joined.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(joined)])
    ass=tmp/'ranking.ass'
    create_subtitles(ass,title,captions,rank_names=names)
    (dest/'SHOTLIST_FOR_REVIEW.json').write_text(json.dumps(shotlist,ensure_ascii=False,indent=2),encoding='utf-8')
    # Original transition sounds, with optional externally licensed narration.
    sfx=tmp/'transitions.wav'
    create_transition_sfx(sfx)
    voiceover_timeline(dest,captions)
    final=dest/f'TOP5_DRAFT_REVIEW_ONLY_{width}x{height}.mp4'
    audio_inputs=['-i',str(sfx)]+(['-i',str(narration)] if narration else [])
    if narration:
        audio_filter=('[1:a]atrim=0:30,asetpts=N/SR/TB,volume=0.60[sfx];'
                      '[2:a]apad,atrim=0:30,asetpts=N/SR/TB,volume=1.0[voice];'
                      '[sfx][voice]amix=inputs=2:duration=first:normalize=0[aout]')
    else:
        audio_filter='[1:a]atrim=0:30,asetpts=N/SR/TB[aout]'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(joined),*audio_inputs,
         '-filter_complex',f'[0:v]subtitles={ass}[vout];{audio_filter}',
         '-map','[vout]','-map','[aout]','-t','30',
         '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-r','24',
         '-c:a','aac','-b:a','128k','-movflags','+faststart',str(final)],timeout=350)
    final_duration=probe_duration(final)
    if abs(final_duration-30)>0.3:
        raise RuntimeError(f'최종 영상 길이 오류: {final_duration:.2f}초')
    # Eight frames for rapid visual review of cuts, title, ranking and readability.
    try:
        run(['ffmpeg','-hide_banner','-loglevel','error','-y',
             '-i',str(final),'-vf','fps=1/4,scale=240:426,tile=4x2',
             '-frames:v','1',str(dest/'QA_CONTACT_SHEET.jpg')],timeout=90)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print('[경고] QA contact sheet extraction failed',flush=True)
    return final

def write_rights_docs(selected,out):
    out=Path(out)
    lines=['# YouTube 설명란 출처 표기 초안','', '원본을 발췌·재편집하고 한국어 순위와 자막을 추가했습니다.',
           '이 문서는 라이선스 메타데이터 기반 초안입니다. 게시 전 원권리자·음악·출연자 검토가 필요합니다.','']
    report=['# 게시 전 검토 (자동 통과 아님)','', '- [ ] 5개 원본의 원제작자 및 라이선스 검증',
            '- [ ] 원본에 삽입된 음악·음성·영상에 별도 권리 침해가 없는지 확인',
            '- [ ] 인물 초상·개인정보·동물 안전·브랜드 문제 검토',
            '- [ ] 실제 영상 30초 전체를 보고 오동작·유해 장면 검수',
            '- [ ] 허가된 한국어 TTS 파일을 추가하고 자막과 일치시켰는지 확인',
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
    parser.add_argument('--mode',choices=['discover','review','draft','local-test'],default=os.environ.get('MODE','review'))
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
    settings={}
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
        cands=discover(args.topic,count=35 if args.mode in ('draft','review') else 25)
        save_candidates(cands,out)
        if args.mode=='discover':
            print(f'검색 완료: 후보 {len(cands)}개. 출처·라이선스 검토하세요.',flush=True)
            return 0
        if len(cands)<5:
            raise RuntimeError('CC BY/CC0 영상 후보 5개 미만입니다. 주제를 변경해 다시 실행하세요.')
        selected=collect_media(cands,out,review_only=(args.mode=='review'),excluded_titles=settings.get('exclude_titles',[]))
        if args.mode=='review':
            print('[V4] 검수 결과만 출력, MP4는 검수 전 생성하지 않습니다.',flush=True)
            return 0
    write_rights_docs(selected,out)
    narration=Path(args.narration) if args.narration else None
    if narration and not narration.exists():
        raise FileNotFoundError(str(narration))
    final=render_video(selected,out,args.title,captions,narration,args.size,settings.get('source_names',{}),settings.get('focus_overrides',{}))
    print(f'렌더 완료: {final} ({probe_duration(final):.2f}초)',flush=True)
    return 0

if __name__=='__main__':
    try:
        sys.exit(cli())
    except Exception as e:
        print(f'오류: {e}',file=sys.stderr)
        sys.exit(1)