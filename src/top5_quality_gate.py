"""Quality-only 80/100 gate. Rights remain explicitly unverified, never auto-publish."""
import hashlib
from pathlib import Path

LIMITS={"hook":20,"humor_payoff":25,"ranking":15,"flow":15,"creative_captions":10,"sound":10}
def assess_quality(scorecard,technical,video):
    result={"quality_80_pass":False,"quality_score_100":None,"threshold":80,
            "rights_status":"DEFERRED_UNVERIFIED","youtube_auto_upload":False,
            "manual_upload_rights_warning":True}
    p=Path(video)
    if not p.is_file() or technical.get("technical_pass") is not True:
        result["reason"]="selected_video_missing_or_technical_defects"
        return result
    if scorecard.get("full_av_review_complete") is not True:
        result["reason"]="full_audiovisual_editorial_review_missing"
        return result
    dimensions=scorecard.get("dimensions",{})
    if not isinstance(dimensions,dict) or any(type(dimensions.get(k)) not in (int,float)
            or not 0<=dimensions[k]<=mx for k,mx in LIMITS.items()):
        result["reason"]="invalid_or_missing_quality_dimensions"
        return result
    digest=hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""): digest.update(block)
    if digest.hexdigest()!=scorecard.get("reviewed_video_sha256"):
        result["reason"]="review_evidence_does_not_match_selected_video"
        return result
    # Rights/money dimension (5 points) receives zero until independently reviewed.
    score=sum(dimensions[k] for k in LIMITS)
    result.update({"quality_score_100":score,"quality_80_pass":score>=80,
                   "quality_review_verified":True,
                   "rights_monetization_points":0,
                   "reason":"quality_80_verified_rights_deferred" if score>=80 else "quality_below_80_reedit"})
    return result
