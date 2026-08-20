"""
collector/sources/reddit.py
────────────────────────────
Reddit JSON API 소스 어댑터.

API key 불필요 (public subreddit JSON endpoint 사용).
고해상도 portrait 이미지를 수집해 Tier 2 처리.

지원 subreddit 예:
  VerticalWallpapers, wallpaper, EarthPorn, spaceporn,
  CityPorn, ArchitecturePorn, amoledbackgrounds, AbstractWallpapers
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from collector.downloader import Downloader, DownloadError
from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)

TARGET_W = 1440
TARGET_H = 3440

# 이미지 직접 링크로 끝나는 도메인
DIRECT_DOMAINS = {"i.redd.it", "i.imgur.com", "imgur.com"}
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


class RedditAdapter(BaseSourceAdapter):

    @property
    def name(self) -> str:
        return "reddit"

    def __init__(self, config: dict):
        super().__init__(config)
        r_cfg = config.get("sources", {}).get("reddit", {})
        self.subreddits: list[str] = r_cfg.get("subreddits", ["VerticalWallpapers"])
        self.sort: str = r_cfg.get("sort", "hot")
        self.time: str = r_cfg.get("time", "month")
        self.limit_per_sub: int = int(r_cfg.get("limit_per_sub", 100))
        self._dl = Downloader(config)
        # Reddit 공식 User-Agent 규격: platform:appid:version (by /u/username)
        self._dl._session.headers.update({
            "User-Agent": "python:PortraitFrame:v1.0 (by /u/hdcho102303)",
            "Accept": "application/json",
        })

    def discover(self, query: str = "", limit: int = 50, **kwargs) -> list[ImageCandidate]:
        """단일 subreddit 에서 후보 수집 (query = subreddit 이름)."""
        subreddit = query or (self.subreddits[0] if self.subreddits else "VerticalWallpapers")
        return self._scrape_subreddit(subreddit, limit)

    def discover_all(self, limit_per_query: int = 100) -> list[ImageCandidate]:
        """설정된 모든 subreddit 순회."""
        all_candidates: list[ImageCandidate] = []
        seen: set[str] = set()

        for sub in self.subreddits:
            results = self._scrape_subreddit(sub, self.limit_per_sub)
            for c in results:
                if c.image_url not in seen:
                    seen.add(c.image_url)
                    all_candidates.append(c)
            time.sleep(1.0)  # subreddit 간 대기

        return all_candidates

    # ──────────────────────────────────────────
    # 내부 로직
    # ──────────────────────────────────────────

    def _scrape_subreddit(self, subreddit: str, limit: int) -> list[ImageCandidate]:
        candidates: list[ImageCandidate] = []
        after: Optional[str] = None

        while len(candidates) < limit:
            url = f"https://www.reddit.com/r/{subreddit}/{self.sort}.json"
            params: dict = {"limit": 100, "t": self.time}
            if after:
                params["after"] = after

            try:
                data = self._dl.get_json(url, params=params)
            except DownloadError as e:
                logger.error("[reddit] r/%s fetch failed: %s", subreddit, e)
                break

            posts = data.get("data", {}).get("children", [])
            if not posts:
                break

            for post in posts:
                c = self._parse_post(post.get("data", {}), subreddit)
                if c:
                    candidates.append(c)
                if len(candidates) >= limit:
                    break

            after = data.get("data", {}).get("after")
            if not after:
                break

        logger.info("[reddit] r/%s → %d candidates", subreddit, len(candidates))
        return candidates

    @staticmethod
    def _parse_post(post: dict, subreddit: str) -> Optional[ImageCandidate]:
        url: str = post.get("url", "")
        if not url:
            return None

        # 직접 이미지 링크 확인
        ext = ""
        for e in ALLOWED_EXTS:
            if url.lower().split("?")[0].endswith(e):
                ext = e
                break
        if not ext:
            return None

        # 해상도 정보 추출 (preview 데이터)
        preview = post.get("preview", {})
        images = preview.get("images", [])
        w, h = 0, 0
        if images:
            source = images[0].get("source", {})
            w = source.get("width", 0)
            h = source.get("height", 0)

        # 최소 규격 필터
        if w > 0 and h > 0:
            if w < TARGET_W or h < TARGET_H:
                return None
            # landscape 제거
            if w > h * 1.2:
                return None

        page_url = f"https://www.reddit.com{post.get('permalink', '')}"
        title = post.get("title", "")
        flair = post.get("link_flair_text") or ""

        return ImageCandidate(
            source="reddit",
            source_url=page_url,
            image_url=url,
            width=w,
            height=h,
            title=title,
            extra={
                "subreddit": subreddit,
                "score": post.get("score", 0),
                "flair": flair,
                "post_id": post.get("id", ""),
            },
        )
