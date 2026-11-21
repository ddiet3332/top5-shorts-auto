#!/usr/bin/env python3
"""V31: compare 8 real frames per rank with English video-action phrases.

X-CLIP (MIT, trained on Kinetics-400) gives relative text-video compatibility,
NOT verified action, joke quality, copyright ownership, or YPP approval.
No paid API. No video modification. Never publish automatically.
"""
from __future__ import annotations
import argparse,io,json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image

MODEL="microsoft/xclip-base-patch32"
RANKS=[(5,2.,6.),(4,6.,11.),(3,11.,15.),(2,15.,21.),(1,21.,27.)]
# The first English description is the expected subject/action.
# Other descriptions are deliberately plausible alternatives.
SCENES=[
 (("소파","sofa","34689563"),[
 "A white cat hides under a sofa then reaches out to grab a pink toy.",
 "A white cat sleeps motionless under a sofa.",
 "A white cat calmly walks past a sofa without playing.",
 "An empty sofa with no cat underneath."]),
 (("구르기","rolling","40826295"),[
 "A video of a cat rolling and playing on its back on a sidewalk.",
 "A video of a cat sitting still on a city sidewalk.",
 "A video of a cat walking straight along a sidewalk.",
 "A video of a sidewalk without any animals."]),
 (("bag","쇼핑백"),[
 "A video of a cat playing inside a paper shopping bag.",
 "A video of a cat sitting quietly next to a shopping bag.",
 "A video of a cat walking slowly across a floor.",
 "A video of an empty shopping bag without a cat."]),
 (("cotton","면봉","moomin"),[
 "A video of a cat playing with a cotton swab held by a human hand.",
 "A video of a cat sitting still on a chair.",
 "A video of a cat walking quietly past a person.",
 "A video of an empty table without a cat."]),
 (("둘","larry","chloé","two cats"),[
 "A video of two cats actively playing together.",
 "A video of two cats sitting quietly next to each other.",
 "A video of only one cat resting inside a house.",
 "A video of an empty room without cats."]),
 (("풀숲","grass","zeitlupe"),[
 "A video of a white cat running or jumping over a grassy area.",
 "A video of a cat sitting quietly in green grass.",
 "A video of a person walking through green grass.",
 "A video of an empty grassy field without animals."]),
 (("건물","rooftop","salto","roof"),[
 "A video of a cat leaping through the air between two rooftops.",
 "A video of a cat walking slowly on a rooftop.",
 "A video of a cat sitting still on a rooftop.",
 "A video of buildings with no animals in the picture."]),
 (("pigeon","비둘기"),[
 "A video of a cat chasing a pigeon in a street.",
 "A video of a cat walking alone in a street.",
 "A video of a pigeon standing alone in a street.",
 "A video of an empty street with no animals."]),
 (("jump","도약"),[
 "A video of a cat jumping through the air.",
 "A video of a cat sitting completely still.",
 "A video of a cat walking slowly.",
 "A video of an empty outdoor scene with no animal."])
]
FALLBACK=[
 "A video of a cat moving quickly or jumping.",
 "A video of a cat sitting quietly.",
 "A video of a cat walking slowly.",
 "A video of a room without cats."]

# Deliberately conservative subject hypotheses from original filenames.
# A matching *title* only defines a question for the model, never certifies
# that the selected 6-second frames actually depict the described event.
SUPPORTED_TOPICS = {"cat_surprises", "dog_surprises", "human_moments",
                    "objects_oddities", "nature_moments"}

