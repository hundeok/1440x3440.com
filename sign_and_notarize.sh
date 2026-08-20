#!/bin/bash
# 앱 서명(Codesign) 및 공증(Notarization) 자동화 스크립트

# ==============================================================================
# [설정 부분] - 아래 내용을 대표님의 정보로 채워주세요!
# ==============================================================================
# 1. 키체인에 등록된 개발자 인증서 이름 (security find-identity -v -p codesigning 로 확인)
# 예: "Developer ID Application: GILDONG HONG (ABCDE12345)"
CERTIFICATE_NAME="Developer ID Application: Hundeok Cho (S4P788X68K)"

# 2. 키체인에 등록한 notarytool 프로필 이름 (xcrun notarytool store-credentials 로 생성한 이름)
NOTARY_PROFILE="NOTARY_CREDENTIALS"

# 3. 서명할 앱 파일 이름
APP_NAME="PortraitFrame"
APP_PATH="dist/${APP_NAME}.app"
ZIP_PATH="dist/${APP_NAME}.zip"

# ==============================================================================

echo "🚀 [1/4] 빌드 및 내부 파일 코드 서명 시작..."
# PyInstaller 자체의 서명 기능을 이용해 내부 라이브러리들까지 꼼꼼하게 서명합니다.
python3 -m PyInstaller --clean --noconfirm --windowed \
    --name "${APP_NAME}" \
    --osx-bundle-identifier "com.portraitframe.app" \
    --icon "icon.icns" \
    --codesign-identity "${CERTIFICATE_NAME}" \
    viewer.py

if [ ! -d "$APP_PATH" ]; then
    echo "❌ 앱 빌드에 실패했습니다."
    exit 1
fi

echo "📦 [2/4] 공증을 위해 앱 압축(Zip) 중..."
# 공증 서버에는 zip 파일 형태로 올려야 합니다.
/usr/bin/ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"

echo "☁️ [3/4] 애플 서버에 공증(Notarization) 요청 및 대기 중... (수 분이 걸릴 수 있습니다)"
xcrun notarytool submit "${ZIP_PATH}" --keychain-profile "${NOTARY_PROFILE}" --wait

echo "📎 [4/4] 공증 티켓을 앱에 박아넣기(Stapling)..."
xcrun stapler staple "${APP_PATH}"

echo "🎉 모든 과정이 완료되었습니다!"
echo "이제 ${APP_PATH} 파일은 인터넷을 통해 배포해도 '확인되지 않은 개발자' 경고가 뜨지 않습니다."
