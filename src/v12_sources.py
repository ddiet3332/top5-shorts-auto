#!/usr/bin/env python3
"""V12 external-video source review. No scraping, no bulk downloads, no upload.

Reads explicitly curated Pexels/Pixabay/Mixkit video pages. If an *existing*
PEXELS_API_KEY secret is configured, also requests a small Pexels API shortlist.
Produces a phone-friendly review board, a CSV, and a transparent risk report.
"""
from __future__ import annotations
import argparse
import csv
import html
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request
import urllib.error

VALID={
    'pexels':{
        'host':'www.pexels.com','prefix':'/video/',
        'license':'Pexels License','license_host':'www.pexels.com',
    },
    'mixkit':{
        'host':'mixkit.co','prefix':'/free-stock-video/',
        'license':'Mixkit Stock Video Free License','license_host':'mixkit.co',
    },
    'pixabay':{
        'host':'pixabay.com','prefix':'/videos/',
        'license':'Pixabay Content License','license_host':'pixabay.com',
    },
}


def allowed_page(record):
    provider=record.get('provider')
    rules=VALID.get(provider)
    if not rules:
        return False
    p=urllib.parse.urlsplit(str(record.get('page_url','')))
    licensed=urllib.parse.urlsplit(str(record.get('license_url','')))
    path=p.path.removeprefix('/es-es') if provider=='pexels' else p.path
    if p.scheme!='https' or p.netloc!=rules['host'] or not path.startswith(rules['prefix']):
        return False
    if licensed.scheme!='https' or licensed.netloc!=rules['license_host']:
        return False
    if record.get('license_label')!=rules['license']:
        return False
    if provider=='mixkit' and not re.fullmatch(r'/free-stock-video/[^/]+-[0-9]+/?',p.path):
        return False
    if provider=='pexels' and not re.fullmatch(r'/video/[^/]+-[0-9]+/?',path):
        return False
    if provider=='pixabay' and not re.fullmatch(r'/videos/[^/]+-[0-9]+/?',p.path):
        return False
    return True


def validate_catalog(raw):
    if not isinstance(raw,list) or len(raw)>40:
        raise ValueError('후보 목록은 40개 이하여야 합니다.')
    ids=set()
    checked=[]
    for rec in raw:
        if not isinstance(rec,dict) or not rec.get('id') or not allowed_page(rec):
            raise ValueError('출처 도메인 또는 개별 영상 라이선스가 허용 기준에 맞지 않습니다.')
        if rec['id'] in ids:
            raise ValueError('후보 ID 중복')
        ids.add(rec['id'])
        # Provider-level permission is not individual authorship, original sound, or
        # YouTube reused-content clearance.
        item=dict(rec)
        item['actual_video_watched']=False
        item['source_audio_approved']=False
        item['third_party_rights_verified']=False
        item['publication_approved']=False
        item['review_status']='PAGE_FOUND_VIDEO_NEEDS_VISUAL_REVIEW'
        checked.append(item)
    return checked


def parse_pexels_results(response):
    result=[]
    for video in response.get('videos',[]):
        if not isinstance(video,dict):
            continue
        video_id=video.get('id')
        if not isinstance(video_id,int) or video_id<=0:
            continue
        duration=video.get('duration')
        if isinstance(duration,(int,float)) and (duration<5.25 or duration>180):
            continue
        page=video.get('url','')
        if not isinstance(page,str) or not re.fullmatch(
            r'https://www\.pexels\.com/video/[^/?#]+-[0-9]+/?',page):
            continue
        creator=video.get('user') or {}
        item={
            'id':f'PEXELS-API-{video_id}',
            'provider':'pexels',
            'title':f'Pexels video #{video_id} (action not yet verified)',
            'page_url':page,
            'creator':str(creator.get('name','unverified'))[:120],
            'license_label':'Pexels License',
            'license_url':'https://www.pexels.com/license/',
            'action_description':'Search result only; visually confirm what happens.',
            'review_target':'Watch 5 seconds including setup and payoff; remove weak clips.',
            'individual_page_checked':False,
            'actual_video_watched':False,
            'source_audio_approved':False,
            'third_party_rights_verified':False,
            'publication_approved':False,
            'license_review_status':'provider_terms_only',
            'asset_download_authorized':False,
            'duration_sec':duration,
        }
        if allowed_page(item):
            result.append(item)
    return result


def existing_pexels_api_search(key,query,per_page=8):
    if not isinstance(key,str) or len(key)<8:
        raise ValueError('Invalid existing Pexels API key')
    params=urllib.parse.urlencode({
        'query':query,'page':1,'per_page':min(8,max(1,per_page))
    })
    endpoint='https://api.pexels.com/v1/videos/search?'+params
    req=urllib.request.Request(endpoint,headers={
        'Authorization':key,'Accept':'application/json',
        'User-Agent':'Top5ShortsEditorialReview/1.0'
    })
    with urllib.request.urlopen(req,timeout=25) as resp:
        if resp.status!=200:
            raise RuntimeError('Pexels API did not return HTTP 200')
        data=json.load(resp)
    return parse_pexels_results(data)


