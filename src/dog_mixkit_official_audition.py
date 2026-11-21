"""Attempt official, explicitly-linked Mixkit Free downloads from three curated pages.

Do not guess undocumented download endpoints or scrape in bulk. Only direct
download anchors actually present in the official page may be followed.
Restricted/unknown license videos are never requested. Preview remains
unreviewed, commercial right/YouTube monetization never automatically granted.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from urllib.parse import urljoin,urlsplit
import urllib.request
from v12_pexels_audition import make_five_second_preview, safe_failure_code
from v8_moments import moment_photo
from dog_mixkit_license_screen import screen_catalog

MAX_PAGE_BYTES = 768 * 1024
MAX_VIDEO_BYTES = 45 * 1024 * 1024
OFFICIAL_HOSTS = {"mixkit.co","assets.mixkit.co","videos.mixkit.co","cdn.mixkit.co"}


class DirectLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.anchors=[]
        self.active=None

    def handle_starttag(self,tag,attrs):
        if tag=="a":
            item=dict(attrs)
            self.active={"href":item.get("href"),
                         "download_attr":"download" in item,
                         "words":[]}

    def handle_data(self,data):
        if self.active is not None:
            self.active["words"].append(data.strip())

    def handle_endtag(self,tag):
        if tag=="a" and self.active is not None:
            self.anchors.append(self.active)
            self.active=None


def select_explicit_download_link(source_url, html):
    if "Mixkit Stock Video Free License" not in html or "Download Free Video" not in html:
        raise ValueError("FREE_LICENSE_PAGE_NOT_CONFIRMED")
    parser=DirectLinks()
    parser.feed(html)
    for anchor in parser.anchors:
        href=anchor["href"]
        if not isinstance(href,str) or not href:
            continue
        text=" ".join(anchor["words"]).casefold()
        if not (anchor["download_attr"] or "download free video" in text):
            continue
        url=urljoin(source_url,href)
        p=urlsplit(url)
        if (p.scheme!="https" or p.hostname not in OFFICIAL_HOSTS or
            p.username or p.password or p.port not in (None,443) or
            not p.path.lower().endswith(".mp4") or
            "/preview/" in p.path.lower()):
            continue
        return url
    return None


def read_official_page(source_url, *, opener=None):
    opener=opener or urllib.request.urlopen
    req=urllib.request.Request(source_url,headers={
        "User-Agent":"TOP5-Curated-Editorial-Review/1.0",
        "Accept":"text/html"})
    with opener(req,timeout=18) as response:
        final=urlsplit(response.geturl())
        original=urlsplit(source_url)
        if final.scheme!="https" or final.hostname!="mixkit.co" or final.path!=original.path:
            raise ValueError("MIXKIT_OFFICIAL_PAGE_REDIRECT")
        if "text/html" not in response.headers.get("Content-Type","").lower():
            raise ValueError("MIXKIT_NOT_HTML")
        body=response.read(MAX_PAGE_BYTES+1)
        if len(body)>MAX_PAGE_BYTES:
            raise ValueError("MIXKIT_HTML_TOO_LARGE")
    return body.decode("utf-8",errors="replace")


def official_video_download(url,target,*,opener=None):
    opener=opener or urllib.request.urlopen
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname not in OFFICIAL_HOSTS or not p.path.endswith(".mp4"):
        raise ValueError("UNTRUSTED_MEDIA_DOWNLOAD_URL")
    temp=target.with_suffix(".part")
    try:
        with opener(urllib.request.Request(url,headers={
                "User-Agent":"TOP5-Curated-Editorial-Review/1.0",
                "Accept":"video/mp4,application/octet-stream;q=0.8"}),timeout=40) as response:
            final=urlsplit(response.geturl())
            if final.scheme!="https" or final.hostname not in OFFICIAL_HOSTS:
                raise ValueError("UNTRUSTED_MIXKIT_MEDIA_REDIRECT")
            media_type=response.headers.get("Content-Type","").lower()
            if not ("video/" in media_type or "application/octet-stream" in media_type):
                raise ValueError("NOT_VIDEO_RESPONSE")
            declared=response.headers.get("Content-Length")
            if declared and int(declared)>MAX_VIDEO_BYTES:
                raise ValueError("MEDIA_SIZE_CAP")
            size=0
            with temp.open("wb") as out:
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:
                        break
                    size+=len(chunk)
                    if size>MAX_VIDEO_BYTES:
                        raise ValueError("MEDIA_SIZE_CAP")
                    out.write(chunk)
        if size<50000:
            raise ValueError("MEDIA_TOO_SMALL")
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)


def probe_duration(source):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=noprint_wrappers=1:nokey=1",str(source)],
                     capture_output=True,text=True,check=True,timeout=20)
    return float(p.stdout.strip())


def audit_mixkit(catalog,output,*,reader=None,downloader=None,probe=None,previewer=None,image_maker=None):
    screened=screen_catalog(catalog)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    reader=reader or read_official_page
    downloader=downloader or official_video_download
    probe=probe or probe_duration
    previewer=previewer or make_five_second_preview
    image_maker=image_maker or moment_photo
    records=[]
    for item in screened["free_license_page_candidates"][:3]:
        sid=item["id"]
        row={"id":sid,"provider":"mixkit","source_url":item["source_url"],
             "license_class":"FREE","rank_target":item["rank_target"],
             "status":"NOT_TESTED","rights_status":"UNVERIFIED",
             "semantic_review":"UNVERIFIED","reviewed_frames":False,
             "editorial_score":None,"publication_approved":False}
        source=output/(sid+"_temp_original.mp4")
        preview=output/(sid+"_preview.mp4")
        frames=[output/(sid+f"_frame{i}.jpg") for i in range(3)]
        try:
            html=reader(item["source_url"])
            link=select_explicit_download_link(item["source_url"],html)
            if link is None:
                row["status"]="OFFICIAL_BROWSER_DOWNLOAD_REQUIRED"
            else:
                downloader(link,source)
                duration=float(probe(source))
                if not 5.3<=duration<=90:
                    raise ValueError("MIXKIT_SOURCE_DURATION_INVALID")
                start=min(max(0.0,duration/2-2.5),duration-5.1)
                previewer(source,start,preview)
                if not preview.is_file() or preview.stat().st_size<2000:
                    raise ValueError("MIXKIT_PREVIEW_INVALID")
                for offset,frame in zip((0.5,2.5,4.5),frames):
                    image_maker(source,start+offset,frame)
                    if not frame.is_file() or frame.stat().st_size==0:
                        raise ValueError("MIXKIT_FRAME_INVALID")
                row.update({"status":"PREVIEW_READY_REVIEW_REQUIRED",
                            "preview_file":preview.name,
                            "frame_files":[f.name for f in frames],
                            "source_duration_sec":round(duration,2),
                            "preview_start_sec":round(start,2)})
        except Exception as exc:
            row["status"]="MIXKIT_FETCH_OR_REVIEW_FAILED"
            row["failure_code"]=safe_failure_code(exc)
            row["failure_type"]=type(exc).__name__
            preview.unlink(missing_ok=True)
            for frame in frames:
                frame.unlink(missing_ok=True)
        finally:
            source.unlink(missing_ok=True)
        records.append(row)
        print("MIXKIT_OFFICIAL_AUDITION",sid,row["status"],flush=True)
    results={"provider":"mixkit","status":"PREVIEW_READY" if any(
             x["status"]=="PREVIEW_READY_REVIEW_REQUIRED" for x in records)
             else "NO_PREVIEW","candidates":records,
             "restricted_ids_blocked":[x["id"] for x in screened["commercially_blocked"]],
             "publication_approved":False,"rights_status":"UNVERIFIED",
             "source_audio_approved":False,
             "note":"Only official explicit download links, never hidden endpoints or access controls."}
    (output/"DOG_MIXKIT_OFFICIAL_AUDITION.json").write_text(
        json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return results


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--catalog",type=Path,
                   default=Path("sample/dog_mixkit_license_screen_v1.json"))
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=audit_mixkit(a.catalog,a.output)
    print("DOG_MIXKIT_FINAL",r["status"],len(r["candidates"]),flush=True)


if __name__=="__main__":
    main()
