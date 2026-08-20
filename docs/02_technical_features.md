# PortraitFrame: Technical Features

## 1. Zero-Latency Viewer (PyQt6)
- **하드웨어 가속:** PyQt6의 QGraphicsView 시스템을 활용하여 끊김 없는 부드러운 이미지 전환(Fade, Zoom 등)을 구현했습니다.
- **백그라운드 프리페칭(Prefetching):** 다음 슬라이드로 넘어갈 이미지를 미리 메모리에 올려두어 로딩 딜레이(Zero-latency)를 완벽하게 제거했습니다.
- **Wakelock:** 뷰어가 켜져 있는 동안 화면이 꺼지거나 잠자기 모드로 진입하지 않도록 방지하는 기능이 내장되어 있습니다.

## 2. Advanced Image Processing (Pillow & ImageHash)
수집기(Collector)는 단순히 이미지를 다운로드하는 것을 넘어, 철저한 품질 관리를 수행합니다.

- **비율 기반 자동 크롭:** 원본 이미지가 1440x3440 비율이 아닐 경우, 중심부(Center)를 기준으로 가장 예쁜 구도로 자동 크롭 및 리사이징하여 WebP로 압축 저장합니다.
- **Laplacian Variance (블러 필터):** 초점이 나갔거나 흐릿한 사진을 수학적으로 계산하여 자동으로 버립니다.
- **Standard Deviation (단색/깨짐 필터):** 이미지의 픽셀 편차를 검사하여 데이터가 유실되어 단색으로 렌더링되거나 깨진 파일들을 정확하게 잡아내어 폐기합니다.

## 3. Intelligent Deduplication (중복 방지 시스템)
인터넷에서 무작위로 사진을 긁어올 때 발생하는 동일/유사 이미지 중복 저장 문제를 해결했습니다.

- **SHA-256 해시:** 파일 자체가 완벽히 동일한 경우를 걸러냅니다.
- **Perceptual Hash (pHash):** 이미지를 흑백으로 변환하고 축소하여 시각적 구조의 해시값을 추출합니다. 해상도가 다르거나 약간 크롭된 사진이더라도 '시각적으로 같은 사진'이라면 Hamming Distance를 계산해 똑똑하게 걸러냅니다. (Threshold <= 8)

## 4. Secure Credential Management (보안)
- `python-dotenv`를 도입하여 Wallhaven, Unsplash, Pexels 등의 API 키를 소스 코드나 `config.yaml`에 하드코딩하지 않습니다.
- 로컬의 `.env` 파일에서 실행 시간에 환경 변수를 주입받아 작동하므로, GitHub 등 오픈소스 공간에 코드를 안전하게 공유할 수 있습니다.
