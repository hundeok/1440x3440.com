#!/usr/bin/env python3
"""
viewer.py — PortraitFrame Viewer 진입점

사용법:
  python viewer.py
  python viewer.py --config /path/to/config.yaml
"""
import os
import sys

if getattr(sys, 'frozen', False):
    # PyInstaller로 패키징된 앱(.app) 내부에서 실행 시
    # sys.executable: .../PortraitFrame.app/Contents/MacOS/viewer
    app_bundle_path = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
    # 앱 번들이 위치한 폴더(외부)로 CWD 변경 (config.yaml, library/ 경로 매칭을 위해)
    os.chdir(os.path.dirname(app_bundle_path))

import argparse
import logging
import yaml

from app.config import AppConfig
from app.qt_viewer import PortraitViewer
from PyQt6.QtWidgets import QApplication


def main() -> None:
    parser = argparse.ArgumentParser(description="PortraitFrame — 1440×3440 디지털 액자")
    parser.add_argument("--config", default="config.yaml", help="config 파일 경로")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    try:
        config = AppConfig.from_yaml(args.config)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    app = QApplication(sys.argv)
    viewer = PortraitViewer(config)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
