"""Capture genuine CC license snapshots for downloaded Archive candidates."""
import argparse
import json
from pathlib import Path
from .license_snapshot import snapshot_license, LicenseCaptureError

def capture(report, output_dir):
    root=Path(output_dir)
    evidence={}
    failures=[]
    for row in report.get("results",[]):
        if row.get("status")!="TECHNICAL_PASS_PENDING_SEMANTIC_AND_RIGHTS":
            continue
        identifier=str(row.get("id") or "")
        license_url=row.get("license_url") or ""
        if not license_url.startswith("https://creativecommons.org/"):
            failures.append({"id":identifier,"reason":"LICENSE_URL_NOT_CC_HTTPS"})
            continue
        try:
            proof=snapshot_license(license_url,root/(identifier[:48].replace("/","_")+".html"))
            evidence[identifier]={"license":license_url,"license_snapshot_sha256":proof["license_snapshot_sha256"],
                "license_url":license_url,"snapshot_file":proof["snapshot_file"]}
        except (LicenseCaptureError,OSError) as exc:
            failures.append({"id":identifier,"reason":type(exc).__name__})
    return {"evidence":evidence,"failures":failures,"rights_verified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--probe",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=capture(json.loads(Path(a.probe).read_text()),a.output_dir)
    Path(a.output).write_text(json.dumps(report["evidence"],indent=2)+"\n")
    print(json.dumps({"evidence_count":len(report["evidence"]),"failures":report["failures"]}))
if __name__=="__main__":main()
