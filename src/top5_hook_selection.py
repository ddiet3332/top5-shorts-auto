"""Select a two-second opening from screened originals."""
import subprocess

import numpy as np

HOOK_SECONDS = 2
GAP = 0.25


class SourceShortage(RuntimeError):
    def __init__(self, code, detail, attempts=()):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.attempts = list(attempts)


def sampled_frames(source, start, seconds):
    raw = subprocess.check_output(
        ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-ss", str(start), "-i", source["local_path"],
         "-t", str(seconds), "-an", "-vf", "fps=3,scale=64:36,format=gray", "-f", "rawvideo", "-"],
        stderr=subprocess.PIPE, timeout=30)
    return np.frombuffer(raw, np.uint8).reshape(-1, 36, 64).astype(np.int16)


def identity(row):
    return row.get("source_page") or row["title"]


def separated(start, ranked_start, ranked_duration):
    return (start + HOOK_SECONDS + GAP <= ranked_start or
            start >= ranked_start + ranked_duration + GAP)


def choose_hook(ranked, candidates, durations, attempts):
    """Prefer independent footage. A reused window must also differ visually."""
    rank_indices = {identity(row): i for i, row in enumerate(ranked)}
    rank_frames = {}
    for row in sorted(candidates, key=lambda x: identity(x) in rank_indices):
        index = rank_indices.get(identity(row))
        mode = "independent_source" if index is None else "nonoverlapping_rank_source"
        end = row["duration_sec"] - HOOK_SECONDS - 0.1
        if end < 0:
            continue
        starts = dict.fromkeys(round(x, 3) for x in (
            min(end, row["cut_start"] + 1.3), 0, end / 2, end,
            *range(1, int(end) + 1, max(1, int(end / 12)))))
        for start in starts:
            if index is not None and not separated(start, row["cut_start"], durations[index]):
                continue
            result = {"stage": "hook", "title": row["title"], "start_sec": start, "mode": mode}
            try:
                opening = sampled_frames(row, start, HOOK_SECONDS)
                if len(opening) < 6 or np.any((opening <= 20).mean(axis=(1, 2)) > 0.95):
                    code = "HOOK_DARK_OR_SHORT"
                elif np.abs(np.diff(opening, axis=0)).mean() < 1.0:
                    code = "HOOK_LOW_MOTION"
                else:
                    code = None
                    for rank, ranked_row in enumerate(ranked):
                        if rank not in rank_frames:
                            rank_frames[rank] = sampled_frames(ranked_row, ranked_row["cut_start"], durations[rank])
                        ranked_sample = rank_frames[rank]
                        if len(ranked_sample) < 6:
                            code = "HOOK_COMPARISON_UNAVAILABLE"
                            break
                        distances = np.abs(opening[:, None] - ranked_sample[None, :]).mean(axis=(2, 3))
                        if (distances.min(axis=1) < 9).mean() >= 0.34:
                            code = "HOOK_REPEATED_VISUALS"
                            break
            except (subprocess.SubprocessError, OSError, ValueError):
                code = "HOOK_SAMPLE_FAILED"
            attempts.append({**result, "reason_code": code, "status": "REJECTED" if code else "SELECTED"})
            if code is None:
                return {**row, "hook_start": start, "hook_mode": mode}
    raise SourceShortage("NO_DISTINCT_HOOK", "별도 원본 또는 구분 가능한 2초 훅 구간 부족", attempts)
