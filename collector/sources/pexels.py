"""
collector/sources/pexels.py
────────────────────────────
Pexels API 소스 어댑터.

무료 API key 발급: https://www.pexels.com/api
제한: 200 req/hour, 20,000 req/month

portrait 방향 고해상도 이미지 수집 → Tier 2 처리.
"""
from __future__ import annotations

import logging

from collector.downloader import Downloader, DownloadError
from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.pexels.com/v1/search"
TARGET_W = 1440
TARGET_H = 3440


class PexelsAdapter(BaseSourceAdapter):

    @property
    def name(self) -> str:
        return "pexels"

    def __init__(self, config: dict):
        super().__init__(config)
        p_cfg = config.get("sources", {}).get("pexels", {})
        self.api_key: str = p_cfg.get("api_key", "")
        self.queries: list[str] = p_cfg.get("queries", ["nature"])
        self._dl = Downloader(config)

    def discover(self, query: str = "nature", limit: int = 50, **kwargs) -> list[ImageCandidate]:
        if not self.api_key:
            logger.warning("[pexels] api_key not set. Get one at pexels.com/api")
            return []

        self._dl._session.headers.update({"Authorization": self.api_key})

        candidates: list[ImageCandidate] = []
        page = 1

        while len(candidates) < limit:
            params = {
                "query": query,
                "orientation": "portrait",
                "size": "large",     # width >= 1920
                "per_page": 80,
                "page": page,
            }
            try:
                data = self._dl.get_json(SEARCH_URL, params=params)
            except DownloadError as e:
                logger.error("[pexels] API error (q=%r): %s", query, e)
                break

            items = data.get("photos", [])
            if not items:
                break

            for item in items:
                c = self._parse(item)
                if c:
                    candidates.append(c)
                if len(candidates) >= limit:
                    break

            # 다음 페이지
            if not data.get("next_page"):
                break
            page += 1

        logger.info("[pexels] q=%r → %d candidates", query, len(candidates))
        return candidates

    def discover_all(self, limit_per_query: int = 50) -> list[ImageCandidate]:
        if not self.api_key:
            logger.warning("[pexels] api_key not set")
            return []

        all_candidates: list[ImageCandidate] = []
        seen: set[str] = set()

        for q in self.queries:
            results = self.discover(q, limit=limit_per_query)
            for c in results:
                if c.image_url not in seen:
                    seen.add(c.image_url)
                    all_candidates.append(c)

        return all_candidates

    @staticmethod
    def _parse(item: dict) -> ImageCandidate | None:
        w = item.get("width", 0)
        h = item.get("height", 0)

        if w < TARGET_W or h < TARGET_H:
            return None
        if w >= h:
            return None

        # 최고 품질 URL (original)
        src = item.get("src", {})
        image_url = src.get("original", "")
        if not image_url:
            return None

        page_url = item.get("url", "")
        photographer = item.get("photographer", "")

        return ImageCandidate(
            source="pexels",
            source_url=page_url,
            image_url=image_url,
            width=w,
            height=h,
            extra={
                "pexels_id": item.get("id"),
                "photographer": photographer,
                "avg_color": item.get("avg_color", ""),
            },
        )
