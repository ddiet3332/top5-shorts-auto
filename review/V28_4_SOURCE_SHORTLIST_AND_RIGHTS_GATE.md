# TOP5 V28.4 — 웃긴 장면 후보 및 실제 검수 계획
기록일: 2026-11-15

## 사용자 확정 디자인 (변경 금지)
- `review/TOP5_TEMPLATE_STYLE_LOCK.md`를 그대로 적용.
- 기존 V28.3의 상단 제목/검은 305px 헤더/왼쪽 순위표/중앙 원본 영상/하단 한 줄 자막/3초 엔드카드 고정.
- 하단 Caption 60pt (47pt에서 확대 완료); 디자인 수정은 금지. 재미 없는 원본을 고급 디자인으로 포장하지 말 것.
- 이 문서는 차기 소스 편집 후보만 다룬다. **영상 업로드 또는 수익화 승인 아님.**

## 실제 V28.3 검수에서 나온 문제
- 5위 (상자) : 4초의 상당 구간이 행동 종료 후 정적임.
- 3위 (간식/의자): 반전/황당함에 대한 증거가 약함.
- 2위 (카메라 접근): 피사체 흐림과 결말 전달력 부족.
- 기존 1위: 처음 훅과 본편의 같은 점프 중복, 동작 후 정적 장면.

## 1차 무료 사용 가능 후보 (각각 실제 프레임 선별 전 단계)
1. **Pexels 6931535 — Tabby Cat Jumps from the Bench**
   - 공식 페이지: https://www.pexels.com/video/tabby-cat-jumps-from-the-bench-6931535/
   - 제공자: Artyom Saqib; 6초, 2160×3840(세로), Pexels License.
   - 페이지 제목은 점프를 주장하지만 소개 문구는 앉아 있는 고양이를 설명하므로 **실제 5초 행동/결말 확인 전 채택 금지**.
   - 검토 대상: 기존 5위 대체 가능성.
2. **Pexels 6853903 — A Ginger Cat Jumping Up And Down A Chair**
   - https://www.pexels.com/video/a-ginger-cat-jumping-up-and-down-a-chair-6853903/
   - 제공자: cottonbro studio; 32초, 2160×4096(세로), Pexels License.
   - 긴 영상 중에서 진짜 점프 또는 실수와 후속 행동이 한 번에 잡히는 5초 컷을 찾아야 함.
   - 검토 대상: 기존 3위 대체 가능성.
3. **Pexels 6853902 — A Cat Hopping On A Chair**
   - https://www.pexels.com/video/a-cat-hopping-on-a-chair-6853902/
   - 제공자: cottonbro studio; 9초, 4096×2160(가로), Pexels License.
   - 6853903과 같은 고양이·같은 행동일 가능성 확인: 중복이면 둘 중 하나만 채택.
   - 검토 대상: 기존 2위 대체 가능성.
4. **Wikimedia Commons — Cat jumping backwards.webm**
   - https://commons.wikimedia.org/wiki/File:Cat_jumping_backwards.webm
   - 작성자 Mary Qin; 18.81초, 1920×1080, CC BY 3.0.
   - 원 Vimeo 영상의 과거 CC BY 표기를 2017년 Commons 검수에서 확인한 기록. 저작권 귀속/제3자 권리 별도 검증 필요.
   - 원본에서 4~6초 연속 동작과 웃긴 반전이 입증되면 2~3위 후보.
   - 게재 시 원저작자·원본 URL·CC BY 라이선스 URL·편집·변경 사실을 명시.
5. **Wikimedia Commons — Kitten jumping on bamboo mat.webm**
   - https://commons.wikimedia.org/wiki/File:Kitten_jumping_on_bamboo_mat.webm
   - 업로더 Fumikas Sagisavas, 4.33초 1920×1080, CC0 자체 창작 표시.
   - 정확한 장면과 출처/제3자 권리 확인 전 선정 금지. 기존 프로그램이 5초 이상 클립을 요구하므로 무작정 반복/정지 연장하여 웃긴 장면을 꾸며내지 않음.

## 제외 후보 — 사용료/권리 제한
- https://vbear.media/library/27540/cat-fails-jump-from-chair-to-bed-in-South-Korea — Exclusive licensing. **권리 계약 전 자동 수집/사용 금지.**
- https://vbear.media/library/36015/orange-cat-gets-startled-by-movement-under-a-duvet-and-tumbles-off-the-bed-in-Chongqing-China — nonexclusive licensing, but not automatically free. **권리 계약 전 금지.**
- https://commons.wikimedia.org/wiki/File:Jump.webm — Commons 측 'License review needed' + 저해상도 320×240, 제외.

## 자동화 현재 상태
- 후보 Pexels 3개의 실제 5초 원본 리뷰를 위한 Actions 워크플로 추가:
  `.github/workflows/v28_4_source_audition.yml`
- 입력: `sample/v28_4_candidate_sources.json`
- 다운로드는 이전에 구현·검증한 공식 Pexels 다운로드 경로만 이용하고 접근 제한을 우회하지 않음.
- 아티팩트: 5초 무음 원본 미리보기·후보 프레임·source audition JSON (최대 7일 보관)
- CC0/CC BY Wikimedia 후보는 메타데이터만 등록. **이번 Pexels audition에서 다운로드하거나 자동 채택하지 않음.**

## 실제 컷 통과 규칙
- 첫 1초 안에 무엇이 일어나는지 이해 가능
- 설정→행동→결과(또는 반전)가 같은 클립 안에 존재
- 행동을 직접 보여주는 프레임 명확, 인위적 역재생/합성 오인 금지
- 원본 5개가 서로 다른 행동을 보여주고 순위의 차이가 납득 가능
- 실제 30초 MP4를 검수한 뒤 7항목 100점 재평가
- 소스 음악·인물·로고·브랜드·동물 안전 등 제3자 권리 별도 검토
- 라이선스 메타데이터 및 이용 허가 = 유튜브 재사용 콘텐츠 수익화 허가 아님
- 미확인/낮은 재미 후보 자동 채택 금지

## 외부 검증 참고
- YouTube 채널 수익화 정책: https://support.google.com/youtube/answer/1311392
- YouTube Shorts 수익화 정책: https://support.google.com/youtube/answer/12504220
- Pexels 라이선스: https://www.pexels.com/license/
