#!/usr/bin/env python3
"""V19 source-diverse, small, rights-aware cat footage audition.

No scraping of stock platform pages. Individual public asset page/license
observations are manually curated in sample/v19-curated-external.json.
Only THREE explicit Pexels IDs are tested by their existing official single
asset download endpoint; other providers remain page-link-only until their
individual source and download rights are cleared.
"""
from __future__ import annotations
import argparse
import csv
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from v12_sources import allowed_page

ALLOWED_PEXELS_IDS = frozenset({"PX-7680667","PX-6853903","PX-6853188"})
MIXKIT_RESTRICTED_EXAMPLES = frozenset({
    "https://mixkit.co/free-stock-video/kitten-playing-with-ball-6999/",
    "https://mixkit.co/free-stock-video/young-cats-play-in-the-garden-14184/",
    "https://mixkit.co/free-stock-video/kitten-hiding-outside-26381/",
    "https://mixkit.co/free-stock-video/kitten-playing-in-the-couch-6954/",
})
LIC_URL = {
    "pexels":"https://www.pexels.com/license/",
    "mixkit":"https://mixkit.co/license/modal/videoFree/",
    "pixabay":"https://pixabay.com/service/license-summary/",
}
STATE_NOTE = {
    "pexels":"Pexels single-item official free download audition, if selected.",
    "mixkit":"Individual Free License text observed; NO automatic video extraction.",
    "pixabay":"Provider Content License observed, AI/repost risk unresolved, NO auto download.",
}


def validate_catalog(items):
    if not isinstance(items,list) or not 5 <= len(items) <= 15:
        raise ValueError("V19 requires 5..15 individually curated source pages")
    seen_id=set()
    seen_url=set()
    audited=[]
    pexels_for_preview=0
    for raw in items:
        if not isinstance(raw,dict) or not allowed_page(raw):
            raise ValueError("Invalid provider/source page or license metadata")
        provider=raw["provider"]
        url=raw["page_url"]
        if url in MIXKIT_RESTRICTED_EXAMPLES:
            raise ValueError("MIXKIT_RESTRICTED_LICENSE: commercial use prohibited")
        if raw.get("license_url")!=LIC_URL.get(provider):
            raise ValueError("Provider license URL must be precise, no restricted substitutions")
        if raw.get("individual_page_checked") is not True:
            raise ValueError("The exact individual page must first be reviewed")
        if raw.get("rights_evidence_status") != "individual_public_page_license_text_checked_not_rights_cleared":
            raise ValueError("Exact page-license evidence label is required")
        if not re.fullmatch(r"20[2-9][0-9]-[01][0-9]-[0-3][0-9]",
                            str(raw.get("license_checked_on",""))):
            raise ValueError("Specific license verification date missing")
        if raw.get("actual_video_watched") is True or raw.get("publication_approved") is True:
            raise ValueError("Catalog metadata cannot authorize video/rights review")
        if raw.get("source_audio_approved") is True or raw.get("third_party_rights_verified") is True:
            raise ValueError("Catalog cannot clear third-party/source audio rights")
        asset_id=raw.get("id")
        if not isinstance(asset_id,str) or asset_id in seen_id or url in seen_url:
            raise ValueError("Duplicate or missing curated asset")
        prefix={"pexels":"PX-","mixkit":"MK-","pixabay":"PB-"}[provider]
        if not asset_id.startswith(prefix):
            raise ValueError("Provider prefix mismatch")
        m=re.search(r"-(\d+)/?$",urlsplit(url).path)
        if not m or asset_id != prefix+m.group(1):
            raise ValueError("ID and official item-page ID mismatch")
        audit_action=raw.get("audit_action")
        if audit_action not in ("pexels_official_single_video_preview","page_only_review"):
            raise ValueError("No arbitrary downloads permitted")
        if audit_action=="pexels_official_single_video_preview":
            if provider!="pexels" or asset_id not in ALLOWED_PEXELS_IDS:
                raise ValueError("Only three explicitly curated Pexels items may auto-download")
            pexels_for_preview+=1
        if pexels_for_preview>3:
            raise ValueError("Maximum three small preview source downloads")
        seen_id.add(asset_id)
        seen_url.add(url)
        row=dict(raw)
        row.update({"actual_video_watched":False,
                    "individual_rights_verified":False,
                    "third_party_rights_verified":False,
                    "source_audio_approved":False,
                    "publication_approved":False,
                    "youtube_reused_content_cleared":False,
                    "review_status":"PAGE_LICENSE_EVIDENCE_ONLY_SOURCE_FOOTAGE_UNREVIEWED"})
        audited.append(row)
    return audited


