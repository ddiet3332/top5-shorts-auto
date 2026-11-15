# V21.2 — 2026-11-15 실제 30초 편집본 / 100점 평가

## 결과
- 실제 5개 서로 다른 원본을 사용해 V21 검수용 30초 쇼츠 제작 완료. 1080×1920/24fps H.264/AAC, 전체 오디오·비디오 디코딩 통과.
- 5→1위: Pexels 레이저 고양이 → Pexels 잔디 추격 → Pexels 의자 점프 → Panini! CC0 Cat Jumpscare → Record 124 CC BY 3.0 Salto - Cat Jump.
- 원본 오디오 전부 제거, Python에서 직접 만든 합성 리듬/반응 효과음만 혼합. 영상 픽셀은 재인코딩 없이 오디오만 리마스터.
- 로컬 실제 최종 검수본 `TOP5_V21_2_REVIEW_ONLY_1080x1920.mp4`: 영상·음성 30.000초, 음향 평균 -21.1 LUFS / True Peak -2.2 dBFS. GitHub Actions V21.2 음향 재생성도 자동화 코드에 반영.
- 약 17.5~18.1초 고양이의 실제 근접 돌진 장면이 존재하며 반전 자막과 동기화됨. 약 0.1초 간격으로 원본과 편집본을 대조해 확인.

## 기존 고정 100점 평가

| 항목 | 만점 | 실제 편집본 정성 평가 |
|---|---:|---:|
| 첫 2초 후킹 | 20 | 19 |
| 장면의 재미·반전 | 25 | 14 |
| TOP5 순위 설득력 | 15 | 11 |
| 컷 전환·흐름 | 15 | 12 |
| 코믹 자막·창작성 | 10 | 6 |
| 사운드·몰입감 | 10 | 7 |
| 저작권·수익화 준비 | 5 | 2 |
| **합계** | **100** | **71** |

**판정: 71/100, 제작 목표 75 미만 / 게시 후보 목표 85 미만. 영상 공개 금지.**

## 문제점 / 후속 수정
1. **5위 레이저, 4위 잔디**: 명확한 코미디 반전 부족. 실제로 더 웃긴 원본으로 대체.
2. **3위 스핑크스**: 의자에 올라가는 장면은 확인되나 전반부 어두운 컷이 길어 훅 개선 필요.
3. **1위 건물 점프**: 실제 도약은 강하나 기존 영상/아웃트로 반복이고, Vimeo 이식 CC BY 메타데이터만으로 저작권 권리 전체가 증명되지는 않음. 저작자·제3자 권리와 음악·상표 검토 필요.
4. **Pexels 외부 원본**: 공급사 라이선스가 상업 이용을 허용해도 제3자 권리 및 유튜브 재사용 콘텐츠 수익화 적합성은 따로 판단해야 함. 외부 원음·음악 전부 미사용.
5. **자막의 창작성**: 정확한 상황 설명은 확보했으나 자체 해설/비교가 부족. 단순 영상 모음의 수익화 위험을 해소하지 못함.

## 원본 출처
- Pexels Yasir YETER: https://www.pexels.com/video/cat-17462877/
- Pexels Marc Espejo: https://www.pexels.com/video/video-of-a-cat-catching-the-white-cloth-6187151/
- Pexels KoolShooters: https://www.pexels.com/video/a-sphynx-cat-jumping-on-a-stool-7680667/
- Commons Panini! CC0: https://commons.wikimedia.org/wiki/File:Cat_Jumpscare.webm
- Commons Record 124 CC BY 3.0: https://commons.wikimedia.org/wiki/File:Salto_-_Cat_Jump.webm
- Pexels Terms: https://www.pexels.com/terms-of-service/
- YouTube reused content guidance: https://support.google.com/youtube/answer/1311392

이 문서는 완료된 검수본에 대한 **편집자의 정성 평가**이며, 알고리즘이 재미를 자동 승인했다는 뜻이 아닙니다. GitHub Actions의 자동 실행 성공은 게시 허가가 아닙니다.
