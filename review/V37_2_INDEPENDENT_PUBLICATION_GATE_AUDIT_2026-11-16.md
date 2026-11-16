# V37.2 independent publication-gate audit — 2026-11-16

## Starting point
Reviewed `review/V37_1_ACTUAL_EDITED_VIDEO_100POINT_EDITORIAL_QA.md`, baseline V35 handoff, workflow definition, production script first 180 lines, and the V37.1 artifact metadata. **No fresh rendered MP4 was independently played or decoded in this audit.** The existing V37.1 83/100 is provisional, not upgraded.

## Verified production artifact
- Run: https://github.com/ddiet3332/top5-shorts-auto/actions/runs/43766411020
- Artifact: `TOP5-V32-auto-review-14`, id `14182940090`, 14,157,365 bytes, SHA-256 digest `2c940b5bd5c2dc718ba860f0b85642ef7f5f29fb75fe3bbca22d28afd173e4ef`.
- Artifact expires 2026-11-22 21:57:46 UTC. Artifact metadata and workflow success are **not** equivalent to independent playback or editorial QA.
- Workflow explicitly validates ffmpeg full video+audio decode and runs design regression tests. Current workflow has no automatic publication step.

## Blocking findings
1. Source rights: Commons CC0 uploader assertions and Pexels account attribution are not independent chain-of-title evidence. The door CC BY-SA 4.0 and roof CC BY 3.0 require documented attribution, license links and change notices. The door adaptation's ShareAlike scope must be assessed and the license text included in the deliverable's attribution package. A mixed montage cannot simply be declared wholly proprietary.
2. Third-party rights: Verify people, trademarks, music, art and privacy/property rights in actual source footage; muting original audio addresses audio rights only.
3. YouTube reused-content/inauthentic-content: Licensed third-party footage + short two-stage captions + synthesized effects is still materially a compilation. Add genuine editorial explanation, creative causality, comparative analysis, or substantial transformation beyond decorative effects **without changing approved V28.3 geometry or introducing TTS**. No YPP assurance can be inferred from copyright compliance.
4. Current V37.1 83/100 must not be increased merely by improving metadata or adding effects. Verify the actual 5th camera-rush readability, 2nd door payoff and 1st roof-jump action on decoded rendered frames, and listen to final AAC in context.
5. A self-asserted `rights_verified` flag or source provider license must not auto-enable publication. Require explicit source-by-source evidence references, human-reviewed third-party rights, attribution audit, and editorial originality review. Until all gates pass: `publication_approved=false`.

## Concrete next iteration acceptance criteria
- Retain 1080×1920, 24fps, 30s, 305px header, rank markers, 60pt caption at (504,1190), 27–30s endcard, no TTS, no original audio.
- Prefer a visually strong genuinely CC0 action clip instead of BY-SA door **only if** real sampled frames demonstrate an equally complete setup→action→payoff; CC0 status alone does not prove uploader ownership.
- Produce a source-specific evidence manifest with title, creator, canonical URL, license URL and version, upload provenance, changes, third-party-rights concerns, confidence and unresolved gaps.
- Render H264/AAC; ffmpeg full-decode; sample actual rendered frames at action milestones; perform independent sound and narrative QA; write a dimension-by-dimension 100-point score with evidence. Reject scores below 85 and any rights/originality blockers regardless of score.
- Preserve every rejected candidate and its reason in the repository. Never auto-publish.

## Outcome
**NOT POSTABLE.** No new rendered or independently viewed video in this iteration. V37.1 remains 83/100 provisional and publication clearance remains unresolved. This is a documented gate audit, not a successful video iteration.