def make_report(items,output,api_state):
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    fieldnames=('id','provider','title','page_url','creator','license_label',
                'license_url','action_description','review_target',
                'actual_video_watched','third_party_rights_verified',
                'source_audio_approved','publication_approved','review_status')
    with (out/'V12_SOURCES.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fieldnames,extrasaction='ignore')
        w.writeheader()
        w.writerows(items)
    (out/'V12_SOURCE_REPORT.json').write_text(
        json.dumps({'status':'NOT_APPROVED','candidate_count':len(items),
                    'pexels_api':api_state,'candidates':items},ensure_ascii=False,indent=2),
        encoding='utf-8')
    lines=['# V12 외부 영상 소스 검수 대기 목록','',
           f'출처 페이지 후보: {len(items)}개. 실제 영상 재미·원본 권리 최종 확인: **0개**.',
           f'Pexels API 상태: {api_state}.',
           '원본 다운로드나 사용 허가를 받았다는 뜻이 아닙니다.',
           'Mixkit은 개별 영상이 **Free License**인지 확인해야 하며 Restricted 사용 금지.',
           '이 목록은 페이지 URL에서 영상을 자동 추출하거나 크롤링하지 않습니다.','',
           '## 실제 편집 전에 필요한 조건','',
           '- [ ] 5초 안에 시작·행동·반전이 실제로 보임',
           '- [ ] 출처 페이지에서 해당 파일의 이용 조건 확인',
           '- [ ] 원작자·음원·제3자 권리 확인',
           '- [ ] 다른 순위 장면과 중복되지 않음',
           '- [ ] 독창적인 해설·상황 비교·평가를 추가할 수 있음',
           '- [ ] 허가되지 않은 원본 오디오를 복제하지 않음','']
    for row in items:
        lines.extend([f"### {row['title']} ({row['provider']})",
                      f"- 원본 페이지: {row['page_url']}",
                      f"- 제작자 표시: {row['creator']}",
                      f"- 제공자 라이선스: {row['license_label']}",
                      f"- 장면 검수 기준: {row['review_target']}",
                      '- **게시 승인: 아니오**',''])
    (out/'V12_RIGHTS_AND_EDITORIAL.md').write_text('\n'.join(lines),encoding='utf-8')
    def h(s): return html.escape(str(s),quote=True)
    cards='\n'.join(
        '<article><div class="provider">'+h(r['provider']).upper()+'</div>'
        '<h2>'+h(r['title'])+'</h2>'
        '<p>'+h(r['action_description'])+'</p>'
        '<small>영상 제작자: '+h(r['creator'])+'</small>'
        '<p class="warn">동작·음원·수익화 검수 전</p>'
        '<p><a href="'+h(r['page_url'])+'" target="_blank" rel="noopener noreferrer">원본 페이지에서 영상 확인 ↗</a></p>'
        '<p><a class="sub" href="'+h(r['license_url'])+'" target="_blank" rel="noopener noreferrer">해당 플랫폼 라이선스 확인</a></p>'
        '</article>' for r in items)
    page='''<!doctype html><html lang="ko"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V12 TOP5 콘텐츠 후보 검수</title>
<style>
body{margin:0;background:#111318;color:#eee;font-family:system-ui,sans-serif;line-height:1.55}
header{padding:24px 20px;background:#171a20;border-bottom:1px solid #3d4148}
main{max-width:850px;margin:auto;padding:18px}
section{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
article{border:1px solid #3d4148;border-radius:14px;padding:16px;background:#1c2027}
h1{font-size:23px;margin:0}h2{font-size:17px}p{font-size:14px}
small{color:#bec5cb}.provider{color:#fdcc74;font-size:12px;font-weight:700}
.warn{color:#eab97f}a{color:#9fd0ff}a.sub{color:#bccbd7}
</style><header><h1>V12 · 재미있는 TOP5 후보 검수</h1>
<p>페이지별 영상과 개별 라이선스를 직접 확인하는 단계. 아직 게시 승인은 0개입니다.</p>
</header><main><p>API 상태: '''+h(api_state)+'''</p>
<section>'''+cards+'''</section></main></html>'''
    (out/'V12_MOBILE_REVIEW.html').write_text(page,encoding='utf-8')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--catalog',default='sample/v12-sources.json')
    ap.add_argument('--output',default='output')
    ap.add_argument('--existing-pexels-api',action='store_true',
                    help='Use only if user already has a valid PEXELS_API_KEY secret')
    args=ap.parse_args()
    records=validate_catalog(json.loads(Path(args.catalog).read_text(encoding='utf-8')))
    api_state='NOT_CONFIGURED_NEW_KEYS_PAUSED'
    key=os.getenv('PEXELS_API_KEY','')
    if args.existing_pexels_api and key:
        api_state='REQUEST_ATTEMPTED'
        for query in ('cat jumping','funny cat'):
            try:
                more=existing_pexels_api_search(key,query)
                used={x['page_url'] for x in records}
                for row in more:
                    if row['page_url'] not in used:
                        row['review_status']='API_METADATA_NEEDS_VIDEO_REVIEW'
                        records.append(row);used.add(row['page_url'])
                api_state='WORKED_RESULT_METADATA_UNREVIEWED'
            except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as e:
                api_state='FAILED_CHECK_API_ACCESS'
                print('Pexels API call failed without exposing credentials: '+type(e).__name__,flush=True)
                break
    make_report(records,args.output,api_state)
    print(f'V12 review completed: {len(records)} source pages, 0 videos approved',flush=True)


if __name__=='__main__':
    main()
