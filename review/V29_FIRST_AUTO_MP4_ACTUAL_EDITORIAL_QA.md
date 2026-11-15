# V29 first fully-automatic render — actual MP4 editorial QA

Date: 2026-11-15
Source: GitHub Actions run 43726115408 / artifact TOP5-V29-auto-review-2.
Rendered file: `TOP5_AUTO_V29_REVIEW_1080x1920.mp4`

## Verified technical facts
- Actual MP4 downloaded, opened and sampled across 0–30 seconds.
- 30.000 seconds; 1080×1920; 24fps; video H.264; audio AAC; both streams decoded fully.
- The approved V28.3 black header, centered two-line title, left ranking, original footage, one line 60pt reaction captions and 27–30s endcard are present.
- Topic recommendation: 5 candidate categories, automated heuristic chose cat (6 eligible metadata originals; 5 used), with no paid external AI requests.
- No unapproved original camera audio used. Camera footage rights are NOT independently confirmed.

## Seven-category 100-point score (provisional sampled-frame editorial judgement)
| Category | Score | Grounding |
|---|---:|---|
| Hook | 13 / 20 | Kitten close-up is cute but not inherently shocking; stronger roof jump is buried at rank 5 |
| Funny/surprising outcome | 9 / 25 | Strong outdoor jump, moderate grass movement; indoor camera motion and street walking lack an obvious comic result |
| Rank ordering | 4 / 15 | Roof-to-roof leap is 5th while ordinary kitten camera approach is 1st: inverted payoff |
| Cut flow | 9 / 15 | Real 30s timeline, but some ranks linger after action or omit the setup/result |
| Original captions | 4 / 10 | Generic `다음 움직임 주목` style reacts weakly and does not add a meaningful story |
| Sound | 7 / 10 provisional | Licensed-original audio absent and synthesized AAC passes technical checks; detailed perceptual audition not performed |
| Rights/monetization | 1 / 5 | CC BY 2/3 and CC0 **metadata only**; underlying author and third-party rights/YPP reused-content not independently cleared |
| **Total** | **47 / 100 (provisional)** | **Not ready to post** |

This is a sampled-frame editorial evaluation, not a claim of complete human inspection of every frame, a measured audience reaction score, or an official YPP decision.

## Specific corrective action for next automatic render
- Current 5th: `Salto - Cat Jump.webm` — spectacular roof-to-roof jump; promote to 1st.
- Current 4th: `Katzensprung in Zeitlupe.webm` — white cat moving in green grass; move to 2nd at most, not an extreme surprise.
- Current 3rd: `Cat jumping backwards.webm` — shaky indoor shot; demote to 4th and change label/caption to avoid claiming a clearly visible jump.
- Current 2nd: `Cat chasing a pigeon.webm` — the chosen 15–21s clip shows a walking street cat, not a clearly proven pigeon chase; demote to 5th and remove `추격전` mislabel.
- Current 1st: `Cat Jumpscare.webm` — kitten approaches camera, not a jumpscare; demote to 3rd and label `카메라 접근`.
- Preserve all fixed design geometry, text sizes/colors, endcard, no TTS, and no unapproved original sound.

## Required publication gate
- >=75 to continue editorial production, >=85 to be a post candidate, rights gate separately verified.
- Do not publish just because GitHub Actions passes.
- A commentary caption on free-license source clips is not automatically sufficient original value for YouTube monetization.
