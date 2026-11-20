"""Render verified-source topics with the existing V28.3/V32 production renderer."""
import argparse
import json
from pathlib import Path

from top5_auto_v29 import CUT_LENGTHS, assemble_video, save_license_and_status, technical_qa
from top5_auto_v32 import select_v32_hook, source_digest, write_rendered_hook_evidence
from top5_hook_selection import SourceShortage
from top5_reviewed_sources import select_reviewed_sources
from dog_editorial_evidence import BASELINE_SHA, LABELS, collect, shot


def render_reviewed_topic(topic, output, *, profile=None, baseline=None):
    output.mkdir(parents=True, exist_ok=True)
    # User-approved reference 1631.mp4 is the only allowed dog TOP5 visual layout.
    # Fail closed: never publish/review a white-canvas V28.3 render as design-locked.
    if topic.get("topic_id") == "dog_surprises":
        lock = json.loads(Path("sample/top5_design_lock_v1.json").read_text(encoding="utf-8"))
        if lock["version"] != "TOP5_DESIGN_LOCK_V1":
            raise RuntimeError("DESIGN_LOCK_MISSING_OR_CHANGED")
        # Render only through the user-approved full-bleed implementation.
    lengths = list(CUT_LENGTHS.values())
    segments = None
    selection_options = {}
    if profile is not None:
        segments = profile["segments"]
        if (tuple(label for label,_ in segments) != LABELS or sum(n for _,n in segments) != 30
            or any(n <= 0 for _,n in segments) or profile["baseline_sha256"] != BASELINE_SHA
            or (baseline is not None and source_digest(baseline) != BASELINE_SHA)):
            raise ValueError("INVALID_EDITORIAL_PROFILE_OR_BASELINE")
        lengths = [n for _,n in segments[1:-1]]
        selection_options = {"edits":profile["edits"],
                             "additional_sources":profile.get("additional_sources", ()),
                             "required_ids":{spec["source_id"] for spec in profile["shots"].values()}}
        if "replacement_audition" in profile:
            inventory = Path(profile["replacement_audition"]).read_text(encoding="utf-8")
            (output/"DOG_REPLACEMENT_AUDITION.json").write_text(inventory, encoding="utf-8")
    ranked, attempts, hook_pool = select_reviewed_sources(topic, output, lengths, **selection_options)
    digests = [source_digest(Path(row["local_path"])) for row in ranked]
    hook, audit, hook_path = select_v32_hook(ranked, hook_pool, digests, output)
    if not audit["independent_hook"]:
        raise SourceShortage("SOURCE_SHORTAGE", "An independently reviewed hook is required")
    options = {}
    layout = []
    if profile is not None:
        specs = profile["shots"]
        ranked = [shot(row,specs[label]) for (label,_),row in zip(segments[1:-1],ranked,strict=True)]
        hook = shot(hook,specs["hook"])
        audit["source_end_sec"] = round(hook["hook_start"]+segments[0][1]*hook["playback_rate"],3)
        ending = shot({**ranked[-1],"cut_start":profile["ending_start_sec"],"action_family":"tug",
                       "caption":profile["ending_caption"]},specs["outro"])
        options.update(segments=segments,ending_source=ending)
        start = 0
        for (label,length),row in zip(segments,[hook,*ranked,ending],strict=True):
            layout.append((label,start,length,row,specs[label]))
            start += length
    save_license_and_status(topic, ranked, [], attempts, output, hook)
    if topic.get("topic_id") == "dog_surprises":
        from top5_locked_design import render_locked
        video, _ = render_locked(topic,ranked,output,hook,ending,segments)
    else:
        video = assemble_video(
            topic, ranked, output, hook, moving_ending=True,
            hook_caption=hook["caption"], hook_caption_y=1712, mobile_captions=True, **options,
        )
    qa = technical_qa(video, output, topic, ranked)
    if topic.get("topic_id") == "dog_surprises":
        qa["rendered_design"] = "TOP5_DESIGN_LOCK_V1 / 1631.mp4"
    write_rendered_hook_evidence(video, audit, hook_path)
    qa.update(hook_mode=audit["hook_mode"], audio_listening="UNVERIFIED",
              rendered_design=("TOP5_DESIGN_LOCK_V1 / 1631.mp4" if topic.get("topic_id") == "dog_surprises" else "V28.3 white canvas and rank rail with 86pt captions"),
              source_permissions_fully_cleared=False, publication_approved=False)
    (output / "V32_TECHNICAL_QA.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    if profile is not None:
        collect(video,baseline,output,layout)
    print("V32 VIDEO COMPLETE", video, "publication = NO", flush=True)
    return video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", default="sample/top5_auto_topics_v30.json")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--editorial-profile",type=Path)
    parser.add_argument("--baseline",type=Path)
    args = parser.parse_args()
    topics = json.loads(Path(args.topics).read_text(encoding="utf-8"))
    topic = next((row for row in topics if row["topic_id"] == args.topic and row.get("source_catalog")), None)
    if topic is None:
        parser.error("Topic has no reviewed source catalog")
    profile = json.loads(args.editorial_profile.read_text(encoding="utf-8")) if args.editorial_profile else None
    render_reviewed_topic(topic, args.output,profile=profile,baseline=args.baseline)


if __name__ == "__main__":
    main()
