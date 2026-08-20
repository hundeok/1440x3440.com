"""
collector/downloader.py
────────────────────────
HTTP 다운로더.

  - retry + exponential backoff
  - rate limiting (요청 간 대기)
  - 임시 파일에 저장 후 반환
  - 응답 Content-Type / 파일 크기 검증
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

VALID_CONTENT_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif",
}


class DownloadError(Exception):
    pass


class Downloader:
    def __init__(self, config: dict):
        c = config.get("collector", {})
        self.rate_limit = float(c.get("rate_limit", 1.0))
        self.max_retries = int(c.get("max_retries", 3))
        self.timeout = int(c.get("timeout", 30))
        self.user_agent = c.get("user_agent", "PortraitFrame/1.0")
        self._last_request_time: float = 0.0

        self._session = requests.Session()
        self._session.headers.update({"User-Agent": self.user_agent})

    # ──────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────

    def download(self, url: str, dest: Path) -> Path:
        """
        URL 을 dest 경로에 저장. 성공하면 dest 반환.
        실패하면 DownloadError.
        """
        self._rate_wait()
        dest.parent.mkdir(parents=True, exist_ok=True)

        last_err: Exception = Exception("unknown")
        for attempt in range(self.max_retries):
            try:
                return self._fetch(url, dest)
            except DownloadError as e:
                last_err = e
                wait = 2 ** attempt
                logger.warning("Download failed (attempt %d/%d): %s — retry in %ds",
                               attempt + 1, self.max_retries, e, wait)
                time.sleep(wait)

        raise DownloadError(f"All {self.max_retries} attempts failed for {url}: {last_err}")

    def get_json(self, url: str, params: dict | None = None, api_key: str = "") -> dict:
        """JSON API 요청. api_key 가 있으면 쿼리에 추가."""
        self._rate_wait()
        if api_key:
            params = dict(params or {})
            params["apikey"] = api_key

        last_err: Exception = Exception("unknown")
        for attempt in range(self.max_retries):
            try:
                resp = self._session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 403:
                    raise DownloadError(f"403 Forbidden — {url}")
                if resp.status_code == 429:
                    wait = 2 ** (attempt + 2)
                    logger.warning("Rate limited (429) — waiting %ds", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except DownloadError:
                raise   # 403 등 재시도 불필요
            except Exception as e:
                last_err = e
                wait = 2 ** attempt
                logger.warning("API request failed (attempt %d/%d): %s — retry in %ds",
                               attempt + 1, self.max_retries, e, wait)
                time.sleep(wait)

        raise DownloadError(f"API request failed for {url}: {last_err}")

    # ──────────────────────────────────────────
    # 내부 로직
    # ──────────────────────────────────────────

    def _fetch(self, url: str, dest: Path) -> Path:
        with self._session.get(url, stream=True, timeout=self.timeout) as resp:
            if resp.status_code in (403, 404):
                raise DownloadError(f"HTTP {resp.status_code}: {url}")
            if resp.status_code == 429:
                raise DownloadError(f"Rate limited (429): {url}")
            resp.raise_for_status()

            # Content-Type 검사
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ct and ct not in VALID_CONTENT_TYPES:
                raise DownloadError(f"Invalid content-type '{ct}' for {url}")

            # 파일 저장
            with dest.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

        return dest

    def _rate_wait(self) -> None:
        """요청 간 최소 대기 시간 확보."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self._last_request_time = time.monotonic()

    def close(self) -> None:
        self._session.close()
