#!/bin/bash
# Intel Mac 전용 네이티브 빌드 스크립트

echo "인텔 맥 네이티브 빌드를 시작합니다..."

# 1. 꼬임 방지를 위해 새로운 가상 환경 생성
python3 -m venv .venv_intel_native
source .venv_intel_native/bin/activate

# 2. 패키지 설치
python3 -m pip install -U pip
python3 -m pip install pyinstaller PyQt6 pyyaml python-dotenv pillow

# 3. PyInstaller 빌드
# Bundle Identifier를 명시하여 언더바(_)로 인한 Info.plist 파싱 오류를 방지합니다.
python3 -m PyInstaller --clean --noconfirm --windowed \
    --name "PortraitFrame" \
    --osx-bundle-identifier "com.portraitframe.app" \
    --icon "icon.icns" \
    viewer.py

echo "✅ 빌드가 완료되었습니다! dist/ 폴더 안에 PortraitFrame.app 이 생성되었습니다."
