"""
collector/sources/generic.py
──────────────────────────────
Generic URL 목록 소스 어댑터.

config.yaml 에서 url_file 경로를 지정하면
해당 파일의 URL 목록을 이미지 후보로 반환한다.

url_file 형식 (한 줄에 URL 하나):
  https://example.com/image1.jpg
  https://example.com/image2.png
"""
from __future__ import annotations

import logging
from pathlib import Path

from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)


class GenericAdapter(BaseSourceAdapter):

    @property
    def name(self) -> str:
        return "generic"

    def __init__(self, config: dict):
        super().__init__(config)
        g_cfg = config.get("sources", {}).get("generic", {})
        self.url_file: str = g_cfg.get("url_file", "")

    def discover(self, query: str = "", limit: int = 50, **kwargs) -> list[ImageCandidate]:
        if not self.url_file:
            logger.warning("[generic] url_file not set in config")
            return []

        path = Path(self.url_file)
        if not path.exists():
            logger.error("[generic] url_file not found: %s", path)
            return []

        urls = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        candidates = []
        for url in urls[:limit]:
            candidates.append(ImageCandidate(
                source="generic",
                source_url=url,
                image_url=url,
                width=0,   # 알 수 없음 — downloader 후 확인
                height=0,
            ))

        logger.info("[generic] %d URLs loaded from %s", len(candidates), self.url_file)
        return candidates
