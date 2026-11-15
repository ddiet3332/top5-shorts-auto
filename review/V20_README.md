# TOP5 V20 — 촬영자 자작 원본·상업 이용 허가 우선 검수

이전 V17·V19는 원본 수집에 성공해도 5초 동안 웃음/반전이 충분하지 않은 영상이 많았습니다. V20은 **실제로 본인 촬영 영상이라고 표시한 고품질 원본**을 우선 검토합니다.

## 검토 중인 정확한 원본 3개

1. **Cat Jumpscare.webm** — Panini! / 1920×1080 / 약 10.35초 / 13.42MB / Wikimedia Commons CC0 / 원본페이지: https://commons.wikimedia.org/wiki/File:Cat_Jumpscare.webm
   설명은 카메라를 향해 빠르게 달려오는 고양이. 실제 놀람·코믹 순간은 미검수.
2. **Ocicat on Cat Wheel.webm** — Oldperson / 1280×720 / 약 64초 / 47.96MB / Wikimedia Commons CC0 / 원본페이지: https://commons.wikimedia.org/wiki/File:Ocicat_on_Cat_Wheel.webm
   러닝휠의 고양이. 속도 변화나 예상 밖 결말이 없다면 제외.
3. **Black and white cat growl and hiss.webm** — Abujoy / 1920×1080 / 약 35초 / 11.09MB / Wikimedia Commons CC BY 4.0 / 원본페이지: https://commons.wikimedia.org/wiki/File:Black_and_white_cat_growl_and_hiss.webm
   으르렁거리고 하악질하는 고양이. 공격/스트레스 장면을 웃음으로 왜곡하지 않아야 함.

## 라이선스·수익화 분리

- CC0는 해당 저작권자의 공개 라이선스 조건상 상업적 이용 허락을 별도로 다시 받을 필요가 없습니다. 하지만 ‘Own work’ 표기가 원작자의 실제 소유권을 독립적으로 입증하지는 않으며 피사체·음원·제3자 권리는 따로 점검합니다.
- CC BY 4.0은 적절한 저작자, 원본 URL, 라이선스 링크, 편집·변경 내역 표기가 필요합니다.
- 유튜브 재사용 콘텐츠 정책은 저작권 허락과 별개입니다. 단순 TOP5 편집은 허가 영상이어도 수익화 거절 가능성이 있습니다.
- 모든 소스 미리보기는 원본 오디오를 제거합니다. 페이지 메타데이터, 제목 또는 동작 점수만으로 재미와 권리·게시 승인 자동판정을 금지합니다.

## 프로그램 절차

GitHub Actions: .github/workflows/v20.yml
- 정확한 File: 원본 제목과 촬영자 명칭, 'Own work' 주장, 해당 파일의 **현재** CC0 또는 CC BY 4.0 이용 조건을 대조.
- 불일치 원본은 자동 제외하고 이유 기록.
- 일치한 원본 1~3개만 기존 V17 실제 동작 미리보기 엔진으로 내려받아 5초 MP4 2개씩 생성 시도.
- 영상의 실제 행동, 프레임별 반전·웃음·가독성은 채팅에서 직접 판단.
- GitHub Actions의 artifact와 review/v20_latest.json에 최신 실행 ID·후보·실패 이유 기록. 사용자 ZIP 반복 업로드 불필요.
- 전체 **기존 100점 평가표는 30초 완성본이 생성되기 전까지 미평가**.
- 어떠한 경우도 5개 미만 후보를 억지로 선정하거나 수익화·저작권이 자동으로 통과했다고 표시하지 않습니다.

## 촬영자 직접 허락이 필요한 기타 SNS 영상

CC0나 적합한 CC BY처럼 허락이 명시되지 않았다면, 영상 촬영자가 정말 권리를 갖고 있는지 확인하고 **해당 영상의 유튜브 상업 이용, 발췌, 편집, 음성·자막 추가, 썸네일 사용 범위**를 서면으로 허락받아야 합니다. 허가 수령 전 영상은 검색·링크 검토에 한정하고 쇼츠 최종 렌더링에 넣지 않습니다. 허가문·개인 연락처·계약서는 공개 GitHub 저장소에 기록하지 않습니다.

YouTube 공식 정책:
- https://support.google.com/youtube/answer/1311392
- https://support.google.com/youtube/answer/2797468
- https://support.google.com/youtube/answer/12361994
