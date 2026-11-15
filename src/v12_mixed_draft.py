#!/usr/bin/env python3
"""V12 mixed Commons + Pexels editorial draft. Never automatic publication.

Only precisely curated Pexels pages via the official Free Download link.
Commons sources revalidate CC BY/CC0 metadata. Source audio is always disabled.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import urllib.parse

from top5 import (
    fetch_json,extract_candidates,download_video,probe_duration,crop_risk,
    render_video,write_rights_docs,DEFAULT_CAPTIONS,CLIP_MIN_SEC,CLIP_MAX_SEC,V15_SEGMENTS,V16_SEGMENTS
)
from v12_pexels_audition import download_single_pexels
from v12_sources import allowed_page


def validate_mixed_selection(rows, catalog):
    if not isinstance(rows,list) or len(rows)!=5:
        raise ValueError('Exactly five editorially selected sources are required')
    sources={x['id']:x for x in catalog if x.get('provider')=='pexels'}
    keys=[]
    validated=[]
    for row in rows:
        provider=row.get('provider')
        if provider not in ('pexels','wikimedia'):
            raise ValueError('Unknown provider')
        identity=row.get('id') if provider=='pexels' else row.get('title')
        key=(provider,identity)
        if not identity or key in keys:
            raise ValueError('Missing or duplicate source')
        keys.append(key)
        start=row.get('start_sec')
        if not isinstance(start,(int,float)) or not 0<=start<590:
            raise ValueError('start_sec outside 0..590')
        if row.get('audio_approved') is True:
            raise ValueError('V12 source audio remains disabled until separate rights approval')
        if provider=='pexels':
            if identity not in sources or not allowed_page(sources[identity]):
                raise ValueError('Pexels file must be one of curated pages with matching license metadata')
        else:
            if not str(identity).startswith('File:'):
                raise ValueError('Wikimedia source must be an exact File: title')
        if not isinstance(row.get('display_name'),str) or not row['display_name'].strip():
            raise ValueError('Each rank needs a source-accurate display name')
        validated.append(row)
    return validated


def fetch_mixed_sources(rows,catalog,out):
    out=Path(out)
    tmp=out/'clips'
    tmp.mkdir(parents=True,exist_ok=True)
    pexels={x['id']:x for x in catalog if x.get('provider')=='pexels'}
    wiki_titles=[r['title'] for r in rows if r['provider']=='wikimedia']
    indexed={}
    if wiki_titles:
        response=fetch_json({
            'action':'query','format':'json','formatversion':'2',
            'titles':'|'.join(wiki_titles),'prop':'imageinfo',
            'iiprop':'url|size|mime|extmetadata'
        })
        indexed={x['title']:x for x in extract_candidates(response)}
    selected=[]
    labels={}
    for number,row in enumerate(rows):
        local=tmp/f'mixed_{number+1:02}.mp4'
        if row['provider']=='pexels':
            meta=pexels[row['id']]
            properties=download_single_pexels(meta,local,max_bytes=50*1024*1024)
            item={
                'title':f"Pexels {meta['id']}",
                'source_page':meta['page_url'],
                'author':meta.get('creator',''),
                'license':'Pexels License',
                'license_url':meta['license_url'],
                'source_claim':'Individual page marked free to use under Pexels Content License; not Creative Commons',
                'review_flags':['original authorship check','trademarks','third-party sounds/people',
                                'video/action timing','YouTube reused-content evaluation'],
                'provider':'pexels',
                'duration':properties['duration_sec'],
                'actual_action_reviewed':True,
                'individual_rights_verified':False,
            }
        else:
            title=row['title']
            if title not in indexed:
                raise ValueError('Wikimedia license metadata failed for '+title)
            found=indexed[title]
            suffix=Path(urllib.parse.urlsplit(found['download_url']).path).suffix.lower()
            if suffix not in ('.mp4','.webm','.ogv','.ogg'):
                raise ValueError('Unknown Commons media extension')
            local=tmp/f'mixed_{number+1:02}{suffix}'
            download_video(found,local)
            item={**found, 'provider':'wikimedia', 'duration':probe_duration(local),
                  'individual_rights_verified':False}
        duration=float(item['duration'])
        start=float(row['start_sec'])
        if not CLIP_MIN_SEC<=duration<=CLIP_MAX_SEC or start+5>duration:
            raise ValueError(f'Selected 5s range invalid for {item["title"]}')
        item.update({
            'local_path':str(local),'duration':duration,
            'highlight_start':start,'crop_risk':crop_risk(local),
            'audio_approved':False, 'approved_for_publication':False,
            'editorial_selected':True,
            'reaction_sfx':row.get('reaction_sfx',''),
            'reaction_offset':row.get('reaction_offset')
        })
        selected.append(item)
        labels[item['title']]=row['display_name']
        print(f"[V12 source {number+1}/5] {item['provider']} {item['title']} -> {duration:.1f}s at {start:.1f}s",flush=True)
    return selected,labels


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',default='output')
    ap.add_argument('--sources',default='sample/v12-sources.json')
    ap.add_argument('--selection',default='sample/v12-mixed-selection.json')
    ap.add_argument('--script',default='sample/v12-mixed-script.json')
    ap.add_argument('--title',default='고양이의 예상 밖 행동 TOP5')
    ap.add_argument('--v15-pacing',action='store_true',help='3-second rank3, 6-second rank2/rank1')
    ap.add_argument('--v16-pacing',action='store_true',help='4-sec rank5 and 4-sec rank3, total 30sec')
    args=ap.parse_args()
    catalog=json.loads(Path(args.sources).read_text(encoding='utf-8'))
    rows=validate_mixed_selection(
        json.loads(Path(args.selection).read_text(encoding='utf-8')),catalog)
    notes=json.loads(Path(args.script).read_text(encoding='utf-8'))
    if notes.get('publication_approved') is True:
        raise ValueError('This workflow intentionally cannot grant publication approval')
    captions=dict(DEFAULT_CAPTIONS)
    captions.update({k:str(v)[:72] for k,v in notes.get('captions',{}).items() if k in captions})
    caption_phases=notes.get('phases',{})
    caption_phase_offsets=notes.get('phase_offsets',{})
    if not isinstance(caption_phase_offsets,dict) or any(
        key not in ('rank5','rank4','rank3','rank2','rank1')
        or type(value) not in (int,float)
        for key,value in caption_phase_offsets.items()):
        raise ValueError('Caption split offsets must be numeric seconds keyed by actual rank')
    if not isinstance(caption_phases,dict) or any(
        key not in ('rank5','rank4','rank3','rank2','rank1') for key in caption_phases):
        raise ValueError('V14 caption phases must be named by ranked segment')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    selected,labels=fetch_mixed_sources(rows,catalog,out)
    write_rights_docs(selected,out)
    mp4=render_video(selected,out,args.title,captions,
                     narration=None,size='1080x1920',name_overrides=labels,
                     caption_phases=caption_phases,
                      caption_phase_offsets=caption_phase_offsets,
                     segments=V16_SEGMENTS if args.v16_pacing else (V15_SEGMENTS if args.v15_pacing else None))
    rights={'license_check':'METADATA_ONLY','source_audio_approved':False,
            'publication_approved':False,
            'source_counts':{'pexels':sum(x['provider']=='pexels' for x in selected),
                             'wikimedia':sum(x['provider']=='wikimedia' for x in selected)},
            'individual_items':[{
                'title':item['title'],'provider':item['provider'],
                'source_url':item['source_page'],
                'reported_license':item['license'],
                'license_url':item['license_url'],
                'creator':item['author'],
                'actual_action_reviewed':item.get('actual_action_reviewed',False),
                'third_party_rights_verified':False
            } for item in selected]}
    (out/'V12_MIXED_RIGHTS_AUDIT.json').write_text(
        json.dumps(rights,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'[V12 mixed] 30s REVIEW ONLY draft created: {mp4}',flush=True)


if __name__=='__main__':
    main()
