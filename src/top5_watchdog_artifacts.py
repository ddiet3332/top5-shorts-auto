"""Inspect the three active TOP5 production entry points via GitHub Actions."""
import hashlib
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from top5_watchdog_decision import decide

WORKFLOWS = {
    "top5-ai-topic-planner.yml": ("top5-topic-plan-", "TOP5_REVIEW_1080x1920.mp4", "GENERIC_V06_QA.json"),
    "top5-production-validation.yml": ("TOP5-dog-production-validation-", "TOP5_AUTO_V29_REVIEW_1080x1920.mp4", "PUBLICATION_GATE.json"),
    "v32-dog-end-to-end.yml": ("TOP5-DOG-LIGHT-REVIEW-", "TOP5_DOG_REVIEW_360x640.mp4", "SELF_CONTAINED_QA.json"),
}


def api(route, *options):
    return subprocess.check_output(
        ["gh", "api", f"repos/{os.environ['GH_REPO']}/actions/{route}", *options], timeout=45)


def find(root, filename):
    return next(root.rglob(filename), None)


def inspect_artifact(root, video_name, qa_name):
    video, qa = find(root, video_name), find(root, qa_name)
    if not video or not qa:
        return "MP4 또는 QA 보고서 누락"
    data = json.loads(qa.read_text(encoding="utf-8"))
    if video_name == "TOP5_REVIEW_1080x1920.mp4":
        evidence = find(root, "RIGHTS_EVIDENCE.json")
        if not evidence or not find(root, "QA.md"):
            return "한국어 QA 보고서 또는 권리 증빙 누락"
        if data.get("sha256") != hashlib.sha256(video.read_bytes()).hexdigest():
            return "MP4 해시와 QA 보고서 불일치"
        if not data.get("technical_checks") or not all(data["technical_checks"].values()):
            return "MP4 기술 검사 실패"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(video),
                    "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
                   check=True, timeout=95, capture_output=True)
    result = "MP4 전체 영상·오디오 디코딩 통과, QA 보고서 확인"
    if video_name.endswith("360x640.mp4"):
        result += " (360×640 휴대폰 검토본)"
    return result


def inspect(workflow, artifact_spec):
    runs = json.loads(api(f"workflows/{workflow}/runs",
                          "-f", f"branch={os.environ['TOP5_DEFAULT_BRANCH']}", "-F", "per_page=6",
                          "-X", "GET"))["workflow_runs"]
    if not runs:
        return "실행 이력 없음"
    run = json.loads(api(f"runs/{runs[0]['id']}"))
    decision = decide([run])
    link = f"[실행 #{run['id']}]({run['html_url']})"
    if decision["action"] == "rerun_failed_jobs" and run["conclusion"] in {"timed_out", "startup_failure"}:
        api(f"runs/{run['id']}/rerun-failed-jobs", "-X", "POST")
        return f"{link} · 시간 초과 또는 시작 실패로 재시도 요청"
    if run["status"] != "completed":
        return f"{link} · 진행 중"

    prefix, video, qa = artifact_spec
    artifacts = json.loads(api(f"runs/{run['id']}/artifacts?per_page=100"))["artifacts"]
    available = [item for item in artifacts if item["name"].startswith(prefix) and not item["expired"]]
    if workflow == "top5-ai-topic-planner.yml":
        available = [item for item in available if item["name"].endswith(f"-{run['run_attempt']}")]
    if not available:
        return f"{link} · {run['conclusion']} · 현재 실행의 Artifact 없음"
    artifact = max(available, key=lambda item: item["id"])
    with TemporaryDirectory() as folder:
        root = Path(folder)
        archive = root / "review.zip"
        with archive.open("wb") as target:
            subprocess.run(["gh", "api",
                            f"repos/{os.environ['GH_REPO']}/actions/artifacts/{artifact['id']}/zip"],
                           stdout=target, check=True, timeout=90)
        subprocess.run(["unzip", "-oq", str(archive), "-d", str(root)], check=True, timeout=30)
        source_qa = find(root, "SOURCE_DOWNLOAD_QA.json")
        if source_qa and not find(root, video):
            data = json.loads(source_qa.read_text(encoding="utf-8"))
            if data["downloaded_valid_sources"] < 5:
                return f"{link} · 원본 확보 부족 ({data['downloaded_valid_sources']}/5)"
        result = inspect_artifact(root, video, qa)
        return f"{link} · {run['conclusion']} · {result}"


if __name__ == "__main__":
    lines = ["## TOP5 제작 감시", ""]
    for workflow, spec in WORKFLOWS.items():
        try:
            result = inspect(workflow, spec)
        except (subprocess.SubprocessError, OSError, ValueError, KeyError) as exc:
            result = f"결과 검증 실패 ({type(exc).__name__})"
        lines.append(f"- {workflow} · {result}")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n")
