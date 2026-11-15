# V28.4 후속 후보 발굴 및 실행 기록 (2026-11-15)

## 고정 조건
- 기존 사용자 승인 V28.3 디자인 + 하단 Caption 60pt 변경 금지. 코드 `review/TOP5_TEMPLATE_STYLE_LOCK.md` 준수.
- 영상은 자체 새 편집 이전에 **원본의 실제 동작/결과**를 확인해야 함.
- 게시, 수익화 통과는 여전히 미승인.

## 신규 유망 후보 — 실제 프레임 미확인, 라이선스 출처 우선검토
1. [Cat chasing a pigeon.webm](https://commons.wikimedia.org/wiki/File:Cat_chasing_a_pigeon.webm)
   - 제공자: Jeromi Mikhael. Wikimedia Commons에 본인 촬영 작품·CC0 표시, 원본 29.808초 640x480, 약 17.4MB.
   - 설명: 비둘기를 쫓던 고양이의 실패 장면. **사건→결과가 존재한다고 원본 페이지가 설명하지만, 편집 적합 5초 시점을 실제 프레임으로 확인하지 않았으므로 확정 불가**.
   - 촬영 배경에 행인이 있다면 초상·사용 목적·제3자 권리 점검.
   - 낮은 640×480 해상도로 세로 1080×1920 배치 시 화질 손실 우려.
2. [Moomin1.webm](https://commons.wikimedia.org/wiki/File:Moomin1.webm)
   - 제공자: Tet. Wikimedia Commons 본인 작품·CC0, 원본 약 19초 1080×1920 세로·4.71MB.
   - 설명: 면봉을 갖고 노는 고양이. **세로 화질과 라이선스 상태는 유리하지만 '황당한 반전'인지 실제 동작 검수 전 확정 불가**.
3. [Sammy springt.webm](https://commons.wikimedia.org/wiki/Category:Videos_of_jumping_cats)
   - 1분 3초·1280×720, 원본 페이지 라이선스 상태 및 행동 검증 미완료.
   - 자동 메타데이터 필터에서 CC0/CC BY 외 권리면 제외.

## 추가 실행 환경
- 신규 검수 스크립트: `src/v28_4_story_candidate_audition.py`
- 자동 검수 워크플로: `.github/workflows/v28_4_story_candidate_audition.yml`
- 소스 확보: Wikimedia 공식 API/공식 업로드 도메인만. 동영상 원본을 외부 사이트에서 임의 재업로드 하지 않음.
- 최대 2개 영상 당 5초 무음 미리보기와 대표 프레임 생성, 메타데이터·권리 미확인 정보 JSON 기록.
- 2026-11-15 후속 검수 워크플로 신규 등록 완료. **GitHub Actions 작업 실행/아티팩트 생성은 현재 조회 시점에 확인되지 않아 미완료**.
- 자동실행이 발생하지 않을 경우 GitHub Actions에서 `TOP5 V28.4 - story payoff candidate audition`을 선택하여 `Run workflow`로 수동 트리거 필요.
- 실제 렌더 가능한 새 장면 3개가 검증되기 전까지 V28.4 본편 제작/게시 판정 보류.

## 판단 원칙
- 같은 점프·놀이 행위를 반복하면 순위 차별성이 무너진다.
- CC0/CC BY 표시와 이용 조건 충족은 유튜브 재사용 콘텐츠 수익화 승인을 보장하지 않는다.
- 실제 원본 행위가 명확하고 창작자 독자 기여가 있는 콘텐츠만 다음 단계로 이동.
