"""
collector/normalizer.py
────────────────────────
이미지를 정확히 1440×3440 WebP 로 변환한다.

Resolution Case 분류:
  A  : 1440×3440 exact       → 그대로 WebP 인코딩
  B  : same ratio, larger    → downscale
  C  : portrait, crops 가능  → center crop → resize
  D  : 비율 차이 큼           → 허용 범위 내 center crop 시도
  E  : 너무 작음              → 탈락

불변 조건:
  최종 저장 파일의 width == 1440 and height == 3440
  이를 위반하면 RuntimeError 발생.
"""
from __future__ import annotations

import logging
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

TARGET_W = 1440
TARGET_H = 3440
TARGET_RATIO = TARGET_W / TARGET_H          # ≈ 0.4186
RATIO_TOLERANCE = 0.02                      # 허용 비율 오차
WEBP_QUALITY = 90


class ResolutionCase(Enum):
    A = auto()   # 정확히 1440×3440
    B = auto()   # 동일 비율, 더 큼
    C = auto()   # portrait, crop 가능
    D = auto()   # 비율 다름, crop 시도
    E = auto()   # 너무 작음 → 탈락


class NormalizerError(Exception):
    pass


class Normalizer:
    def __init__(self, config: dict):
        self.quality = WEBP_QUALITY
        tgt = config.get("target", {})
        # 설정 값을 사용하되 변경 불가 원칙 유지
        assert tgt.get("width", TARGET_W) == TARGET_W, "target width must be 1440"
        assert tgt.get("height", TARGET_H) == TARGET_H, "target height must be 3440"

    # ──────────────────────────────────────────
    # 공개 API
    # ──────────────────────────────────────────

    def process(
        self,
        src_path: Path,
        dst_path: Path,
        *,
        original_size: Optional[tuple[int, int]] = None,
    ) -> dict:
        """
        이미지를 읽어 1440×3440 WebP 로 저장한다.

        Returns
        -------
        dict with keys: case, original_width, original_height, native_1440x3440
        """
        img = self._open(src_path)
        orig_w, orig_h = img.size

        case = self._classify(orig_w, orig_h)
        if case == ResolutionCase.E:
            raise NormalizerError(
                f"Image too small: {orig_w}×{orig_h} < {TARGET_W}×{TARGET_H}"
            )

        result_img = self._transform(img, case)
        self._assert_target(result_img)
        self._save_webp(result_img, dst_path)

        return {
            "case": case.name,
            "original_width": orig_w,
            "original_height": orig_h,
            "native_1440x3440": case == ResolutionCase.A,
        }

    # ──────────────────────────────────────────
    # 내부 로직
    # ──────────────────────────────────────────

    @staticmethod
    def _open(path: Path) -> Image.Image:
        img = Image.open(path)
        # EXIF rotation 적용
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        return img.convert("RGB")

    @staticmethod
    def _classify(w: int, h: int) -> ResolutionCase:
        if w < TARGET_W or h < TARGET_H:
            return ResolutionCase.E

        if w == TARGET_W and h == TARGET_H:
            return ResolutionCase.A

        ratio = w / h
        if abs(ratio - TARGET_RATIO) <= RATIO_TOLERANCE:
            return ResolutionCase.B   # 동일 비율 계열

        # Portrait 여부 (세로가 더 김)
        if h > w:
            return ResolutionCase.C   # portrait, center crop 가능

        return ResolutionCase.D       # landscape or square → 비율 크게 다름

    @staticmethod
    def _transform(img: Image.Image, case: ResolutionCase) -> Image.Image:
        if case == ResolutionCase.A:
            return img

        if case == ResolutionCase.B:
            return img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

        if case in (ResolutionCase.C, ResolutionCase.D):
            return Normalizer._center_crop_resize(img)

        raise NormalizerError(f"Unhandled case: {case}")

    @staticmethod
    def _center_crop_resize(img: Image.Image) -> Image.Image:
        """
        이미지를 center crop 후 TARGET_W × TARGET_H 로 resize.
        """
        w, h = img.size
        img_ratio = w / h

        if img_ratio > TARGET_RATIO:
            # 이미지가 목표보다 넓음 → 좌우를 자른다
            new_w = int(h * TARGET_RATIO)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            # 이미지가 목표보다 좁음 → 상하를 자른다
            new_h = int(w / TARGET_RATIO)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        return img.resize((TARGET_W, TARGET_H), Image.LANCZOS)

    @staticmethod
    def _assert_target(img: Image.Image) -> None:
        """불변 조건 검증 — 실패 시 RuntimeError."""
        w, h = img.size
        if w != TARGET_W or h != TARGET_H:
            raise RuntimeError(
                f"INVARIANT VIOLATED: image is {w}×{h}, expected {TARGET_W}×{TARGET_H}"
            )

    def _save_webp(self, img: Image.Image, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path), format="WEBP", quality=self.quality, method=4)
        logger.debug("Saved WebP: %s", path.name)
