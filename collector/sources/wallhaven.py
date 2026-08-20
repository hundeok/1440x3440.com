"""
collector/sources/wallhaven.py
────────────────────────────────
Wallhaven API 소스 어댑터.

API 문서: https://wallhaven.cc/help/api
검색 엔드포인트: https://wallhaven.cc/api/v1/search

Tier 1: resolutions=1440x3440 (exact match)
Tier 2: atleast=1440x3440 + ratios=portrait (larger portrait images)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from collector.downloader import Downloader, DownloadError
from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)

SEARCH_URL = "https://wallhaven.cc/api/v1/search"
TARGET_W = 1440
TARGET_H = 3440


class WallhavenAdapter(BaseSourceAdapter):

    # ──────────────────────────────────────────
    # 검색 쿼리 정의
    # ──────────────────────────────────────────

    # Tier 1: 정확히 1440×3440 인 이미지
    QUERIES_TIER1 = [
        {"q": "",               "tier": 1},
        {"q": "dark",           "tier": 1},
        {"q": "architecture",   "tier": 1},
        {"q": "nature",         "tier": 1},
        {"q": "space",          "tier": 1},
        {"q": "minimal",        "tier": 1},
        {"q": "city",           "tier": 1},
        {"q": "forest",         "tier": 1},
        {"q": "abstract",       "tier": 1},
        {"q": "cyberpunk",      "tier": 1},
        {"q": "mountain",       "tier": 1},
        {"q": "photography",    "tier": 1},
    ]

    # Tier 2: 1440×3440 이상 portrait 이미지
    QUERIES_TIER2 = [
        {"q": "vertical ultrawide",  "tier": 2},
        {"q": "portrait ultrawide",  "tier": 2},
        {"q": "vertical wallpaper",  "tier": 2},
        {"q": "dark architecture",   "tier": 2},
        {"q": "minimal dark",        "tier": 2},
        {"q": "forest night",        "tier": 2},
        {"q": "space galaxy",        "tier": 2},
        {"q": "city rain",           "tier": 2},
    ]

    @property
    def name(self) -> str:
        return "wallhaven"

    def __init__(self, config: dict):
        super().__init__(config)
        wh_cfg = config.get("sources", {}).get("wallhaven", {})
        self.api_key: str = wh_cfg.get("api_key", "")
        self.purity: str = wh_cfg.get("purity", "100")
        self.categories: str = wh_cfg.get("categories", "100")
        self._downloader = Downloader(config)

    def get_queries(self) -> list[dict]:
        return self.QUERIES_TIER1 + self.QUERIES_TIER2

    # ──────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────

    def discover(self, query: str = "", limit: int = 50, tier: int = 1) -> list[ImageCandidate]:
        """
        query 로 이미지 후보를 검색한다.
        tier=1: 정확히 1440×3440
        tier=2: atleast 1440×3440 + portrait
        """
        candidates: list[ImageCandidate] = []
        page = 1

        while len(candidates) < limit:
            params = self._build_params(query, tier, page)
            try:
                data = self._downloader.get_json(SEARCH_URL, params=params, api_key=self.api_key)
            except DownloadError as e:
                logger.error("[wallhaven] API error (q=%r, page=%d): %s", query, page, e)
                break

            items = data.get("data", [])
            if not items:
                break

            for item in items:
                c = self._parse_item(item)
                if c:
                    candidates.append(c)
                if len(candidates) >= limit:
                    break

            # 다음 페이지
            meta = data.get("meta", {})
            last_page = meta.get("last_page", 1)
            if page >= last_page:
                break
            page += 1

        logger.info("[wallhaven] query=%r tier=%d → %d candidates", query, tier, len(candidates))
        return candidates

    def discover_all(self, limit_per_query: int = 50) -> list[ImageCandidate]:
        """전체 쿼리 목록을 순회하며 후보 수집."""
        all_candidates: list[ImageCandidate] = []
        seen_urls: set[str] = set()

        for q_info in self.QUERIES_TIER1 + self.QUERIES_TIER2:
            q = q_info["q"]
            tier = q_info["tier"]
            results = self.discover(q, limit=limit_per_query, tier=tier)
            for c in results:
                if c.image_url not in seen_urls:
                    seen_urls.add(c.image_url)
                    all_candidates.append(c)

        return all_candidates

    # ──────────────────────────────────────────
    # 내부 로직
    # ──────────────────────────────────────────

    def _build_params(self, query: str, tier: int, page: int) -> dict:
        params: dict = {
            "categories": self.categories,
            "purity": self.purity,
            "sorting": "relevance",
            "order": "desc",
            "page": page,
        }
        if query:
            params["q"] = query

        if tier == 1:
            params["resolutions"] = f"{TARGET_W}x{TARGET_H}"
        else:
            params["atleast"] = f"{TARGET_W}x{TARGET_H}"
            params["ratios"] = "portrait"

        return params

    @staticmethod
    def _parse_item(item: dict) -> Optional[ImageCandidate]:
        """API 응답 아이템을 ImageCandidate 로 변환."""
        image_url = item.get("path", "")
        if not image_url:
            return None

        w = item.get("dimension_x", 0)
        h = item.get("dimension_y", 0)

        # 최소 규격 미달 탈락
        if w < TARGET_W or h < TARGET_H:
            return None

        # Landscape 탈락 (세로가 더 짧은 이미지)
        if w > h:
            return None

        page_url = item.get("url", f"https://wallhaven.cc/w/{item.get('id', '')}")
        tags = [t.get("name", "") for t in item.get("tags", []) if t.get("name")]

        return ImageCandidate(
            source="wallhaven",
            source_url=page_url,
            image_url=image_url,
            width=w,
            height=h,
            tags=tags,
            extra={
                "wallhaven_id": item.get("id"),
                "views": item.get("views", 0),
                "favorites": item.get("favorites", 0),
                "category": item.get("category", ""),
                "purity": item.get("purity", ""),
                "file_type": item.get("file_type", ""),
                "file_size": item.get("file_size", 0),
            },
        )
