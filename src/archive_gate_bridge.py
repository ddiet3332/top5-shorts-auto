"""Bridge verified downloaded Archive bytes into existing Gate0-3 input.

Never fabricates license evidence or treats metadata as legal approval.
"""
import argparse
import hashlib
import json
from pathlib import Path

def bridge(report, license_evidence=None):
    evidence=license_evidence or {}
    candidates=[]
    rejected=[]
    for row in report.get("results",[]):
        identifier=str(row.get("id") or "")
        if row.get("status")!="TECHNICAL_PASS_PENDING_SEMANTIC_AND_RIGHTS":
            rejected.append({"id":identifier,"reason":"NO_TECHNICAL_PASS"})
            continue
        path=Path(row.get("local_path") or "")
        if not path.is_file():
            rejected.append({"id":identifier,"reason":"MEDIA_FILE_MISSING"})
            continue
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=row.get("sha256"):
            rejected.append({"id":identifier,"reason":"MEDIA_SHA256_MISMATCH"})
            continue
        proof=evidence.get(identifier) or {}
        license_digest=proof.get("license_snapshot_sha256")
        if not isinstance(license_digest,str) or len(license_digest)!=64 or any(c not in "0123456789abcdefABCDEF" for c in license_digest):
            rejected.append({"id":identifier,"reason":"LICENSE_SNAPSHOT_REQUIRED"})
            continue
        candidates.append({"id":identifier,"provider":"internet_archive","source_url":row["source_url"],
            "creator":row["creator"],"license":proof.get("license"),
            "license_url":row["license_url"],"license_snapshot_sha256":license_digest,
            "local_path":str(path),"sha256":digest,"size_bytes":path.stat().st_size,
            "duration_sec":row["duration_sec"],"width":row["width"],"height":row["height"],
            "rights_verified":False,"publication_approved":False})
    return {"status":"CANDIDATES_FOR_GATE0_TO_GATE3_NOT_RIGHTS_APPROVED",
            "candidates":candidates,"rejected":rejected,"qualified_metadata_count":len(candidates)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--probe",required=True)
    p.add_argument("--license-evidence")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    evidence=json.loads(Path(args.license_evidence).read_text()) if args.license_evidence else {}
    report=bridge(json.loads(Path(args.probe).read_text()),evidence)
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"qualified_metadata_count":report["qualified_metadata_count"],"rejected":len(report["rejected"])}))
if __name__=="__main__":main()
