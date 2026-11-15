# TOP5 V37.1 — full render and cautious editor QA (2026-11-16 KST)

## Objective and approved template
- Automatically select meaningful and legally usable cat activity clips for an original, commercially viable TOP5 Short.
- **Do not change user-approved V28.3 design**: 30.000s, 1080×1920, 24fps, H264/AAC; 305px black header and 2-line gold/white subject; 5-to-1 left ranking; source native aspect ratio preserved with blurred background; fixed Caption font 60pt at (504,1190); five clips on last 27–30s card; original source audio muted, custom synthesized soundtrack, no TTS.

## Executions directly verified
- Curated V37 original contact-sheet audition: https://github.com/ddiet3332/top5-shorts-auto/actions/runs/43765450350 — success. Five potential sources inspected (one Pexels candidate failed file-size limit; mirrors and idle cats rejected as near-static).
- Actual V37.1 production: https://github.com/ddiet3332/top5-shorts-auto/actions/runs/43766411020 — success, fixed-layout tests pass, entire MP4 video+audio decode pass.
- Video: 30.000s 1080×1920 H264/AAC, 24fps; output GitHub artifact TOP5-V32-auto-review-14; retention 7 days.
- Timing fix: V37 rank 2 door source from 15.35–21.35s to **15.90–21.90s**, showing more than 1s of opened door at finale; sample rendered frames @ global 15.1,15.7,16.4,17.1,17.8,18.5,19.2,19.9,20.4,20.8s audited.
- V37 original authored two-stage captions for 5th, 4th, 3rd and 1st; 3-stage **door attempt → pressing handle → door open** in 2nd. One line at a time, all caption style geometry unchanged.
- Current 2026-11-16 source list in 5th→1st order: 
  1. CC0 Commons `File:Cat Jumpscare.webm`, Panini!, 4.0–8.0s, fast camera rush.
  2. Pexels `40826295`, Zeynep Coşkun, sidewalk roll.
  3. Pexels `34689563`, nilay ortanca, hidden cat catches pink toy, 9.29–13.29s.
  4. CC BY-SA 4.0 Commons `File:Cat opening door.webm`, Astropulse, 15.9–21.9s (latest edit), full door-opening action.
  5. CC BY 3.0 Commons `File:Salto - Cat Jump.webm`, Record 124, roof jump, 2.65–8.65s, separate hook 4.9–6.9s.
- The order above is *shown 5th to 1st* and not a factual global viral-ranking claim.
- Automated trending or viewer-performance evidence has NOT been established; candidate selection uses stored action audit and metadata.

## Provisional professional editor score /100
| dimension | score | evidence |
|---|---:|---|
| Hook | 17/20 | same proven midair roof jump 0–2s, distinct immediate motion |
| Surprise, humor, payoff | 22/25 | camera rush, couch toy catch, paw-actuated door, roof jump; 2nd door action takes a few seconds to pay off |
| Ranking | 13/15 | 2nd door-opening is distinctive compared to 3rd toy play; dim source and delayed reveal limit clarity |
| Cut flow | 14/15 | continuous cat door payoff now actually visible in last second; 5th source motion blur remains |
| Original authored captions | 9/10 | original timed setup→action→payoff instead of just reaction; still short and minimal compared to voice commentary |
| Original audio | 7/10 | synthesized effects+stereo AAC and full decode; full audience reaction/critical listening not measured |
| Rights / YPP | 1/5 | provider-declared licenses only; CC BY-SA obligations and reused-content risks unresolved |
| **Total** | **83/100 provisional** | **Below 85 minimum; cannot publish.** |

The editor score is not measured viewer humor, clickthrough rate, retention, subscriber growth, or YouTube approval.

## Blocking rights and monetization issues
- Source authorship is claimed by Commons own-work uploaders or Pexels profiles. That is useful provenance but not conclusive verification of independent ownership, grants for all third-party elements or withdrawn claims.
- **CC BY-SA 4.0** door-opening adaptation adds attribution and ShareAlike obligations and complicates a mixed-source compilation. Consult licence to correctly scope adapted material, link author and licence and note changes; do NOT treat entire clip as proprietary exclusive footage.
- **CC BY 3.0** rooftop jump must credit Record 124, source and licence, and editing modifications in YouTube description.
- Pexels stock videos may be modified and published on YouTube under its provider terms; this is not a guarantee that each source video was submitted by its owner or that YPP reused-content review will pass.
- YouTube official rules: compilations with little narrative are often reused content even if licensed. New timed captions are a positive creative addition but the work is STILL third-party clips with short writing; significant original commentary or different creative treatment is still needed for reasonable monetization readiness.
- Source original audio is removed. No recognizable people are shown in the five selected footage segments based on sampled frames; source footage still requires rights review.
- **publication_approved=false; automated YouTube posting remains disabled.**

## X-CLIP model evidence and limitations
- V37.0 after earlier door crop (15.35–21.35) was: 5th/4th/3rd relative text-video match, 2nd mismatch possibility −0.689, 1st inconclusive. Human actual frames confirm door does open; model does not reliably detect brief delayed event.
- V37.1 free X-CLIP follow-on: https://github.com/ddiet3332/top5-shorts-auto/actions/runs/43766565470 — launched; follow-up exact outcome and source-frame disagreement must be checked before interpreting.
- Model confidence does not equal humor, copyright, YPP, author provenance, factual appropriateness or publish permission.

## Next required development
1. **Fix the overall reused-content risk**, not just move an 83 score to 85: source-independent original analysis and substantial per-rank transformations that preserve the locked geometry and no TTS. Alternative: use truly user-owned originals with explicit commercial licences; never assume stock terms pass YPP.
2. Decide whether CC BY-SA asset compatibility is worthwhile; prefer safer CC0/Pexels action equally strong if license obligations cannot be satisfied without limiting rights.
3. Align action-synchronized original sounds precisely to frame timestamps and improve 5th blurry moment if original action allows; justify score changes via actual MP4 frame and listening QA.
4. Independently validate creator/third-party rights and legal attribution, then repeat technical/story QA, evaluate >=85 only when fully evidenced.
5. Until BOTH quality and public rights considerations are sufficiently reviewed, preserve **NO automatic public posting** and no user interim notifications. Latest user explicitly requested no status messages until there is a video genuinely ready to post.

## Primary records
- Code: `src/top5_auto_v32.py` (V37.1 inserted), `src/top5_auto_v29.py` (two-/three-stage authored captions).
- Tests: `tests/test_v37_story.py` + previous V28/V32/V36 safeguards.
- Actual clip rights and required attribution: `V37_ATTRIBUTION_AND_PUBLISH_GATES.md` in workflow artifact.
- Original official policy: https://support.google.com/youtube/answer/1311392?hl=ko ; https://www.pexels.com/license/ ; https://creativecommons.org/licenses/by-sa/4.0/ .
