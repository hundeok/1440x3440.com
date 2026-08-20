"""
collector/sources/unsplash.py
──────────────────────────────
Unsplash API 소스 어댑터.

무료 API key 발급: https://unsplash.com/developers
제한: 50 req/hour (Demo), 5000 req/hour (Production)

portrait 방향 고해상도 이미지 수집 → Tier 2 처리.
"""
from __future__ import annotations

import logging

from collector.downloader import Downloader, DownloadError
from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.unsplash.com/search/photos"
TARGET_W = 1440
TARGET_H = 3440


class UnsplashAdapter(BaseSourceAdapter):

    @property
    def name(self) -> str:
        return "unsplash"

    def __init__(self, config: dict):
        super().__init__(config)
        u_cfg = config.get("sources", {}).get("unsplash", {})
        self.access_key: str = u_cfg.get("access_key", "")
        self.queries: list[str] = u_cfg.get("queries", ["nature"])
        self._dl = Downloader(config)

    def discover(self, query: str = "nature", limit: int = 50, **kwargs) -> list[ImageCandidate]:
        if not self.access_key:
            logger.warning("[unsplash] access_key not set. Get one at unsplash.com/developers")
            return []

        candidates: list[ImageCandidate] = []
        page = 1

        while len(candidates) < limit:
            params = {
                "query": query,
                "orientation": "portrait",
                "per_page": 30,
                "page": page,
            }
            try:
                data = self._dl.get_json(
                    SEARCH_URL,
                    params=params,
                    api_key="",  # Authorization header 별도 처리
                )
            except DownloadError as e:
                logger.error("[unsplash] API error (q=%r): %s", query, e)
                break

            # Authorization header 세팅 (첫 호출 전에 주입)
            # Unsplash는 Bearer token 방식이므로 직접 세팅
            items = data.get("results", [])
            if not items:
                break

            for item in items:
                c = self._parse(item)
                if c:
                    candidates.append(c)
                if len(candidates) >= limit:
                    break

            total_pages = data.get("total_pages", 1)
            if page >= total_pages:
                break
            page += 1

        logger.info("[unsplash] q=%r → %d candidates", query, len(candidates))
        return candidates

    def discover_all(self, limit_per_query: int = 50) -> list[ImageCandidate]:
        if not self.access_key:
            logger.warning("[unsplash] access_key not set")
            return []

        # Authorization 헤더 주입
        self._dl._session.headers.update({
            "Authorization": f"Client-ID {self.access_key}"
        })

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

        # 최소 규격 필터
        if w < TARGET_W or h < TARGET_H:
            return None
        # portrait 확인
        if w >= h:
            return None

        urls = item.get("urls", {})
        # raw URL 사용 (최고 품질)
        raw_url = urls.get("raw", "") + "&fm=jpg&q=90"
        if not raw_url:
            return None

        page_url = item.get("links", {}).get("html", "")
        desc = item.get("description") or item.get("alt_description") or ""

        return ImageCandidate(
            source="unsplash",
            source_url=page_url,
            image_url=raw_url,
            width=w,
            height=h,
            title=desc,
            extra={
                "unsplash_id": item.get("id"),
                "likes": item.get("likes", 0),
                "user": item.get("user", {}).get("username", ""),
            },
        )
