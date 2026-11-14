#!/usr/bin/env python3
"""V11: independent CC BY / CC0 candidate audition, never automatic publication.

Only files that pass the existing Wikimedia license whitelist are downloaded.
Outputs 5-second movement previews and source storyboard frames for editorial QA.
"""
from pathlib import Path
import argparse
import json
import math
import subprocess
import urllib.parse

from top5 import fetch_json, extract_candidates, short_meta, download_video, probe_duration
from v8_moments import window_candidates, moment_photo


def validate_titles(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10:
        raise ValueError("후보 목록은 1~10개 문자열이어야 합니다.")
    titles = []
    for title in rows:
        if not isinstance(title, str) or not title.startswith("File:") or len(title) > 256:
            raise ValueError("후보는 정확한 Wikimedia File: 이름을 사용해야 합니다.")
        if title.casefold() in (x.casefold() for x in titles):
            raise ValueError("후보 중복")
        titles.append(title)
    return titles


def ff(cmd, timeout=100):
    subprocess.run(cmd, check=True, timeout=timeout,
                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


def preview(path, start, secs, destination):
    vf=("scale=480:720:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=480:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=12,setsar=1")
    ff(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-ss",f"{start:.3f}","-i",str(path),"-t",f"{secs:.3f}",
        "-vf",vf,"-an","-c:v","libx264","-preset","veryfast",
        "-crf","29","-pix_fmt","yuv420p","-movflags","+faststart",
        str(destination)],timeout=90)


def review(titles, out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    videos=out/"V11_PREVIEWS"
    images=out/"V11_FRAMES"
    videos.mkdir(exist_ok=True)
    images.mkdir(exist_ok=True)
    response=fetch_json({"action":"query","format":"json","formatversion":"2",
        "titles":"|".join(titles),"prop":"imageinfo",
        "iiprop":"url|size|mime|extmetadata"})
    pages={p.get("title","").casefold():p for p in response.get("query",{}).get("pages",[])}
    allowed={c["title"].casefold():c for c in extract_candidates(response)}
    report=[]
    image_number=0
    for idx,title in enumerate(titles,1):
        entry={"requested_title":title,"editorial_status":"NEEDS_HUMAN_REVIEW",
               "rights_status":"METADATA_ONLY_NOT_VERIFIED",
               "approved_for_publication":False,"moments":[]}
        page=pages.get(title.casefold(),{})
        imageinfo=(page.get("imageinfo") or [{}])[0]
        meta=imageinfo.get("extmetadata") or {}
        entry["reported_license_name"]=short_meta(meta,"LicenseShortName")
        entry["reported_license_url"]=short_meta(meta,"LicenseUrl")
        if title.casefold() not in allowed:
            entry["status"]="EXCLUDED_UNSUPPORTED_LICENSE_OR_MEDIA"
            report.append(entry)
            print("[V11 제외]",title,entry["reported_license_name"],flush=True)
            continue
        source=allowed[title.casefold()]
        entry.update({k:source[k] for k in
                      ("source_page","author","license","license_url","source_claim","review_flags")})
        if source["size_bytes"]>45*1024*1024:
            entry["status"]="EXCLUDED_LARGE_FILE"
            report.append(entry)
            continue
        ext=Path(urllib.parse.urlparse(source["download_url"]).path).suffix.lower()
        local=videos/f"source_{idx:02d}{ext}"
        try:
            download_video(source,local)
            duration=probe_duration(local)
            if duration<5.25 or duration>600:
                raise ValueError("5초 이상 검수 가능한 영상이 아닙니다.")
            windows=window_candidates(local,duration,count=3,max_scan=65.0)
            # Alternative windows show movement, not comedic meaning.
            for j,c in enumerate(windows,1):
                start=float(c["start"])
                secs=min(5.0,duration-start-0.1)
                dest=videos/f"candidate_{idx:02d}_moment_{j}.mp4"
                preview(local,start,secs,dest)
                entry["moments"].append({"number":j,"start_sec":start,
                    "motion_score":c["motion"],"preview":str(dest.relative_to(out)),
                    "funny_action_confirmed":False})
            best=float(windows[0]["start"])
            image_number+=1
            for slot, offset in enumerate((0.4,2.5,4.6),1):
                still=images/f"{image_number:02d}_{slot}.jpg"
                moment_photo(local,min(duration-0.1,best+offset),still,width=320,height=568)
            entry["status"]="PREVIEWS_READY_NOT_APPROVED"
            entry["duration_sec"]=round(duration,2)
            entry["best_window_start_sec"]=best
            print(f"[V11 후보 {idx}] {title}: {len(windows)}개 동작 구간",flush=True)
        except Exception as e:
            entry["status"]="FAILED_DOWNLOAD_OR_DECODING"
            entry["error"]=str(e)[:160]
            print("[V11 실패]",title,str(e)[:140],flush=True)
        report.append(entry)
        local.unlink(missing_ok=True)
    for j in (1,2,3):
        # Tile each moment position across successfully decoded sources.
        success=len([x for x in report if x.get("status")=="PREVIEWS_READY_NOT_APPROVED"])
        if not success:
            break
        ff(["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate","1","-start_number","1",
            "-i",str(images/f"%02d_{j}.jpg"),
            "-vf",f"tile=3x{max(1,math.ceil(success/3))}:padding=6:margin=6:color=black",
            "-frames:v","1","-q:v","3",str(out/f"V11_STORYBOARD_{j}.jpg")],timeout=65)
    (out/"V11_CANDIDATE_REPORT.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    guide=["# V11 후보 검수 결과","",
        "시스템은 CC BY·CC0 라이선스 메타데이터를 1차 필터링할 뿐, 원작자나 제3자 권리를 최종 검증하지 않습니다.",
        "후보의 5초 영상은 모두 실제 행동·반전·맥락을 사람이 확인해야 합니다.",
        "파일 제목이 웃기다고 영상이 재미있는 것은 아닙니다.",
        "장면을 승인하기 전까지 selected-draft에 자동 채택하지 않습니다.",""]
    for item in report:
        guide.extend(["## "+item["requested_title"],"상태: "+item["status"],
             "라이선스 URL: "+item.get("reported_license_url",""),
             "미리보기: "+", ".join(x["preview"] for x in item["moments"]),""])
    (out/"V11_REVIEW_GUIDE.md").write_text("\n".join(guide),encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="output")
    parser.add_argument("--candidates",default="sample/v11-candidates.json")
    args=parser.parse_args()
    titles=validate_titles(json.loads(Path(args.candidates).read_text(encoding="utf-8")))
    report=review(titles,args.output)
    if not any(x.get("status")=="PREVIEWS_READY_NOT_APPROVED" for x in report):
        raise RuntimeError("적격 원본 미리보기를 생성하지 못했습니다. 라이선스 보고서를 확인하세요.")


if __name__=="__main__":
    main()