# The expected action competes with *specific* alternative interpretations,
# rather than assuming that a stock title proves something happened on-screen.
# Coarse categories below are hints only; relative logits are not calibrated.
GENERIC_SCENES=[
    (("geyser", "strokkur"),[
        "A natural geyser erupts upward with a visible plume of water.",
        "Steam hangs over a landscape without a water eruption.",
        "A wide static rocky landscape without a visible geyser.",
        "A city street scene with buildings and no geyser."]),
    (("flood", "flooding", "flooded"),[
        "Overflowing floodwater visibly covers streets, buildings or land.",
        "An old town with dry streets and no visible floodwater.",
        "A calm river flowing within its normal riverbanks.",
        "An empty landscape without water or a flood."]),
    (("aurora", "northern lights", "borealis"),[
        "Bright aurora lights form visible colored bands in the night sky.",
        "A dark night sky without clearly visible aurora lights.",
        "An ordinary cloudy daytime sky.",
        "A street of buildings photographed at night."]),
    (("tornado", "twister", "waterspout"),[
        "A visible rotating tornado funnel extends below a storm cloud.",
        "Dark ordinary storm clouds without a distinct tornado funnel.",
        "A calm cloudy sky without strong weather.",
        "A person walking along a road."]),
    (("avalanche", "snow slide"),[
        "A fast-moving avalanche of snow flows downhill.",
        "A snow-covered static mountain with no avalanche.",
        "A calm mountain landscape with no moving snow.",
        "A busy city street."]),
    (("glacier",),[
        "A glacier or moving ice is visible in a cold landscape.",
        "A snowy landscape without any visible glacier.",
        "An ordinary forest with no snow or ice.",
        "A street full of people."]),
    (("ocean", "surf", "wave"),[
        "Large ocean waves crash with moving white foam.",
        "Calm ocean water without breaking waves.",
        "A still river or lake with no crashing waves.",
        "A city scene without ocean water."]),
    (("hail",),[
        "Hailstones fall rapidly onto the ground during a storm.",
        "Rain falls gently without hailstones.",
        "A dry road on a clear day.",
        "A cloudy sky with no precipitation."]),
    (("waterfall","cascading","cascade"),[
        "A video showing a natural waterfall flowing over a rocky edge.",
        "A video showing a calm lake without a waterfall.",
        "A video of a person walking in a city street.",
        "A video of a dry landscape without water."]),
    (("lightning",),[
        "A video showing lightning flashes in a cloudy sky.",
        "A video of a daytime sky with no lightning.",
        "A video of a waterfall flowing over rocks.",
        "A video of a city street with people walking."]),
    (("volcano","eruption",),[
        "A video showing a volcano or volcanic eruption seen from far away.",
        "A video showing calm ocean water with no volcano.",
        "A video of an indoor room with furniture.",
        "A video of a regular cloudy sky without mountains."]),
    (("domino",),[
        "A video featuring domino tiles arranged or moving in a demonstration.",
        "A video showing empty wooden furniture with no dominoes.",
        "A video of people walking outdoors.",
        "A video of ocean waves on a beach."]),
    (("arduino",),[
        "A video of an electronic Arduino device or electronic components.",
        "A video of a forest with trees and no electronics.",
        "A video of a cat moving indoors.",
        "A video of ocean waves crashing."]),
    (("acrobat","gymnast","performance","dance","skate"),[
        "A video showing a person moving or performing a physical activity.",
        "A video showing an empty stage with no people.",
        "A video showing a dog playing outdoors.",
        "A video of an empty street with no people."]),
]

