# Human dance TOP5: source-specific actual rendered-frame rejection (2026-11-21)

- Real source-to-MP4 Actions: https://github.com/ddiet3332/top5-shorts-auto/actions/runs/44891628808
- Output artifact: `TOP5-universal-human_moments-44891628808-1`
- SHA-256 of actual 30.0-second review MP4: `519e8c28138a3dd7ab0dedb1a0aa7df5f2602cb779c65a11557bb98fecca0698`
- Review evidence: extracted rendered MP4 frame(s) at approx. 1, 7, 13, 19 and 25 seconds; verified against source selection order in `stock_fallback/sources/SOURCE_DOWNLOAD_QA.json`
- This is **review-only**; no 85+ editorial score, no contributor/license/likeness/YPP clearance, no publication permission.

## Disqualifications grounded in actual rendered output
1. **Pixabay #15922, `https://pixabay.com/videos/id-15922/`**. Appeared in **rank 1 (24–30s)**. Visible **flamingos at a pond**, not human dancers. The exact Pixabay tags include `flamingo, flamingos, birds, dancing, animals`. This is a **human-topic false positive**. Automatic metadata-based human sourcing must reject.
2. **Pixabay #76124, `https://pixabay.com/videos/id-76124/`**. Appeared in **rank 2 (18–24s)**. Visible computer-rendered/animated baby figure, not genuine live-action human performance. The tags claim `baby, child, toddler, dancing`, without animation markers. **Actual frame review overrides misleading metadata**, so reject this ID from this human-live-action topic.

## Other clips in the same working video
- #1670, #29313, #77004: present in video, but scene action, edit payoffs, recording status, licensing provenance and creative quality are **not yet independently cleared**. Their presence does not certify rank quality or publication.
- An auto-generated video with 5 valid video files was technically real, but **not** an acceptable 5-human-scenes TOP5. `TECHNICAL_PASS` is not equal to `EDITORIAL_PASS`.

## Corrective action
Add `review/rejected_source_ids.json` entry for **`놀라운 댄스 동작 TOP5`: [76124, 15922]**. The existing source acquisition routine takes the ID set before downloading; it should continue searching for different genuine human clips. The separately added animal-tag negative filter also screens future similarly mislabeled footage. Do not bypass either rule because of source shortage. Produce a new MP4 and independently verify every selected source and all five rendered ranks. Human likeness, third-party, original-author and YouTube reused-content monetization checks remain independent blockers.
