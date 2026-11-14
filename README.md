# TOP5 CC Shorts Auto — V1 (한국어 안내)

**주제 검색 → Wikimedia Commons CC BY·CC0 영상 자동 발견 → 5개 파일 자동 다운로드 → 30초 TOP5 세로영상 초안 → 출처·권리 검토 자료 출력**

이 프로젝트는 **검수용 초안 자동 생성기**입니다. 자동 업로드하거나 원본 사용권을 자동으로 보증하지 않습니다. 유튜브 광고 수익화도 보장하지 않습니다.

## 휴대폰으로 실행하기 (최초 설정 1회)

1. GitHub에서 새 저장소를 만듭니다. 예: `top5-shorts-auto`. 실행용 GitHub Actions를 쓰려면 `.github/workflows/top5.yml`이 저장소의 **기본 브랜치**에 있어야 합니다.
2. 이 ZIP의 **압축을 풀어 내부 파일 및 폴더 구조 그대로** 저장소에 올립니다. ZIP 파일 하나만 업로드하면 워크플로는 작동하지 않습니다. 직접 올리기 어렵다면 저장소 URL을 ChatGPT에 알려 코드를 넣는 방법을 안내받으세요.
3. GitHub 모바일 앱 또는 웹에서 저장소 → **Actions** → `TOP5 CC Shorts - discover and draft` → **Run workflow**를 누릅니다.
4. `mode = discover`이면 검색 후보와 출처 목록만 생성합니다. `mode = draft`이면 권리 정보가 기록된 영상 5개 다운로드 및 30초 검수 초안까지 시도합니다.
5. 완료된 Actions 실행 화면의 **Artifacts**에서 `TOP5-shorts-review-...` ZIP을 내려받으면 `TOP5_DRAFT_REVIEW_ONLY_1080x1920.mp4` 등 결과물이 있습니다.

> `Run workflow`가 없으면 워크플로가 기본 브랜치에 배치됐는지, Actions 권한이 켜져 있는지 확인합니다.

## 설정

- `topic`: 영어 검색어 예: `funny cats`, `dog playing`, `kitten playing`
- `title`: 화면 상단 한국어 제목
- `mode=discover`: CC 메타데이터 후보 확인만. 무료/빠름.
- `mode=draft`: 후보 수집 → 5개 원본 파일 자동 다운로드 → 자동 편집. 원본 영상 길이가 너무 짧거나 API 요청이 제한되면 실패하며, 성공을 가장하지 않습니다.
- `sample/script.json`: 편집 중 표시되는 장면별 한국어 자막. 기본 문구는 임시 문구이므로 **실제 영상 확인 후 독창적 해설·스토리로 바꿔야** 수익화 품질을 갖춥니다.

## 영상 구성 (30초)

- 00–02초: 1위 영상 티저 + 제목
- 02–07초: 5위
- 07–12초: 4위
- 12–17초: 3위
- 17–22초: 2위
- 22–27초: 1위
- 27–30초: 다시보기와 댓글 유도

영상은 1080×1920, H.264/AAC, 24fps이며 원본 오디오를 **의도적으로 제거**합니다(저작권 문제가 있는 배경 음악 전파 방지). 검수 초안의 오디오 트랙은 무음입니다. 대사는 별도 TTS 음성 파일을 입력해 제작하거나 추후 기능으로 연결해야 합니다. 기본 랭킹 문구와 자막만 있는 초안은 유튜브 수익화용 완성본이 아닙니다.

## 권리와 제한

- Wikimedia Commons `LicenseUrl`에 **정확히 CC BY 2.0/2.5/3.0/4.0 또는 CC0 1.0이 표시되는 파일만** 수집합니다. BY-SA, NC, ND 등은 자동 후보에서 제외합니다.
- 이 필터는 **신고된 메타데이터**만 검사하며 원본 제작자·음악·출연자·브랜드 등 제3자 권리를 검증하지 못합니다. `RIGHTS_CHECKLIST.md` 확인 필수.
- 최소 길이 5.25초, 파일당 약 60MiB, 총 약 220MiB 이하로 제한합니다. API 데이터 오류·다운로드 오류·후보 부족이면 실패합니다.
- 초안의 순위는 **검색 목록 순서**입니다. 재미·완성도 순위가 아닙니다. 공개 전 꼭 직접 판단하세요.
- 작품별 출처·창작자·라이선스·변경 사항은 `YOUTUBE_CREDITS.txt`에서 확인하고, 라이선스 조건에 따라 실제 설명란에 표시하세요.
- CC BY라 하더라도 유튜브의 `재사용 콘텐츠` 규정으로 수익화가 거절될 수 있습니다. 독창적 해설·분석·유머·재편집을 추가하세요.
- GitHub Actions의 사용 가능 시간, 아티팩트 저장 기간 및 저장소 공개 범위는 본인 설정·요금제에 따라 다릅니다. 공개 저장소에서는 Actions 결과물과 원본 출처가 노출될 수 있습니다.
- 영상 화면은 기존 특정 채널의 직접 복제품이 아닌 TOP5 형식의 자체 디자인입니다.

## 로컬 개발 테스트

Python 3.10+ / FFmpeg + ffprobe / 한글 NanumSquare 폰트 필요.

```bash
python3 -m unittest discover -s tests -v
python3 src/top5.py --mode discover --topic 'cat playing' --output output
python3 src/top5.py --mode draft --topic 'cat playing' --output output
```

외부 네트워크가 막힌 환경에서도 5개 로컬 영상 파일의 테스트용 JSON 목록으로 렌더만 검증할 수 있습니다.

```bash
python3 src/top5.py --mode local-test --local-manifest local.json --size 360x640 --output test-output
```

> `local.json`에는 `title`, `source_page`, `author`, `license`, `license_url`, `review_flags`, `local_path`, `duration`을 가진 영상 5개 객체 배열이 필요합니다.

## 자료

- Wikimedia Commons 라이선스: https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- MediaWiki API imageinfo: https://www.mediawiki.org/wiki/API:Imageinfo
- GitHub Actions: https://docs.github.com/en/actions/how-tos/manage-workflow-runs
- YouTube 정책: https://support.google.com/youtube/answer/1311392
## V2: 순위 이름과 전체 화면

- 1~5위 각각의 이름을 원본 파일명으로 표시합니다. sample/script.json의 source_names에서 한국어 이름을 원본 제목별로 지정할 수 있습니다.
- 기존 블러 배경 대신 9:16 화면을 원본 영상으로 채웁니다. 가로 영상은 좌우가 잘릴 수 있습니다.
- focus_overrides에 원본 제목별 가로 위치값(0.0~1.0)을 지정할 수 있습니다. 자동 위치는 움직임 기반 근사치이며 피사체 식별은 아닙니다.
- SHOTLIST_FOR_REVIEW.json에 구간별 원본·시작시각·초점 위치가 기록됩니다.
- 게시 전 검수용 초안입니다. 웃긴 순간 자체의 자동 이해, 음악/출연자 권리 확인, 해설 TTS와 코믹 효과음은 아직 자동 완료되지 않습니다.
