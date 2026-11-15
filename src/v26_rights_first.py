#!/usr/bin/env python3
"""V26 rights-first entertainment source triage.

Never downloads third-party clips, bypasses preview watermark, signs licenses,
claims to verify authenticity, or publishes to YouTube. Provider statements are
potential leads, not independent frame inspection or contractual clearance.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

REQUIRED_RIGHTS=(
    "licensed","license_terms_confirmed","commercial_monetized_youtube_rights",
    "captions_and_editing_rights","shorts_thumbnail_rights",
    "territory_worldwide","agreement_term_verified",
    "all_third_party_rights_checked","signed_agreement_verified_by_human",
    "original_master_received",
)
SHA256=re.compile(r"^[0-9a-fA-F]{64}$")
OFFICIAL=re.compile(r"^/library/([0-9]+)/[a-zA-Z0-9%._~\-]+/?$")
FORBIDDEN_PUBLIC_FIELDS={
    "contract_text","contract_pdf","full_license_email","signatory_email",
    "signature_image","signed_contract_bytes","personally_identifying_email",
    "private_license_token","phone_number"
}

def validate_candidates(registry):
    if not isinstance(registry,dict) or registry.get("schema_version")!=1:
        raise ValueError("V26 registry schema version 1 required")
    items=registry.get("candidates")
    if not isinstance(items,list) or not 1<=len(items)<=20:
        raise ValueError("V26 must explicitly list 1..20 unique source candidates")
    if registry.get("default_rights",{}).get("licensed") is True:
        raise ValueError("V26 may not default every catalog source to licensed")
    seen=set()
    for item in items:
        if not isinstance(item,dict) or any(k in item for k in FORBIDDEN_PUBLIC_FIELDS):
            raise ValueError("Do not put signed contracts, contact details or secrets in public registry")
        ref=item.get("id","")
        url=item.get("url","")
        u=urlsplit(url) if isinstance(url,str) else None
        match=OFFICIAL.fullmatch(u.path) if u and u.scheme=="https" and u.netloc=="vbear.media" else None
        if not match or ref!=f"VBEAR-{match.group(1)}" or u.query or u.fragment:
            raise ValueError("Source ID must match the official VBear clip page")
        if ref in seen:
            raise ValueError("One original video cannot occupy several candidate slots")
        seen.add(ref)
        if item.get("license_scope_on_page") not in ("non-exclusive","exclusive"):
            raise ValueError("Only individually licenseable provider pages")
        if type(item.get("duration_sec")) not in (int,float) or not 3<=item["duration_sec"]<=120:
            raise ValueError("Provider-stated duration required")
        if not item.get("scene_type") or not item.get("source_claim"):
            raise ValueError("Candidate must have a source-attributed scene description")
        if item.get("rights_verified") is True or item.get("editorial_approved") is True:
            raise ValueError("Catalog cannot preapprove license or humor from marketing text")
        if item.get("preview_downloaded") is True or item.get("source_mp4_available") is True:
            raise ValueError("Provider preview/raw masters not legitimately obtained")
    return items


def validate_private_rights_record(record, item):
    """A sanity gate for locally supplied human-verified facts, NOT proof itself."""
    errors=[]
    if not isinstance(record,dict):
        return ["NO_PRIVATE_SIGNED_CONTRACT_EVIDENCE"]
    if record.get("id")!=item.get("id"):
        errors.append("WRONG_LICENSED_CLIP_ID")
    if any(k in record for k in FORBIDDEN_PUBLIC_FIELDS):
        errors.append("SENSITIVE_CONTRACT_DATA_BELONGS_IN_PRIVATE_REPOSITORY")
    errors.extend(k.upper()+"_NOT_VERIFIED" for k in REQUIRED_RIGHTS if record.get(k) is not True)
    if not isinstance(record.get("private_evidence_digest"),str) or not SHA256.fullmatch(record["private_evidence_digest"]):
        errors.append("PRIVATE_EVIDENCE_HASH_MISSING")
    if not isinstance(record.get("original_master_sha256"),str) or not SHA256.fullmatch(record["original_master_sha256"]):
        errors.append("CAMERA_ORIGINAL_SHA256_MISSING")
    if not isinstance(record.get("reviewer_alias"),str) or not record["reviewer_alias"].strip():
        errors.append("HUMAN_REVIEWER_MISSING")
    expiry=record.get("license_expires_on")
    try:
        date=dt.date.fromisoformat(expiry)
        if date<dt.date.today():
            errors.append("CONTRACT_EXPIRED")
    except (TypeError,ValueError):
        errors.append("CONTRACT_EXPIRY_NOT_DATE")
    if record.get("audio_use_allowed") is True:
        if record.get("third_party_audio_rights_verified") is not True:
            errors.append("RAW_AUDIO_NOT_CLEARED")
    return errors


def triage(registry,private_records=None):
    """Get an auditable queue. Even eligible clips remain unpublished until review."""
    items=validate_candidates(registry)
    private_records=private_records or {}
    if not isinstance(private_records,dict):
        raise ValueError("Private records must be an ID-indexed object")
    decisions=[]
    for item in items:
        record=private_records.get(item["id"])
        reasons=validate_private_rights_record(record,item)
        if item.get("video_frames_inspected") is not True:
            reasons.append("ACTUAL_RAW_VIDEO_NOT_WATCHED")
        if item.get("fully_observed_humor") is not True:
            reasons.append("SETUP_PAYOFF_NOT_OBSERVED")
        if item.get("publication_approved") is True:
            reasons.append("PREMATURE_PUBLICATION_APPROVAL")
        # Strict: catalog never grants editorial approval itself. Do not
        # silently upgrade inspected status just from a signed paper.
        stage="EVIDENCE_REVIEW_REQUIRED" if not reasons else "NOT_EDITORIAL_READY"
        decisions.append({
            "id":item["id"],
            "url":item["url"],
            "provider_description":item["source_claim"],
            "scene_type":item["scene_type"],
            "priority_rank_test":item["rank_test"],
            "license_contract_state":"REQUIRES_HUMAN_CONFIRMATION",
            "source_original_status":"NOT_VERIFIED",
            "rights_gate_reasons":reasons,
            "stage":stage,
            "may_download_unwatermarked_master":not reasons and record.get("original_master_received") is True if record else False,
            "human_comedy_score":None,
            "approved_for_publication":False
        })
    return {
        "schema_version":1,
        "baseline_version":registry.get("current_best_video",{}).get("version","V25"),
        "baseline_score":registry.get("current_best_video",{}).get("score",82),
        "candidate_count":len(decisions),
        "license_approved_automatically":0,
        "rights_ready_for_full_visual_review":sum(x["stage"]=="EVIDENCE_REVIEW_REQUIRED" for x in decisions),
        "new_source_video_rendered":False,
        "final_V26_video_100_point_score":None,
        "youtube_reused_content_monetization_approved":False,
        "publication_approved":False,
        "note":"Provider statements are not verified recordings or contracts; paid license and actual MP4 frame QA required before editing. No voiceover or TTS.",
        "candidates":decisions
    }


def write_reports(result,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    path=output/"V26_RIGHTS_AND_HUMOR_TRIAGE.json"
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    doc=["# TOP5 V26 — signed license and actual humor gate","",
         f"Baseline: **{result['baseline_version']} / {result['baseline_score']}/100** (unchanged)",
         f"Provider candidate pages: **{result['candidate_count']}**",
         "No V26 edited video yet; no provisional new 100-point score.",
         "All clips remain unlicensed and frame-unreviewed until actual proof and original MP4 are supplied.",
         "**Do not copy or crop a watermarked preview into a monetized or private review draft**.",
         "No TTS/narration; captions timed to real behavior, self-produced sound only unless expressly cleared.",
         "YouTube reused-content policy is independent of signed footage rights.",""]
    for row in result["candidates"]:
        doc.extend([f"## {row['id']} — {row['scene_type']}",
                    f"Original page: {row['url']}",
                    f"Provider-described moment (not frame inspected): {row['provider_description']}",
                    f"Proposed rank to test: {row['priority_rank_test']}",
                    f"Gate: {row['stage']}",
                    f"Outstanding: {', '.join(row['rights_gate_reasons']) or 'human contract and source QA review'}",""])
    (output/"V26_RIGHTS_AND_HUMOR_TRIAGE.md").write_text("\n".join(doc),encoding="utf-8")
    return path


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",default="sample/v26-licensed-ugc-candidates.json")
    p.add_argument("--output",default="output")
    p.add_argument("--private-rights",default=None,
                   help="Optional locally mounted, nonpublic ID-indexed evidence metadata; never commit")
    args=p.parse_args()
    catalog=json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    proof=json.loads(Path(args.private_rights).read_text(encoding="utf-8")) if args.private_rights else None
    report=triage(catalog,proof)
    write_reports(report,args.output)
    print("V26:",report["candidate_count"],"described candidates,",
          report["rights_ready_for_full_visual_review"],"evidence-ready;",
          "V25 baseline retained, no V26 video or publication approved",flush=True)


if __name__=="__main__":
    main()
