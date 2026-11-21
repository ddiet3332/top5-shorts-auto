"""User-locked 1631.mp4 design: full-bleed original footage + translucent left rank rail."""
import json
from pathlib import Path
from top5_auto_v29 import assemble_video, technical_qa, cue_with_ass_override
import top5_auto_v29 as v29
from v28_fullscreen_builder import run, FPS, W, H, ASS_HEAD, cue

def fullscreen_scene(source,start,seconds,destination,*,clear_rank_rail=False,picture_height=1920,source_crop=None,playback_rate=1.0):
    if not 0 < playback_rate <= 1:
        raise ValueError("Invalid playback rate")
    crop_filter=""
    if source_crop is not None:
        c=source_crop
        pan=(f"{c.start_x}+({c.end_x}-{c.start_x})*clip((t+{start}-{c.pan_start})/({c.pan_end}-{c.pan_start}),0,1)")
        crop_filter=f"crop={c.width}:{c.height}:'{pan}':{c.y},"
    graph=(f"[0:v]{crop_filter}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
           f"crop={W}:{H},setsar=1,setpts=(PTS-STARTPTS)/{playback_rate},"
           "fps=24,format=yuv420p[v]")
    run(["ffmpeg","-hide_banner","-v","error","-y","-ss",str(start),"-i",str(source),
         "-filter_complex",graph,"-map","[v]","-frames:v",str(round(seconds*FPS)),
         "-an","-c:v","libx264","-preset","veryfast","-crf","23",
         "-pix_fmt","yuv420p",str(destination)],timeout=250)

def locked_subtitles(path,topic,items,*,moving_ending=False,hook_caption=None,
                     hook_caption_y=1020,mobile_captions=True,segments=None,ending_caption=None):
    if segments is None:
        raise ValueError("Explicit locked-design segments required")
    # The reference has a dark translucent panel on the left, 1위 at top.
    # ASS drawing primitives guarantee consistent alpha and geometry.
    lines=[]
    # Reference 1631.mp4 shows a large gold, black-outlined title
    # during the opening hook only (0–2s), not throughout the ranking.
    opening_end=float(segments[0][1])
    headline=str(topic.get("headline") or "강아지 돌발 행동 TOP5")
    if "TOP5" not in headline.upper():
        headline=headline+" TOP5"
    lines.append(cue_with_ass_override(
        0,opening_end,"MainTopic",headline,540,160,8,7,
        r"{\\fs82\\bord5\\shad0\\1c&H00D7FF&\\3c&H000000&}"))
    t=0.0
    for label,length in segments:
        end=t+length
        lines.append(cue_with_ass_override(t,end,"Rank","m 0 0 l 175 0 175 690 0 690",0,455,7,1,r"{\\an7\\pos(0,455)\\p1\\1c&H101010&\\alpha&H77&}"))
        active=1 if label in ("rank1","outro") else int(label[-1]) if label.startswith("rank") else None
        for rank in range(1,6):
            y=475+(rank-1)*145
            color=r"\\1c&H00D7FF&" if rank==active else r"\\1c&HFFFFFF&"
            lines.append(cue_with_ass_override(t,end,"Rank",f"{rank}위",30,y,7,3,r"{\\fs58\\bord3\\3c&H000000&"+color+"}"))
        if label=="hook":
            reaction=hook_caption or "잠깐! 이 강아지 보세요"
            stages=[(0,reaction)]
        elif label=="outro":
            stages=[(0,ending_caption or "당신의 1위는?")]
        else:
            idx=5-int(label[-1])
            row=items[idx]
            stages=row.get("caption_sequence") or [(0,row.get("caption",""))]
        for k,(offset,message) in enumerate(stages):
            stop=t+(float(stages[k+1][0]) if k+1<len(stages) else length)
            if stop<=t+float(offset): continue
            safe=str(message).replace("{","(").replace("}",")")
            lines.append(cue_with_ass_override(t+float(offset),stop,"Caption",safe,
                             540,1160,5,5,r"{\\fs55\\bord5\\shad0\\1c&HFFFFFF&\\3c&H000000&}"))
        t=end
    path.write_text(ASS_HEAD+"\n".join(lines)+"\n",encoding="utf-8")
    return lines

def render_locked(topic,ranked,output,hook,ending,segments):
    # Temporarily swap the legacy composition functions only for this render.
    original_scene=v29.create_scene
    original_subtitles=v29.build_dynamic_subtitles
    try:
        v29.create_scene=fullscreen_scene
        v29.build_dynamic_subtitles=locked_subtitles
        video=assemble_video(topic,ranked,output,hook,moving_ending=True,
                             hook_caption=hook.get("caption"),hook_caption_y=1050,
                             mobile_captions=True,segments=segments,ending_source=ending)
    finally:
        v29.create_scene=original_scene
        v29.build_dynamic_subtitles=original_subtitles
    qa=technical_qa(video,output,topic,ranked)
    qa["rendered_design"]="TOP5_DESIGN_LOCK_V1 / reference 1631.mp4"
    qa["publication_approved"]=False
    (output/"V29_TECHNICAL_QA.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return video,qa
