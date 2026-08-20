"""
collector/dedupe.py
────────────────────
중복 이미지 감지.

  1. SHA-256  : 파일 완전 동일 감지
  2. pHash    : 인지적 중복 감지 (같은 사진의 다른 해상도/압축본)
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import imagehash
from PIL import Image

logger = logging.getLogger(__name__)


class Deduper:
    def __init__(self, config: dict, known_phashes: set[str] | None = None, known_sha256s: set[str] | None = None):
        dd = config.get("dedup", {})
        self.phash_threshold = int(dd.get("phash_threshold", 8))
        self._phashes: set[str] = known_phashes or set()
        self._sha256s: set[str] = known_sha256s or set()

    def load_from_library(self, library) -> None:
        """Library 객체에서 기존 해시 목록 로드."""
        self._phashes = library.get_phashes()
        self._sha256s = library.get_sha256s()
        logger.debug("Loaded %d phashes, %d sha256s", len(self._phashes), len(self._sha256s))

    # ──────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────

    def is_duplicate(self, path: Path, img: Image.Image | None = None) -> tuple[bool, str, str]:
        """
        Returns
        -------
        (is_dup: bool, sha256: str, phash: str)
        """
        sha = self._sha256(path)
        if sha in self._sha256s:
            return True, sha, ""

        if img is None:
            img = Image.open(path).convert("RGB")

        ph = self._phash(img)
        if self._is_phash_dup(ph):
            return True, sha, ph

        return False, sha, ph

    def register(self, sha256: str, phash: str) -> None:
        """수집 확정 후 해시 등록."""
        if sha256:
            self._sha256s.add(sha256)
        if phash:
            self._phashes.add(phash)

    # ──────────────────────────────────────────
    # 내부 계산
    # ──────────────────────────────────────────

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _phash(img: Image.Image) -> str:
        return str(imagehash.phash(img))

    def _is_phash_dup(self, ph: str) -> bool:
        if not self._phashes:
            return False
        candidate = imagehash.hex_to_hash(ph)
        for existing_hex in self._phashes:
            try:
                existing = imagehash.hex_to_hash(existing_hex)
                if (candidate - existing) <= self.phash_threshold:
                    return True
            except Exception:
                continue
        return False
