"""
collector/sources/flickr.py
Flickr API 소스 어댑터. 무료 key 필요: https://www.flickr.com/services/api
"""
from __future__ import annotations
import logging
from typing import Optional
from collector.downloader import Downloader, DownloadError
from collector.sources.base import BaseSourceAdapter, ImageCandidate

logger = logging.getLogger(__name__)
API_URL = "https://www.flickr.com/services/rest/"
TARGET_W = 1440
TARGET_H = 3440

class FlickrAdapter(BaseSourceAdapter):
    @property
    def name(self) -> str:
        return "flickr"

    def __init__(self, config: dict):
        super().__init__(config)
        f_cfg = config.get("sources", {}).get("flickr", {})
        self.api_key: str = f_cfg.get("api_key", "")
        self.queries: list[str] = f_cfg.get("queries", ["portrait nature"])
        self._dl = Downloader(config)

    def discover(self, query: str = "portrait", limit: int = 50, **kwargs) -> list[ImageCandidate]:
        if not self.api_key:
            logger.warning("[flickr] api_key not set. Get one at flickr.com/services/api")
            return []
        candidates: list[ImageCandidate] = []
        page = 1
        while len(candidates) < limit:
            params = {
                "method": "flickr.photos.search",
                "api_key": self.api_key,
                "text": query,
                "orientation": "portrait",
                "extras": "url_o,o_dims,url_k,k_dims,url_h,h_dims",
                "format": "json",
                "nojsoncallback": "1",
                "sort": "interestingness-desc",
                "content_type": "1",
                "media": "photos",
                "per_page": "100",
                "page": str(page),
                "license": "1,2,3,4,5,6,9,10",
            }
            try:
                data = self._dl.get_json(API_URL, params=params)
            except DownloadError as e:
                logger.error("[flickr] API error (q=%r): %s", query, e)
                break
            photos = data.get("photos", {})
            items = photos.get("photo", [])
            if not items:
                break
            for item in items:
                c = self._parse(item)
                if c:
                    candidates.append(c)
                if len(candidates) >= limit:
                    break
            pages = photos.get("pages", 1)
            if page >= pages:
                break
            page += 1
        logger.info("[flickr] q=%r -> %d candidates", query, len(candidates))
        return candidates

    def discover_all(self, limit_per_query: int = 50) -> list[ImageCandidate]:
        if not self.api_key:
            return []
        all_candidates: list[ImageCandidate] = []
        seen: set[str] = set()
        for q in self.queries:
            for c in self.discover(q, limit=limit_per_query):
                if c.image_url not in seen:
                    seen.add(c.image_url)
                    all_candidates.append(c)
        return all_candidates

    @staticmethod
    def _parse(item: dict) -> Optional[ImageCandidate]:
        url = ""
        w = h = 0
        if item.get("url_o"):
            url = item["url_o"]
            w = int(item.get("width_o", 0) or 0)
            h = int(item.get("height_o", 0) or 0)
        elif item.get("url_k"):
            url = item["url_k"]
            w = int(item.get("width_k", 0) or 0)
            h = int(item.get("height_k", 0) or 0)
        elif item.get("url_h"):
            url = item["url_h"]
            w = int(item.get("width_h", 0) or 0)
            h = int(item.get("height_h", 0) or 0)
        if not url:
            return None
        if w > 0 and h > 0:
            if w < TARGET_W or h < TARGET_H:
                return None
            if w >= h:
                return None
        photo_id = item.get("id", "")
        owner = item.get("owner", "")
        page_url = f"https://www.flickr.com/photos/{owner}/{photo_id}"
        return ImageCandidate(
            source="flickr",
            source_url=page_url,
            image_url=url,
            width=w, height=h,
            title=item.get("title", ""),
            extra={"flickr_id": photo_id, "owner": owner},
        )