def prompts_for(title,label,topic_id=None):
    if topic_id is not None and topic_id not in SUPPORTED_TOPICS:
        raise ValueError("UNVERIFIED_OR_UNSUPPORTED_TOPIC_CONTEXT")
    key=(title+" "+label).lower()
    if topic_id in ("nature_moments","objects_oddities","human_moments"):
        for terms,arr in GENERIC_SCENES:
            if any(term in key for term in terms):
                return arr
        if topic_id=="human_moments":
            return [
                "A real person moves, dances, or performs a physical action.",
                "Stylized dancing silhouettes or abstract human graphics.",
                "A static crowd without a clear individual physical action.",
                "An empty indoor room with no people."]
        # Unknown object/nature filenames are genuinely inconclusive.
        return None
    if topic_id=="cat_surprises":
        # IDs such as Pexels PX-15135238 are not semantic titles, but their
        # *verified production topic* makes cat-vs-empty prompts appropriate.
        for terms,arr in SCENES:
            if any(t.lower() in key for t in terms):
                return arr
        return FALLBACK
    if topic_id=="dog_surprises":
        return [
            "A dog runs, jumps or plays actively.",
            "A dog sits still without playful movement.",
            "A dog walks slowly without interacting with anything.",
            "A scene without any dog."]

    # Do not evaluate real object, nature, or human footage as cats.
    if not any(k in key for k in ("cat","kitten","katz","chloé","moomin","larry","felis","dog","puppies","canine","hund","perro")):
        for terms,arr in GENERIC_SCENES:
            if any(term in key for term in terms):
                return arr
        # Explicit uncertainty is safer than a misleading cat-only verdict.
        return None
    # Dog TOP5 must never be evaluated against cat-only prompts.
    if any(term in key for term in ("pexels dog","puppiesplaying","dog playing","dog jumping","dog running")):
        if "jump" in key:
            expected="A video of a dog jumping up toward a person."
        elif "catch" in key or "fetch" in key:
            expected="A video of a dog actively playing fetch or catching a toy."
        elif "puppies" in key:
            expected="A video of puppies actively playing together."
        else:
            expected="A video of a dog running or playing outdoors."
        return [expected,
                "A video of a dog sitting quietly and not playing.",
                "A video of a dog walking slowly without a toy.",
                "A video of an outdoor scene without any dogs."]
    for terms,arr in SCENES:
        if any(s.lower() in key for s in terms):
            return arr
    return FALLBACK

def sample_times(a,b,n=8):
    if n<2 or b-a<1: raise ValueError("Invalid temporal window")
    gap=min(.38,(b-a)/10)
    return [round(float(x),3) for x in np.linspace(a+gap,b-gap,n)]

def take(video,t):
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-ss",str(t),
         "-i",str(video),"-frames:v","1","-f","image2pipe",
         "-vcodec","mjpeg","-q:v","3","pipe:1"]
    data=subprocess.run(cmd,capture_output=True,check=True,timeout=35).stdout
    im=Image.open(io.BytesIO(data)).convert("RGB")
    if im.size!=(1080,1920):raise ValueError("Locked V28.3 1080x1920 geometry required")
    # Exclude TOP5 header and left-hand ranks while keeping real footage.
    # Some background and caption pixels remain: this limits certainty.
    return im.crop((205,318,1060,1532))

def relative_verdict(probs):
    if len(probs)!=4 or any(not math.isfinite(x) for x in probs):
        raise ValueError("Expected four finite candidate scores")
    diff=float(probs[0]-max(probs[1:]))
    top=int(max(range(4),key=lambda i:probs[i]))
    if top!=0 and diff<-.08: flag="POSSIBLE_CAPTION_SCENE_MISMATCH"
    elif top==0 and diff>.12: flag="RELATIVE_TEXT_VIDEO_MATCH_ONLY"
    else: flag="INCONCLUSIVE_NEEDS_EDITORIAL_REVIEW"
    return {"flag":flag,"expected_minus_best_alternative":round(diff,4),
            "top_prompt_index":top,"no_calibrated_confidence":True}

def motion(frames):
    arr=[np.asarray(f.resize((100,130)).convert("L"),dtype=np.float32)
         for f in frames]
    values=[float(np.abs(a-b).mean()) for a,b in zip(arr,arr[1:])]
    return {"mean_frame_change":round(float(np.mean(values)),3),
            "fraction_low_change":round(sum(v<3.3 for v in values)/len(values),3),
            "not_action_or_humor_score":True}

