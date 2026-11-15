# V19 — 저작권 구분이 있는 다중 소스 TOP5 후보 검수

기존 V17 Commons 검색에서 실제 재미있는 5컷이 확보되지 않아 후보 공급원을 다변화합니다. 단, 수익화·게시 자동 승인은 하지 않습니다.

## 이번에 개별 페이지를 확인한 후보 7개

- Pexels PX-7680667: 스핑크스 고양이 의자 점프, 공식 페이지 원본 7초. 실제 재미·착지는 미검수.
- Pexels PX-6187151: 야외 장난감을 추적하는 검은 고양이, 16초·1920×1080, 실제 추적/잡기/반전 타이밍은 미검수.
- Pexels PX-17462877: 실내에서 레이저를 쫓는 줄무늬 고양이, 15초·1080×1920, 실제 반응/웃음은 미검수.
- Pexels PX-7691993: 야외 상자 탐색, 9초. 점프 제목과 달리 페이지 설명은 탐색. 링크 후보만 보관.
- Mixkit MK-22732: 잔디에서 갑자기 움직이는 고양이, 9초. 개별 영상 Free License 문구 확인, 자동 다운로드 안 함.
- Mixkit MK-1779: 빨대로 장난치는 고양이, 15초. 개별 영상 Free License 문구 확인, 이전 면봉놀이 영상과 중복 주의.
- Pixabay PB-305341: ‘Cat Fail’이라고 등록된 5초 영상. Content License 표기 확인. AI 생성/재게시 가능성과 원본 사용권 미검증으로 보류.

실행 #3에서는 Pexels PX-7680667만 5초 미리보기를 생성했고, 4K·장시간 원본 PX-6853903, PX-6853188은 다운로드 제약에 걸려 미리보기를 만들지 못했습니다. 이 두 원본을 위의 짧은 개별 페이지 후보로 교체했습니다. 실패한 원본의 접근을 우회하거나 안전 제한을 무단 완화하지 않습니다.

## 실제 확인한 위험 사례

Mixkit kitten-playing-with-ball-6999, young-cats-play-in-the-garden-14184, kitten-hiding-outside-26381, kitten-playing-in-the-couch-6954의 무료 파일은 **Restricted License / Personal Use Only**로 표시돼 수익화용에서 제외했습니다.

Pexels video-of-cat-jumped-off-the-sofa-4807151은 원본 3초라 5초 순위 컷에 즉시 사용 불가합니다.
Pexels cat-jumping-from-a-box-7691993 공식 설명은 고양이의 나무상자 탐색입니다. 제목으로 실제 점프를 추정하면 안 됩니다.

## V19 실행

GitHub Actions → TOP5 CC Shorts - discover and draft → Run workflow → mode=v19-multisource

1. 수동으로 개별 페이지·라이선스 조건을 검토한 정확한 URL 7개만 샘플 카탈로그에서 사용.
2. Pexels 3개까지만 기존 공식 단일 원본 다운로드 경로로 5초 미리보기 생성 시도. 접근 실패 시 우회 없이 실패 기록.
3. Mixkit·Pixabay는 페이지 링크만 출력. Restricted 페이지는 코드 차단. 대량 다운로드·크롤링 없음.
4. 모바일 HTML, CSV, JSON, Markdown 보고서 및 성공한 미리보기 MP4를 Actions artifact에 저장.
5. ChatGPT의 GitHub 연결을 통해 Actions 아티팩트를 직접 가져올 수 있으므로 사용자는 매번 ZIP을 직접 올리지 않아도 됨.
6. 실제 영상 동작·재미, 출처 원저작자·제3자 음원, 유튜브 수익화는 반드시 별도로 검수.

## 평가표 유지

첫 2초 후킹 20 / 재미·반전 25 / 순위 설득력 15 / 컷·흐름 15 / 자막 창작성 10 / 사운드 10 / 저작권·수익화 준비 5 = 100점.
75점 제작 목표, 85점 게시 후보 목표. **권리 미검증이면 점수와 무관하게 업로드 금지**.

## 공개된 이용 조건

- https://www.pexels.com/license/
- https://help.pexels.com/hc/en-us/articles/900005880463-What-are-the-Terms-and-Conditions
- https://mixkit.co/license/modal/videoFree/
- https://mixkit.co/license/modal/videoRestricted/
- https://pixabay.com/service/license-summary/
- https://support.google.com/youtube/answer/1311392

V19는 Pexels·Mixkit·Pixabay 영상의 비독점 사용조건을 별도 기록하며 CC BY/CC0인 것으로 혼동하지 않습니다. V18 편집 연결은 현재 Wikimedia 원본용이므로, V19 영상까지 최종 렌더링에 넣으려면 해당 소스의 실제 영상과 권리 검증을 먼저 거쳐야 합니다.
