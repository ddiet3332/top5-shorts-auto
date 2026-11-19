"""Measure the rendered video and its audio without assigning editorial points."""
import subprocess

import numpy as np
from PIL import Image

from top5_qa_frames import extract
from v25_audio_remaster import create_soundtrack

FFMPEG = ["ffmpeg", "-nostdin", "-v", "error", "-xerror"]
CUT_SECONDS = 6
CUE_TIMES = (6, 12, 18, 24)


def motion(path, start, seconds, crop=""):
    raw = subprocess.check_output(
        FFMPEG + ["-ss", str(start), "-i", str(path), "-t", str(seconds), "-an",
                  "-vf", crop + "fps=4,scale=64:36,format=gray", "-f", "rawvideo", "-"],
        timeout=40)
    frames = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 36, 64).astype(np.int16)
    changes = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    return {"sample_count": len(frames),
            "mean_change": round(float(changes.mean()), 3) if len(changes) else 0,
            "peak_change": round(float(changes.max()), 3) if len(changes) else 0}


def soundtrack_checks(video, work):
    """Compare decoded AAC with the deterministic music bed and timed cue stems."""
    def pcm(path):
        raw = subprocess.check_output(
            FFMPEG + ["-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "12000",
                      "-f", "f32le", "-"], timeout=30)
        return np.frombuffer(raw, dtype="<f4")

    def similarity(a, b):
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return float(a @ b / norm) if norm else 0

    dry = work / "music_only.wav"
    if not dry.exists():
        create_soundtrack(dry, cue_times=(), action_accents=False)
    bed = pcm(dry)
    expected = pcm(work / "soundtrack.wav")
    actual = pcm(video)
    rate = 12000
    if len(actual) < 29.9 * rate:
        return {"bgm": False, "transition_sfx": False, "cue_matches": []}
    # Find the filter/encoder delay from a music-only interval, then reuse it for every cue.
    sample = actual[rate:2 * rate]
    lag = max(range(-150, 151),
              key=lambda shift: similarity(sample, bed[rate + shift:2 * rate + shift]))
    bgm = [round(similarity(actual[t*rate:(t+1)*rate], bed[t*rate+lag:(t+1)*rate+lag]), 3)
           for t in (1, 7, 13, 19, 25)]
    cue_matches = []
    span = int(0.4 * rate)
    for t in CUE_TIMES:
        offset = t * rate
        reference = slice(offset + lag, offset + lag + span)
        observed = actual[offset:offset + span]
        mix = similarity(observed, expected[reference])
        music = similarity(observed, bed[reference])
        cue_matches.append({"time_sec": t, "mix_similarity": round(mix, 3),
                            "music_only_similarity": round(music, 3),
                            "present": mix >= 0.75 and mix - music >= 0.025})
    return {"bgm": min(bgm) >= 0.7, "bgm_similarity": bgm,
            "transition_sfx": all(row["present"] for row in cue_matches), "cue_matches": cue_matches}


def overlay_checks(video, work, evidence):
    """Verify burnt-in text against known render plates at three frames per rank."""
    evidence.mkdir(parents=True, exist_ok=True)
    frames = extract(video, evidence, count=15)
    montage = Image.new("RGB", (5 * 216, 384))
    results = []
    for index in range(5):
        with Image.open(work / f"overlay_{index}.png") as overlay:
            plate = np.asarray(overlay.resize((360, 640), Image.Resampling.LANCZOS), dtype=np.int16)
        for frame_index in range(index * 3, index * 3 + 3):
            frame = frames["frames"][frame_index]
            with Image.open(evidence / frame.get("file", f"frame_{frame_index + 1:02d}.jpg")) as image:
                actual = np.asarray(image.convert("RGB"), dtype=np.int16)
                if frame_index % 3 == 1:
                    montage.paste(image.resize((216, 384)), (index * 216, 0))

            def match(y0, y1, x0, x1, *, outline=False):
                target = plate[y0:y1, x0:x1]
                observed = actual[y0:y1, x0:x1]
                ink = (target[:, :, 3] >= 250) & (target[:, :, 0] >= 240)
                if not ink.any():
                    return False
                gold = target[:, :, 2][ink] < 150
                r, g, b = observed[ink].T
                color_match = np.where(gold, (r >= 145) & (g >= 108) & (r - b >= 36) & (g - b >= 22),
                                       (r >= 164) & (g >= 164) & (b >= 164))
                if outline:
                    border = (target[:, :, 3] >= 250) & (target[:, :, :3].max(axis=2) <= 20)
                    if not border.any() or (observed[border].max(axis=1) <= 100).mean() < 0.55:
                        return False
                return bool(color_match.mean() >= 0.65)

            ranks = [match((520 + row * 128 - 46)//3, (520 + row * 128 + 46)//3, 8, 66)
                     for row in range(5)]
            results.append({"time_sec": frame["time_seconds"], "rank": 5-index,
                            "header": match(23, 109, 20, 326) and bool(actual[:16].mean() < 12),
                            "rank_labels": ranks,
                            "caption": match(457, 525, 24, 309, outline=True)})
    montage.save(evidence / "RANK_DESIGN_QA.jpg", quality=90)
    return {"overlay_header": all(row["header"] for row in results),
            "rank_alignment": all(all(row["rank_labels"]) for row in results),
            "caption_safe_area": all(row["caption"] for row in results), "frames": results}