def verify(video,selections):
    p=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams",
           "-of","json",str(video)],capture_output=True,text=True,check=True)
    info=json.loads(p.stdout)
    vids=[x for x in info["streams"] if x["codec_type"]=="video"]
    if (len(vids)!=1 or vids[0]["width"]!=1080 or vids[0]["height"]!=1920
        or not 29.8<float(info["format"]["duration"])<30.2):
        raise ValueError("Not the correct finished TOP5 MP4")
    data=json.loads(selections.read_text(encoding="utf-8"))
    rows=data["items_in_rank_5_to_1_order"]
    if len(rows)!=5 or len(set(x["title"] for x in rows))!=5:
        raise ValueError("Exactly five unique origins required")
    return rows

def storyboard(ranks,path):
    sheet=Image.new("RGB",(8*180,5*256),"#15191d")
    for j,(rank,frames) in enumerate(ranks):
        for i,fr in enumerate(frames):
            sheet.paste(fr.resize((180,256)),(i*180,j*256))
    sheet.save(path,quality=88)

def summary(flags):
    return {"relative_match":flags.count("RELATIVE_TEXT_VIDEO_MATCH_ONLY"),
            "possible_mismatch":flags.count("POSSIBLE_CAPTION_SCENE_MISMATCH"),
            "needs_editorial_review":flags.count("INCONCLUSIVE_NEEDS_EDITORIAL_REVIEW") +
                                     flags.count("UNSUPPORTED_SUBJECT_NEEDS_EDITORIAL_REVIEW"),
            "funny_outcome_certified":False,
            "copyright_and_licensing_cleared":False,
            "youtube_monetization_approved":False,
            "publication_approved":False}

def verified_topic_context(path):
    """Read a topic chosen by the actual upstream render, never guessed from a filename."""
    if path is None:
        return None
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    topic=data.get("chosen_topic")
    if topic not in SUPPORTED_TOPICS:
        raise ValueError("UNVERIFIED_OR_UNSUPPORTED_TOPIC_CONTEXT")
    return topic


