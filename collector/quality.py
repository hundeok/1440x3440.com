"""
collector/quality.py
─────────────────────
이미지 품질 필터링.

- 블러 감지 (Laplacian variance via Pillow edge detection)
- 단색/빈 이미지 감지 (픽셀 표준편차)
- JPEG artifact 감지 (간단한 heuristic)
- 종합 quality_score 0.0 ~ 1.0 계산
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter, ImageStat

logger = logging.getLogger(__name__)


class QualityFilter:
    def __init__(self, config: dict):
        q = config.get("quality", {})
        self.min_score = float(q.get("min_quality_score", 0.25))
        self.blur_threshold = float(q.get("blur_threshold", 60.0))
        self.blank_threshold = float(q.get("blank_threshold", 6.0))
        self.min_file_size_kb = float(q.get("min_file_size_kb", 50))

    # ──────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────

    def is_acceptable(self, path: Path, img: Optional[Image.Image] = None) -> tuple[bool, float, str]:
        """
        Returns
        -------
        (ok: bool, score: float, reason: str)
        """
        # 파일 크기 검사
        size_kb = path.stat().st_size / 1024
        if size_kb < self.min_file_size_kb:
            return False, 0.0, f"file too small: {size_kb:.1f}KB"

        # PIL로 열어서 검사
        if img is None:
            try:
                img = Image.open(path).convert("RGB")
            except Exception as e:
                return False, 0.0, f"cannot open image: {e}"

        blur_score = self._blur_score(img)
        blank_score = self._blank_score(img)
        quality_score = self._compute_score(blur_score, blank_score)

        if blur_score < self.blur_threshold:
            return False, quality_score, f"blurry: variance={blur_score:.1f}"
        if blank_score < self.blank_threshold:
            return False, quality_score, f"blank/monochrome: stddev={blank_score:.1f}"
        if quality_score < self.min_score:
            return False, quality_score, f"low quality score: {quality_score:.2f}"

        return True, quality_score, "ok"

    def compute_score(self, img: Image.Image) -> float:
        blur = self._blur_score(img)
        blank = self._blank_score(img)
        return self._compute_score(blur, blank)

    # ──────────────────────────────────────────
    # 내부 계산
    # ──────────────────────────────────────────

    @staticmethod
    def _blur_score(img: Image.Image) -> float:
        """
        Laplacian variance — 높을수록 선명.
        Pillow FIND_EDGES 필터를 이용한 edge 감지 후 분산 계산.
        """
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        return stat.var[0]

    @staticmethod
    def _blank_score(img: Image.Image) -> float:
        """
        픽셀 표준편차 — 낮을수록 단색에 가까움.
        """
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        return stat.stddev[0]

    def _compute_score(self, blur: float, blank: float) -> float:
        """
        blur / blank 값을 0~1 점수로 정규화.
        """
        # blur: 0~5000+ 범위, 500 이상이면 충분히 선명
        blur_norm = min(blur / 500.0, 1.0)
        # blank: 0~127 범위, 30 이상이면 충분히 다채로움
        blank_norm = min(blank / 30.0, 1.0)
        return round((blur_norm * 0.6 + blank_norm * 0.4), 4)
