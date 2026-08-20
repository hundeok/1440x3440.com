# PortraitFrame: Project Overview

## 1. 프로젝트 개요 (Project Goal)
**PortraitFrame**은 세로로 회전된 1440x3440 초광각(Ultra-wide) 모니터를 위한 '고성능 프리미엄 디지털 액자(Digital Gallery)' 프로젝트입니다. 
시중에 존재하는 일반적인 사진 뷰어 앱들이 무겁고 세로 해상도에 최적화되어 있지 않다는 문제점을 해결하기 위해, **"무조건 가볍고 빠를 것(Zero-latency)", "유휴 리소스를 먹지 않을 것"**이라는 확고한 설계 철학을 바탕으로 제작되었습니다.

## 2. 아키텍처 (Decoupled Architecture)
프로젝트는 성능과 안정성을 극대화하기 위해 역할을 두 개의 독립적인 프로그램으로 완벽하게 분리(Decoupling)했습니다.

### A. Viewer (뷰어)
- **역할:** 로컬에 저장된 1440x3440 사진들을 화면에 띄워주는 초경량 애플리케이션
- **특징:** 인터넷 연결이나 복잡한 연산 없이 순수하게 이미지 렌더링에만 집중합니다.
- **배포:** Mac 전용 독립 실행 앱 (`PortraitFrame.app`) 형태로 패키징되어 있어 클릭 한 번으로 실행되며, 다른 Mac으로 손쉽게 AirDrop 공유가 가능합니다.

### B. Collector (수집기)
- **역할:** 인터넷(Unsplash, Pexels, Wallhaven 등)에서 조건에 맞는 고화질 사진을 긁어오는 무거운 '곡괭이' 도구
- **특징:** 멀티스레딩, 이미지 리사이징/크롭, 해시 기반 중복 검사, 품질 필터링 등 무겁고 복잡한 연산을 뷰어와 완전히 분리된 터미널(CLI) 환경에서 백그라운드로 처리합니다.

## 3. 핵심 디렉토리 구조
```text
portrait_frame/
├── PortraitFrame.app/    # (Mac 전용) 뷰어 실행 파일
├── config.yaml           # 전체 환경설정 (뷰어 및 수집기 설정)
├── .env                  # API 키 등 민감한 인증 정보 (Git에서 제외됨)
├── library/              # 수집된 사진들이 저장되는 메인 데이터베이스
│   ├── images/           # 정규화가 완료된 1440x3440 WebP 사진들
│   └── images.json       # 중복 검사용 해시 및 메타데이터 DB
├── app/                  # 뷰어(Viewer) 소스 코드
├── collector/            # 수집기(Collector) 소스 코드
└── docs/                 # 프로젝트 기술 문서
```
