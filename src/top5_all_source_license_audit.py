#!/usr/bin/env python3
"""Audit *all* visual third-party sources, including the independent hook.

Web-observed license/author fields are not legal clearance, grant of commercial
rights from every possible party, YouTube originality approval, or an 85 score.
Unknown or mismatching origin bytes always stay unresolved.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OBSERVATIONS=ROOT/"review/top5_source_license_observations.json"
VIDEO="TOP5_AUTO_V29_REVIEW_1080x1920.mp4"

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def collect_visual_sources(out):
    out=Path(out)
    provenance=load(out/"SELECTED_SOURCE_PROVENANCE.json")
    ranking=provenance.get("selected")
    if (not isinstance(ranking,list) or len(ranking)!=5 or
        [x.get("rank") for x in ranking]!=[5,4,3,2,1] or
        provenance.get("publication_approved") is not False):
        raise ValueError("FIVE_RANKS_AND_UNAPPROVED_PROVENANCE_REQUIRED")
    rows=[]
    for rank in ranking:
        if (not isinstance(rank.get("sha256"),str) or len(rank["sha256"])!=64
            or not str(rank.get("source_page","")).startswith("https://")
            or rank.get("rights_verified") is not False
            or rank.get("publication_approved") is not False):
            raise ValueError("BAD_RANK_SOURCE_PROVENANCE")
        rows.append({"role":f"rank_{rank['rank']}","sha256":rank["sha256"],
                     "source_page":rank["source_page"]})
    hook=load(out/"INDEPENDENT_HOOK_AUDIT.json")
    if (hook.get("status")!="HOOK_RENDER_VERIFIED" or
        hook.get("publication_approved") is not False or
        hook.get("rights_verified") is not False):
        raise ValueError("HOOK_PROVENANCE_INVALID")
    if hook.get("rendered_video_sha256")!=sha(out/VIDEO):
        raise ValueError("HOOK_FOR_DIFFERENT_MP4")
    mode=hook.get("hook_mode")
    if mode=="independent_source":
        if (hook.get("independent_hook") is not True or
            not str(hook.get("source_page","")).startswith("https://") or
            not isinstance(hook.get("sha256"),str) or len(hook["sha256"])!=64):
            raise ValueError("BAD_INDEPENDENT_HOOK_PROVENANCE")
        rows.append({"role":"hook_0_2sec","sha256":hook["sha256"],
                     "source_page":hook["source_page"]})
    elif mode in ("nonoverlapping_rank_source","reused_rank_source"):
        if hook.get("sha256") not in [r["sha256"] for r in ranking]:
            raise ValueError("HOOK_REUSE_SOURCE_NOT_IN_RANKS")
    else:
        raise ValueError("UNRECOGNIZED_HOOK_SOURCE_MODE")
    if len({row["sha256"] for row in rows})!=len(rows):
        raise ValueError("DUPLICATE_SOURCE_SHA")
    return rows

def audit(output,observations=DEFAULT_OBSERVATIONS):
    output=Path(output)
    sources=collect_visual_sources(output)
    observed=load(observations)
    entries=observed.get("sources")
    if not isinstance(entries,list):
        raise ValueError("INVALID_OBSERVATION_CATALOG")
    index={}
    for x in entries:
        if not (isinstance(x,dict) and isinstance(x.get("sha256"),str)
                and len(x["sha256"])==64):
            raise ValueError("BAD_LICENSE_OBSERVATION")
        if x["sha256"] in index:
            raise ValueError("DUPLICATE_LICENSE_OBSERVATION_SHA")
        index[x["sha256"]]=x
    result=[]
    for source in sources:
        match=index.get(source["sha256"])
        good=bool(match and
            match.get("source_page")==source["source_page"] and
            match.get("source_page_license_observed") is True and
            match.get("owner_authorization_independently_verified") is False and
            match.get("third_party_rights_verified") is False and
            match.get("youtube_reused_content_verified") is False and
            match.get("publication_approved") is False and
            all(isinstance(match.get(key),str) and match[key].strip()
                for key in ("creator","license","license_url")))
        result.append({**source,
            "source_page_metadata_observed":good,
            "creator":match["creator"] if good else None,
            "license":match["license"] if good else None,
            "license_url":match["license_url"] if good else None,
            "attribution_required":match["attribution_required"] if good else None,
            "share_alike_review_required":match["share_alike_review_required"] if good else None,
            "rights_independently_verified":False,
            "publication_approved":False})
    unknown=[r["role"] for r in result if not r["source_page_metadata_observed"]]
    share_alike=[r["role"] for r in result if r["share_alike_review_required"] is True]
    report={
      "schema_version":1,
      "status":"PAGE_LICENSE_OBSERVATIONS_REVIEW_ONLY" if not unknown else "MISSING_OR_MISMATCHED_SOURCE_LICENSE_OBSERVATIONS",
      "rank_count":5,
      "independent_hook_included":any(x["role"]=="hook_0_2sec" for x in sources),
      "unique_visual_source_count":len(sources),
      "source_page_metadata_observed_count":len(sources)-len(unknown),
      "unobserved_source_roles":unknown,
      "share_alike_legal_review_roles":share_alike,
      "items":result,
      "source_rights_independently_verified":False,
      "third_party_rights_verified":False,
      "youtube_reused_content_monetization_verified":False,
      "final_editorial_score_100":None,
      "publication_approved":False,
      "automatic_upload_disabled":True,
      "notice":"Source-page license observations and authorship labels are not complete copyright permission, releases or YouTube monetization approval."
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/"TOP5_ALL_SOURCE_LICENSE_AUDIT.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    credits=["# TOP5 원본 영상 출처 — 유튜브 설명란 삽입 검토용","",
      "원본 발췌·재배치, 순위 및 한국어 창작 자막, 자체 합성 효과음/음악을 추가한 검수용 편집본입니다.",
      "아래 출처 표시 초안은 게시 허가 또는 유튜브 수익화 승인을 뜻하지 않습니다.",""]
    for row in result:
        role="오프닝(0~2초)" if row["role"]=="hook_0_2sec" else row["role"].replace("rank_","") + "위"
        if row["source_page_metadata_observed"]:
            credits.extend([f"- {role}: {row['creator']} | {row['source_page']}",
                            f"  라이선스: {row['license']} ({row['license_url']})",
                            "  변경: 구간 발췌·화면 재배치·창작 자막·효과음 추가"])
        else:
            credits.extend([f"- {role}: 출처 메타데이터 미확인 — 게시 금지",
                            f"  원본: {row['source_page']}"])
    credits.extend(["", "주의: CC BY-SA 자료가 포함되면 각색물의 동일조건변경허락 적용 범위를 게시 전에 확인하세요.",
      "Pexels는 무료 상업 이용과 수정 사용을 일반적으로 허용하지만 원본 권한·제3자 권리와 YouTube 재사용 콘텐츠 적합성은 별도 문제입니다.",
      "게시 상태: 보류. 실제 권리 확인, 크리에이티브 독창성 검수, 85/100 이상 실질 평가 필요."])
    (output/"TOP5_SOURCE_CREDITS_COPY_DRAFT_KO.md").write_text(
        "\n".join(credits)+"\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--observations",type=Path,default=DEFAULT_OBSERVATIONS)
    args=p.parse_args()
    result=audit(args.output,args.observations)
    print(json.dumps({k:result[k] for k in
        ("status","unique_visual_source_count","independent_hook_included",
        "source_page_metadata_observed_count","unobserved_source_roles","publication_approved")},
        ensure_ascii=False))
if __name__=="__main__":
    main()