def repair_worklist(ranks,topic):
    """Prioritize candidate replacement and caption re-review; never fabricate a story."""
    items=[]
    for row in ranks:
        flag=row["verdict"]["flag"]
        motion_proxy=row["motion_proxy"]
        low_motion=motion_proxy["fraction_low_change"] >= 0.7
        if flag=="POSSIBLE_CAPTION_SCENE_MISMATCH":
            disposition="CHECK_SOURCE_CUT_AND_REPLACE_IF_MISMATCH_CONFIRMED"
        elif flag=="UNSUPPORTED_SUBJECT_NEEDS_EDITORIAL_REVIEW":
            disposition="VERIFY_SUBJECT_WITH_REAL_FRAMES_BEFORE_WRITING"
        elif low_motion:
            disposition="CHECK_ACTION_PAYOFF_AND_TIMING"
        else:
            disposition="VERIFY_ACTUAL_EVENT_BEFORE_WRITING"
        items.append({
            "rank":row["rank"],
            "original_title":row["original_title"],
            "source_topic":topic,
            "relative_signal":flag,
            "low_motion_advisory":low_motion,
            "repair_priority":0 if row["rank"]==1 and flag!="RELATIVE_TEXT_VIDEO_MATCH_ONLY" else
                              1 if flag=="POSSIBLE_CAPTION_SCENE_MISMATCH" else
                              2 if flag=="UNSUPPORTED_SUBJECT_NEEDS_EDITORIAL_REVIEW" else 3,
            "next_action":disposition,
            "actual_action_confirmed":False,
            "suggested_creative_caption":None,
            "caption_ready_to_render":False,
            "ranking_payoff_verified":False,
            "publisher_rights_verified":False,
        })
    return sorted(items,key=lambda item:(item["repair_priority"],-item["rank"]))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--video",type=Path,required=True)
    ap.add_argument("--selection",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--topic-file",type=Path)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    rows=verify(args.video,args.selection)
    topic=verified_topic_context(args.topic_file)
    import torch
    from transformers import XCLIPProcessor,XCLIPModel
    torch.set_num_threads(2)
    model=XCLIPModel.from_pretrained(MODEL,use_safetensors=True).eval()
    processor=XCLIPProcessor.from_pretrained(MODEL)
    allframes=[]; results=[]
    for (rank,start,end),src in zip(RANKS,rows):
        times=sample_times(start,end)
        frames=[take(args.video,t) for t in times]
        allframes.append((rank,frames))
        prompts=prompts_for(src["title"],src.get("label",""),topic)
        if prompts is None:
            # Filename/label insufficient for defensible scene hypothesis.
            # Include its actual frames in storyboard, but no false model vote.
            probs=[]
            verdict={"flag":"UNSUPPORTED_SUBJECT_NEEDS_EDITORIAL_REVIEW",
                     "expected_minus_best_alternative":0.0,
                     "top_prompt_index":None,
                     "no_calibrated_confidence":True}
        else:
            tokens=processor(text=prompts,videos=frames,return_tensors="pt",padding=True)
            with torch.inference_mode():
                logits=model(**tokens).logits_per_video[0]
            probs=[round(float(x),5) for x in logits.softmax(dim=0).tolist()]
            verdict=relative_verdict(probs)
        results.append({
         "rank":rank,"original_title":src["title"],
         "on_screen_label":src.get("label",""),
         "times_seconds":times,"relative_competing_prompts":prompts,
         "relative_score_vector":probs,
         "verdict":verdict,"motion_proxy":motion(frames),
         "visual_truth_verified":False,
         "creative_or_comedic_payoff_verified":False,
         "third_party_rights_checked":False})
        print("V31",rank,src["title"],verdict["flag"],flush=True)
    storyboard(allframes,args.output/"V31_40_FRAME_STORYBOARD.jpg")
    flags=[r["verdict"]["flag"] for r in results]
    report={
      "model":MODEL,"status":"REVIEW_ONLY_NEVER_PUBLISH",
      "upstream_verified_topic":topic,
      "topic_bound_to_actual_render":topic is not None,
      "uses_free_open_source_model_not_paid_API":True,
      "method":"8-frame X-CLIP video/text comparison, 4 English prompts per rank",
      "dataset":"Kinetics-400",
      "caveat":"Prompt-dependent relative scores, not calibrated accuracy or humor estimates",
      "review_of_originals_not_performed":True,
      "composited_MP4_crops_include_possible_overlay_pixels":True,
      "locked_V28_3_design_preserved":True,
      "summary":summary(flags),"ranks":results}
    (args.output/"V31_SEMANTIC_QA.json").write_text(json.dumps(
         report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# V31 video-text screening","",
      "X-CLIP is a video-language similarity model, not a creativity or rights judge.","",
      "| Rank | Video origin | Relative signal | Margin |",
      "|---|---|---|---:|"]
    for r in results:
        lines.append("| {rank} | {title} | {flag} | {margin:.3f} |".format(
          rank=r["rank"],title=r["original_title"].replace("|","/"),
          flag=r["verdict"]["flag"],
          margin=r["verdict"]["expected_minus_best_alternative"]))
    lines+=["","All source rights, third-party permissions, YPP and publication: **NOT CLEARED**."]
    (args.output/"V31_SEMANTIC_QA.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    worklist={
        "schema_version":1,
        "actual_upstream_topic":topic,
        "topic_context_present":topic is not None,
        "editorial_score_100":None,
        "rights_cleared":False,
        "publication_approved":False,
        "generated_creative_captions":False,
        "automatic_source_replacement_executed":False,
        "method":"X-CLIP prompt-relative comparison + real 8-frame motion cues, advisory only",
        "items":repair_worklist(results,topic),
    }
    (args.output/"TOP5_EDITORIAL_REPAIR_WORKLIST.json").write_text(
        json.dumps(worklist,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print("V31 DONE: SEMANTIC ADVISORY ONLY",flush=True)

if __name__=="__main__":main()