def make_board(items, audition_rows, out, *, audition_enabled):
    out=Path(out)
    out.mkdir(exist_ok=True,parents=True)
    by_id={x["id"]:x for x in audition_rows}
    rows=[]
    for item in items:
        detail=by_id.get(item["id"])
        prepared=dict(item)
        prepared["video_preview_status"]=(detail.get("editorial_status","NOT_REVIEWED")
                                         if detail else "PAGE_LINK_ONLY")
        prepared["preview_windows"]=(detail.get("windows",[]) if detail else [])
        prepared["video_preview_failure_type"]=(detail.get("failure_type") if detail else None)
        prepared["actual_video_watched"]=False  # Full human visual QA pending
        prepared["publication_approved"]=False
        rows.append(prepared)
    report={
        "schema_version":1,
        "mode":"V19_SOURCE_DIVERSE_REVIEW_ONLY",
        "status":"AWAITING_EDITORIAL_AND_RIGHTS_QA",
        "candidate_page_count":len(rows),
        "provider_counts":{key:sum(x["provider"]==key for x in rows)
                           for key in ("pexels","mixkit","pixabay")},
        "actual_pexels_source_previews_created":sum(
            bool(x["preview_windows"]) for x in rows),
        "video_previews_created":sum(len(x["preview_windows"]) for x in rows),
        "three_item_pexels_audition_enabled":audition_enabled,
        "all_rights_approved":False,
        "publication_approved":False,
        "candidates":rows,
        "notes":[
            "No automated Mixkit/Pixabay downloading or page scraping.",
            "Individual page licenses do not verify the author, music, faces or YouTube monetization.",
            "Stock footage edited into a simple countdown may still fail reused-content monetization.",
            "A candidate page being found is not proof a comedic action is visible."
        ]
    }
    (out/"V19_SOURCE_DIVERSE_AUDIT.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (out/"V19_REVIEW_QUEUE.csv").open("w",newline="",encoding="utf-8-sig") as f:
        columns=("id","provider","title","page_url","creator","license_label",
                 "license_url","license_checked_on","video_preview_status",
                 "actual_video_watched","publication_approved","review_goal")
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        w.writeheader();w.writerows(rows)
    lines=["# TOP5 V19 — 개별 페이지 기반 다중 소스 검수","",
           f"페이지 후보: **{len(rows)}개**",
           f"실제 미리보기 생성 원본: **{report['actual_pexels_source_previews_created']}개**",
           "최종 TOP5 채택: **0개** — 실제 5초 재생·권리 검수 전",
           "자동 Pexels 소수 미리보기 이외 외부 플랫폼 동영상 다운로드 없음.",
           "Mixkit Restricted License 비상업 이용만 허용. Free License를 개별 영상마다 확인.",
           "Pixabay의 AI 생성·리포스트 영상은 추가 원본 확인 전 사용 금지.",
           "모든 외부 원본의 음악/제3자 권리 및 YouTube 재사용 콘텐츠 검토 필요.",""]
    cards=[]
    for i,row in enumerate(rows,1):
        status=row["video_preview_status"]
        lines += [f"## {i}. {row['title']} ({row['provider']})",
                  f"- URL: {row['page_url']}",
                  f"- 라이선스 확인: {row['license_label']} / {row['license_checked_on']}",
                  f"- 원본 재생 검수: 미완료, 자동 미리보기 상태: {status}",
                  f"- 목적: {row['review_goal']}", ""]
        es=lambda t:html.escape(str(t),quote=True)
        previews=", ".join(w.get("preview_file","") for w in row["preview_windows"])
        cards.append(
            '<article><h2>'+es(row["title"])+'</h2>'
            '<p class="meta">'+es(row["provider"].upper())+' · '+es(row["license_label"])+'</p>'
            '<p>'+es(row.get("action_description_page",""))+'</p>'
            '<p><b>실제 영상 확인: 필요</b> / '+es(status)+'</p>'
            ('<p>미리보기 파일: '+es(previews)+'</p>' if previews else '')
            +'<p><a href="'+es(row["page_url"])+'" target="_blank" rel="noopener noreferrer">원본 개별 페이지</a>'
            ' · <a href="'+es(row["license_url"])+'" target="_blank" rel="noopener noreferrer">이용 조건</a></p>'
            '</article>'
        )
    (out/"V19_EDITORIAL_QUEUE.md").write_text("\n".join(lines),encoding="utf-8")
    page="""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>V19 TOP5 source review</title><style>
body{background:#0e1116;color:#f6f6f6;font-family:system-ui;margin:0;line-height:1.5}
header{padding:20px;background:#1d2630}main{max-width:900px;margin:auto;padding:16px}
section{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
article{padding:16px;border:1px solid #454f5a;border-radius:12px;background:#1b232c}
h1{font-size:22px}h2{font-size:17px}.meta{color:#a8c5dc;font-size:13px}
p{font-size:14px}a{color:#aee1fa}aside{color:#ffc878}</style></head><body>
<header><h1>V19 · TOP5 고양이 다중 소스 검수</h1>
<p>페이지 정보 ≠ 동작 확인 ≠ 저작권 승인 ≠ 수익화 승인</p></header>
<main><aside>전체 후보는 미검수·미승인. Mixkit Restricted는 제외. Pixabay 원본 진정성 확인 전 사용 금지.</aside>
<section>"""+ "\n".join(cards) +"</section></main></body></html>"
    (out/"V19_PHONE_REVIEW.html").write_text(page,encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",default="sample/v19-curated-external.json")
    p.add_argument("--output",default="output")
    p.add_argument("--pexels-audition",action="store_true")
    args=p.parse_args()
    items=validate_catalog(json.loads(Path(args.catalog).read_text(encoding="utf-8")))
    selected=[x for x in items if x.get("audit_action")=="pexels_official_single_video_preview"]
    audition_rows=[]
    if args.pexels_audition and selected:
        from v12_pexels_audition import audition
        audition_rows=audition(selected,Path(args.output)/"V19_PEXELS",max_candidates=3)
    result=make_board(items,audition_rows,Path(args.output),audition_enabled=args.pexels_audition)
    print(f"V19 page review={result['candidate_page_count']} / video previews="
          f"{result['video_previews_created']} / publish approvals=0")


if __name__=="__main__":
    main()
