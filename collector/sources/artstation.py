"""
collector/sources/artstation.py
ArtStation 공개 API 소스 어댑터. API key 불필요.
"""
from __future__ import annotations
import logging
import time
from collector.downloader import Downloader, DownloadError
from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)
TARGET_W = 1440
TARGET_H = 3440
SECTIONS = [
    "https://www.artstation.com/api/v2/artworks.json?page={page}&per_page=50&sorting=trending",
    "https://www.artstation.com/api/v2/artworks.json?page={page}&per_page=50&sorting=latest",
]

class ArtstationAdapter(BaseSourceAdapter):
    @property
    def name(self) -> str:
        return "artstation"

    def __init__(self, config: dict):
        super().__init__(config)
        a_cfg = config.get("sources", {}).get("artstation", {})
        self.pages_per_section: int = int(a_cfg.get("pages_per_section", 3))
        self._dl = Downloader(config)
        self._dl._session.headers.update({
            "Referer": "https://www.artstation.com/",
            "Accept": "application/json",
        })

    def discover_all(self, limit_per_query: int = 50) -> list[ImageCandidate]:
        all_candidates: list[ImageCandidate] = []
        seen: set[str] = set()
        for section_tmpl in SECTIONS:
            for page in range(1, self.pages_per_section + 1):
                url = section_tmpl.format(page=page)
                try:
                    data = self._dl.get_json(url)
                except DownloadError as e:
                    logger.error("[artstation] fetch failed: %s", e)
                    break
                items = data.get("data", [])
                if not items:
                    break
                for item in items:
                    for c in self._parse_artwork(item):
                        if c.image_url not in seen:
                            seen.add(c.image_url)
                            all_candidates.append(c)
                time.sleep(1.0)
        logger.info("[artstation] %d candidates", len(all_candidates))
        return all_candidates

    def discover(self, query: str = "", limit: int = 50, **kwargs) -> list[ImageCandidate]:
        return self.discover_all()[:limit]

    @staticmethod
    def _parse_artwork(item: dict) -> list[ImageCandidate]:
        candidates = []
        page_url = item.get("permalink", "")
        title = item.get("title", "")
        username = item.get("user", {}).get("username", "")
        for asset in item.get("assets", []):
            if asset.get("asset_type") != "image":
                continue
            w = int(asset.get("width", 0) or 0)
            h = int(asset.get("height", 0) or 0)
            if w < TARGET_W or h < TARGET_H:
                continue
            if w >= h:
                continue
            img_url = asset.get("image_url", "")
            if not img_url:
                continue
            candidates.append(ImageCandidate(
                source="artstation",
                source_url=page_url,
                image_url=img_url,
                width=w, height=h,
                title=title,
                extra={"artist": username, "asset_id": asset.get("id")},
            ))
        return candidates
