"""Generate an evidence-based replacement readiness report without changing the render."""
import argparse
import json
import math
from pathlib import Path

from dog_replacement_gate import decide_replacements



RUBRIC = {
    "visible_action":25,"comedic_surprise":30,"setup_payoff_timing":20,
    "mobile_readability":15,"distinctness":10,
}


def incumbent_reviews(profile, review_path):
    """Score only fully evidenced baseline segments; no invented scores."""
    scores={"rank5":None,"rank2":None}
    blockers=[]
    if review_path is None or not Path(review_path).is_file():
        return scores,["INCUMBENT_SEGMENT_REVIEW_MISSING"]
    doc=json.loads(Path(review_path).read_text(encoding="utf-8"))
    if (doc.get("schema_version")!=1 or
        doc.get("review_kind")!="incumbent_rank_segment_scoring" or
        doc.get("rubric_version")!="dog_rank_segment_v1" or
        doc.get("publication_approved") is not False or
        doc.get("max_points")!=RUBRIC):
        raise ValueError("INVALID_INCUMBENT_SCORING_MANIFEST")
    ranks=doc.get("ranks",{})
    for rank in scores:
        row=ranks.get(rank,{})
        if row.get("source_id")!=profile.get("shots",{}).get(rank,{}).get("source_id"):
            blockers.append(rank.upper()+"_SOURCE_ID_MISMATCH")
            continue
        if row.get("reviewed_frames") is not True:
            blockers.append(rank.upper()+"_NOT_VISUALLY_SCORED")
            continue
        frames=row.get("frame_timestamps_sec",[])
        notes=row.get("review_notes")
        components=row.get("points")
        if (not isinstance(frames,list) or len(frames)<3 or
            any(not isinstance(t,(int,float)) or isinstance(t,bool) or
                not math.isfinite(t) or t<0 for t in frames) or
            not isinstance(notes,str) or len(notes.strip())<25 or
            not isinstance(components,dict) or components.keys()!=RUBRIC.keys() or
            any(not isinstance(v,(int,float)) or isinstance(v,bool) or
                not math.isfinite(v) or v<0 or v>RUBRIC[k]
                for k,v in components.items())):
            blockers.append(rank.upper()+"_SCORE_EVIDENCE_INVALID")
            continue
        scores[rank]=sum(components.values())
    return scores,blockers



def read_sample_reviewed_candidates(path):
    """Import verified visual-only rank candidates, not rights authorization."""
    if path is None or not Path(path).is_file():
        return []
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if (data.get("schema_version")!=1 or
        data.get("review_scope")!="NINE_FRAME_VISUAL_RANK5_SAMPLE_NOT_PUBLICATION_APPROVAL" or
        data.get("rubric_version")!="dog_rank_segment_v1" or
        data.get("publication_approved") is not False):
        raise ValueError("INVALID_VISUAL_REVIEW_MANIFEST")
    rows=data.get("candidates",[])
    if not isinstance(rows,list) or len(rows)!=1:
        raise ValueError("INVALID_VISUAL_CANDIDATE_COUNT")
    candidates=[]
    for row in rows:
        if (row.get("id")!="PX-5263686" or row.get("rank_target")!="rank5" or
            row.get("sha256")!="dfacbc6cc5522107bc21cd6711c9c5b07fd527959313fd0fa6469ee81c327b9b" or
            row.get("action_family")!="roll_studio" or
            row.get("rights_status")!="UNVERIFIED" or
            row.get("publication_approved") is not False or
            row.get("reviewed_frames") is not True or
            row.get("semantic_review")!="PASS"):
            raise ValueError("VISUAL_CANDIDATE_PROVENANCE_OR_RIGHTS_INVALID")
        points=row.get("visual_rubric")
        if not isinstance(points,dict) or points.keys()!=RUBRIC.keys():
            raise ValueError("VISUAL_CANDIDATE_RUBRIC_MISSING")
        if (any(not isinstance(v,(int,float)) or isinstance(v,bool) or
                not math.isfinite(v) or v<0 or v>RUBRIC[k]
                for k,v in points.items()) or
            not isinstance(row.get("editorial_score"),(int,float)) or
            row["editorial_score"]!=sum(points.values())):
            raise ValueError("VISUAL_CANDIDATE_SCORE_INVALID")
        candidates.append(row)
    return candidates


