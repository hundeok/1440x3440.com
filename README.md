# PortraitFrame

세로 UWQHD(1440×3440) 전용 디지털 액자 + 이미지 수집/큐레이션 엔진.

## 빠른 시작

```bash
# 1. 가상환경 생성 및 의존성 설치
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. config.yaml 편집 — Wallhaven API key 설정 (선택사항)
#    wallhaven.cc/settings 에서 API key 발급
#    api_key: "" → api_key: "YOUR_KEY"

# 3. 이미지 수집 (처음에는 소량으로 테스트)
python -m collector collect --source wallhaven --limit 20

# 4. 라이브러리 검사
python -m collector audit

# 5. 뷰어 실행
python viewer.py
```

## CLI 명령어

```bash
# 수집
python -m collector collect                      # 모든 소스
python -m collector collect --source wallhaven   # Wallhaven만
python -m collector collect --limit 50           # 최대 50장

# 검사
python -m collector audit

# 정규화 재실행 (보통 불필요)
python -m collector normalize
```

## 뷰어 키보드 단축키

| 키 | 동작 |
|----|------|
| `→` / `←` | 다음 / 이전 |
| `SPACE` | 일시정지 / 재생 |
| `F` | 즐겨찾기 ❤ |
| `X` | 제거 ✕ |
| `R` | 랜덤 모드 |
| `S` | 순서대로 모드 |
| `ESC` | 전체화면 해제 |
| `Q` | 종료 |

## 이미지 규격

**모든 이미지는 정확히 1440×3440 px** 이어야 합니다.  
이 조건을 위반하는 파일은 library/images/ 에 존재할 수 없습니다.

```bash
python -m collector audit
# ✓ Audit passed — all files are valid 1440×3440
```

## 프로젝트 구조

```
portrait_frame/
├── app/
│   ├── config.py      # config.yaml 로더
│   ├── controls.py    # 키보드 바인딩
│   └── viewer.py      # Tkinter 뷰어
├── collector/
│   ├── collector.py   # 메인 오케스트레이터
│   ├── downloader.py  # HTTP 다운로더
│   ├── normalizer.py  # 1440×3440 변환
│   ├── quality.py     # 품질 필터
│   ├── dedupe.py      # SHA256 + pHash 중복 제거
│   ├── library.py     # images.json 관리
│   └── sources/
│       ├── wallhaven.py
│       ├── reddit.py  # (Phase 1F)
│       └── generic.py
├── library/
│   ├── images/        # 최종 1440×3440 .webp 파일
│   ├── originals/     # 원본 (keep_originals: true 시)
│   └── images.json    # 메타데이터 DB
├── rejected/          # X 누른 이미지
├── logs/
├── config.yaml
├── requirements.txt
└── viewer.py          # 진입점
```

## Wallhaven API Key

API key 없이도 SFW public 이미지 수집 가능.  
API key가 있으면 더 많은 검색 옵션 사용 가능.

1. [wallhaven.cc/settings](https://wallhaven.cc/settings) 에서 발급
2. `config.yaml` 의 `api_key` 필드에 입력

## 목표

- 1차: 50~100장 (실제 모니터에서 화질 확인)
- 2차: 500장
- 3차: 1,000장+

## Phase 계획

| Phase | 내용 |
|-------|------|
| 1A | Skeleton ✓ |
| 1B | Image processor ✓ |
| 1C | Wallhaven adapter ✓ |
| 1D | Python viewer ✓ |
| 1E | 실제 모니터 테스트 |
| 1F | Reddit + 추가 소스 |
| 2 | 큐레이션 엔진 (취향 학습) |
| 3 | 카테고리/채널 |
| 4 | Web viewer |
| 5 | R2 외부 스토리지 |
