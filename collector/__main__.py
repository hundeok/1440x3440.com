"""
collector/__main__.py
──────────────────────
CLI 진입점.

사용법:
  python -m collector collect                     # 모든 소스에서 수집
  python -m collector collect --source wallhaven  # 특정 소스만
  python -m collector collect --limit 50          # 최대 50장
  python -m collector normalize                   # 정규화 재실행
  python -m collector audit                       # 라이브러리 검사
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml


def _setup_logging(config: dict) -> None:
    log_cfg = config.get("log", {})
    level_str = log_cfg.get("level", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)
    log_file = log_cfg.get("file", "./logs/collector.log")

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


import os
from dotenv import load_dotenv

def _load_config(path: str = "config.yaml") -> dict:
    load_dotenv()
    p = Path(path)
    if not p.exists():
        print(f"ERROR: config file not found: {p.resolve()}")
        sys.exit(1)
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Override keys with environment variables if present
    sources = data.setdefault("sources", {})
    if "WALLHAVEN_API_KEY" in os.environ:
        sources.setdefault("wallhaven", {})["api_key"] = os.environ["WALLHAVEN_API_KEY"]
    if "UNSPLASH_ACCESS_KEY" in os.environ:
        sources.setdefault("unsplash", {})["access_key"] = os.environ["UNSPLASH_ACCESS_KEY"]
    if "PEXELS_API_KEY" in os.environ:
        sources.setdefault("pexels", {})["api_key"] = os.environ["PEXELS_API_KEY"]
    if "FLICKR_API_KEY" in os.environ:
        sources.setdefault("flickr", {})["api_key"] = os.environ["FLICKR_API_KEY"]

    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="collector",
        description="PortraitFrame — 1440×3440 이미지 수집기",
    )
    parser.add_argument(
        "--config", default="config.yaml", help="config 파일 경로 (기본: config.yaml)"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # collect
    p_collect = sub.add_parser("collect", help="이미지 수집")
    p_collect.add_argument("--source", help="특정 소스 이름 (예: wallhaven)")
    p_collect.add_argument("--limit", type=int, default=None, help="소스당 최대 수집 수")

    # normalize
    sub.add_parser("normalize", help="라이브러리 정규화 재실행")

    # audit
    sub.add_parser("audit", help="라이브러리 무결성 검사")

    args = parser.parse_args()

    # 프로젝트 루트를 CWD 기준으로 설정
    config = _load_config(args.config)
    _setup_logging(config)

    from collector.collector import Collector
    collector = Collector(config)

    if args.command == "collect":
        source_names = [args.source] if args.source else None
        collector.collect(source_names=source_names, limit=args.limit)

    elif args.command == "normalize":
        collector.normalize()

    elif args.command == "audit":
        collector.audit()


if __name__ == "__main__":
    import logging
    import warnings
    from PIL import Image
    
    # [Optimization] 초고해상도 메모리 폭탄 방어: 경고를 에러로 격상시켜 수집 단계에서 즉각 폐기
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Notice] 수집 작업이 사용자에 의해 안전하게 취소되었습니다. (Graceful Exit)")
        import sys
        sys.exit(0)