def report(profile_path: Path, audition_path: Path, provider_reports=(), incumbent_review_path=None, reviewed_candidate_path=None) -> dict:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    audition = json.loads(audition_path.read_text(encoding="utf-8"))
    fixed = {label: spec for label, spec in profile["shots"].items()
             if label not in ("rank5", "rank2", "outro")}
    used_ids = {spec["source_id"] for spec in fixed.values()}
    used_actions = {spec["action"] for spec in fixed.values()}
    candidates = {"rank5": [], "rank2": []}
    rejected = []
    for row in audition.get("candidates", []):
        # Old auditions are not clearance or editorial scores; don't invent either.
        if row.get("disposition") == "SELECTED":
            continue
        if row.get("rank_target") in candidates:
            candidates[row["rank_target"]].append(row)
        else:
            rejected.append({"id": row.get("id"), "reason": "NO_TARGET_RANK_OR_UNREVIEWED"})
    visually_reviewed = read_sample_reviewed_candidates(reviewed_candidate_path)
    for row in visually_reviewed:
        candidates[row["rank_target"]].append(row)
    reviewed_incumbents, baseline_blockers = incumbent_reviews(profile, incumbent_review_path)
    # Provider previews are only candidate discovery, never independent
    # rights clearance, verified comedy, or automatic rank assignments.
    provider_auditions = []
    provider_ready = []
    provider_new = []
    provider_cached = []
    for source in provider_reports:
        source = Path(source)
        if not source.is_file():
            continue
        try:
            feed = json.loads(source.read_text(encoding="utf-8"))
            if not isinstance(feed, dict) or not isinstance(feed.get("candidates"),list):
                raise ValueError("INVALID_PROVIDER_AUDITION")
            name = str(feed.get("provider") or source.stem)
            for item in feed["candidates"]:
                if not isinstance(item,dict):
                    continue
                row = {"provider":name, "id":item.get("id"),
                       "status":item.get("status"),
                       "preview_origin":item.get("preview_origin","NEW_THIS_RUN"),
                       "rights_status":item.get("rights_status","UNVERIFIED"),
                       "editorial_score":None,
                       "publication_approved":False}
                provider_auditions.append(row)
                if row["status"]=="PREVIEW_READY_REVIEW_REQUIRED":
                    provider_ready.append(row)
                    (provider_cached if row["preview_origin"]=="CACHED_PREVIOUS_RUN"
                     else provider_new).append(row)
        except (ValueError, OSError, TypeError):
            provider_auditions.append({"provider":source.stem,
                                       "status":"INVALID_PROVIDER_AUDITION",
                                       "publication_approved":False})
    decisions = decide_replacements(candidates, incumbent_scores=reviewed_incumbents,
                                    fixed_source_ids=used_ids, fixed_action_families=used_actions)
    return {
        "schema_version": 1,
        "design_lock": "TOP5_DESIGN_LOCK_V1",
        "incumbent_review_scores": reviewed_incumbents,
        "incumbent_review_blockers": baseline_blockers,
        "incumbent_scores_are_only_from_verified_frame_review": True,
        "candidate_count": sum(map(len, candidates.values())),
        "visually_reviewed_candidate_ids_rights_pending": [
            row["id"] for row in visually_reviewed if row["rights_status"]!="CLEARED"],
        "provider_preview_count": len(provider_ready),
        "provider_preview_new_count": len(provider_new),
        "provider_preview_cached_count": len(provider_cached),
        "provider_preview_ids_pending_review": [r["id"] for r in provider_ready],
        "provider_auditions": provider_auditions,
        "provider_preview_score_is_not_automatic": True,
        "decisions": [vars(d) for d in decisions],
        "unassigned_auditions": rejected,
        "publication_approved": False,
        "editorial_score": None,
        "next_action": ("REVIEW_UPGRADE" if any(
            d.status == "REPLACEMENT_ELIGIBLE" for d in decisions)
            else "RIGHTS_REVIEW_REQUIRED_FOR_RANK5" if any(
                d.rank=="rank5" and d.reason=="RIGHTS_REVIEW_REQUIRED"
                for d in decisions)
            else "REVIEW_NEW_PREVIEWS" if provider_new
            else "REVIEW_PENDING_PREVIEWS" if provider_ready
            else "DISCOVER_AND_REVIEW_CANDIDATES")
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", type=Path, default=Path("sample/dog_editorial_profile_v1.json"))
    p.add_argument("--audition", type=Path, default=Path("sample/dog_replacement_audition.json"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--provider-reports",type=Path,nargs="*",default=[])
    p.add_argument("--incumbent-review",type=Path,default=Path("sample/dog_incumbent_segment_review_v1.json"))
    p.add_argument("--reviewed-candidates",type=Path,default=Path("sample/dog_rank5_reviewed_candidates_v1.json"))
    a = p.parse_args()
    result = report(a.profile, a.audition, a.provider_reports, a.incumbent_review, a.reviewed_candidates)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("DOG_REPLACEMENT_STATUS", result["next_action"], flush=True)


if __name__ == "__main__":
    main()
