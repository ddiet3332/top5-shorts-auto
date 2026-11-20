"""Render verified-source topics with the existing V28.3/V32 production renderer."""
import argparse
import json
from pathlib import Path

from top5_auto_v29 import CUT_LENGTHS, assemble_video, save_license_and_status, technical_qa
from top5_auto_v32 import select_v32_hook, source_digest, write_rendered_hook_evidence
from top5_hook_selection import SourceShortage
from top5_reviewed_sources import select_reviewed_sources


def render_reviewed_topic(topic, output):
    output.mkdir(parents=True, exist_ok=True)
    ranked, attempts, hook_pool = select_reviewed_sources(topic, output, list(CUT_LENGTHS.values()))
    digests = [source_digest(Path(row["local_path"])) for row in ranked]
    hook, audit, hook_path = select_v32_hook(ranked, hook_pool, digests, output)
    if not audit["independent_hook"]:
        raise SourceShortage("SOURCE_SHORTAGE", "An independently reviewed hook is required")
    save_license_and_status(topic, ranked, [], attempts, output, hook)
    video = assemble_video(
        topic, ranked, output, hook, moving_ending=True,
        hook_caption=hook["caption"], hook_caption_y=1712, mobile_captions=True,
    )
    qa = technical_qa(video, output, topic, ranked)
    write_rendered_hook_evidence(video, audit, hook_path)
    qa.update(hook_mode=audit["hook_mode"], audio_listening="UNVERIFIED",
              source_permissions_fully_cleared=False, publication_approved=False)
    (output / "V32_TECHNICAL_QA.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print("V32 VIDEO COMPLETE", video, "publication = NO", flush=True)
    return video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", default="sample/top5_auto_topics_v30.json")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    topics = json.loads(Path(args.topics).read_text(encoding="utf-8"))
    topic = next((row for row in topics if row["topic_id"] == args.topic and row.get("source_catalog")), None)
    if topic is None:
        parser.error("Topic has no reviewed source catalog")
    render_reviewed_topic(topic, args.output)


if __name__ == "__main__":
    main()
