# TOP5 V25 — 내레이션 결합과 권리 확인 상태 (2026-11-15)

## 기준 영상과 품질 기준
- 기준: V23 실제 30초 편집본, 1080×1920/24fps/H.264-AAC, 편집자 정성 평가 81/100.
- V24 4위 교체 실험 79/100은 거절, **V23 유지**.
- V25 새 내레이션 MP4는 아직 완성되지 않았습니다. 현재 대화에서 7개 음성 **대본**을 설계했지만 실제 SAMI 음성은 생성되지 않았습니다. 완성본·85점·게시 승인이라고 표기하지 마세요.
- SAMI 남성 '차분한 아나운서' 1.0x, 7개 구간 0–2, 2–6, 6–11, 11–15, 15–21, 21–27, 27–30초.
- 음성 muxer는 누락/과도한 음성 길이를 차단하고, 원속도 유지(아템포 금지), 기존 합성 효과음만 ducking, 30초 전체 비디오·오디오 디코딩 QA. 별도 시험 신호 7개로 성공 확인. 테스트 신호는 실제 음성이나 납품물이 아닙니다.
- 정확한 코드·manifest·SAMI CSV/지시서/원본 검토 대장은 사용자의 V25 다운로드 패키지에 들어 있습니다. 로컬 구현 파일은 별도이며 **현재 GitHub Actions의 V25 자동 믹스가 구현·검증됐다고 주장하지 마세요**.

## 기존 원본 5개 권리 요약
| 구간 | 출처와 표시된 저작자 | 허가 근거 | 현행 제한 |
|---|---|---|---|
| 5위 상자 진입 | Pexels PX-5495527, Meow Meow | Pexels License | 원저작자·제3자 권리와 YT 수익화 보장 불가 |
| 4위 장난감 도약 | Pexels PX-9208508, Maria Gomes | Pexels License | 동일 |
| 3위 의자 점프 | Pexels PX-7680667, KoolShooters | Pexels License | 동일 |
| 2위 카메라 돌진 | Commons Cat Jumpscare.webm, Panini! | Own work / CC0 1.0 | 원저작자 메타데이터·재사용 콘텐츠 별도 |
| 1위 건물 점프 | Commons Salto - Cat Jump.webm, Record 124 | CC BY 3.0 / 2020-08-04 자동 봇이 원 Vimeo 라이선스 확인 | 표기는 근거가 있으나 인간/제3자 권리 독립 검증 미완료 |

특히 1위는 라이선스 근거가 **전혀 없는 영상이 아닙니다.** Commons의 자동 라이선스 확인 이력과 원저작권·제3자 권리 확인을 구분해야 합니다. 영상 출처 표시에는 저작자, 원본 링크, CC BY 3.0 URL, 변경 내역을 보존해야 합니다.

## 새로운 돌발 장면 라이선스 후보
VBear Media의 **Cat fails jump from chair to bed in South Korea**(clip #27540)는 설명상 실제 점프 실패→낙하→보호자가 도움, 9초 원본. 독점 라이선스 권한 보유를 표시하며 별도 라이선싱 요청이 필요함.
- https://vbear.media/library/27540/cat-fails-jump-from-chair-to-bed-in-South-Korea
- Contact: Licensing@vbear.media
- 허락·금액 합의·계약 **없음**, 원본 영상도 현재 미사용. 무료 영상인 것으로 표시하지 않음.
- 영상의 코미디 전달력을 실제 시청 검수하기 전까지 확정하지 않음.

## 공식 이용 조건/YouTube 정책
- https://www.pexels.com/license/
- https://help.pexels.com/hc/en-us/articles/360042827333-Can-I-upload-Pexels-images-and-videos-to-YouTube
- https://commons.wikimedia.org/wiki/File:Salto_-_Cat_Jump.webm
- https://support.google.com/youtube/answer/1311392

**게시 승인: 아니오.** 사용 허락이 있어도 유튜브 재사용 콘텐츠 심사는 별개이며, 음성 해설/실질적 독창성의 영향도 개별 심사 전에는 보장할 수 없습니다.
