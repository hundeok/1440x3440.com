"""
collector/library.py
────────────────────
중앙 데이터 저장소. images.json 을 관리하고
이미지 메타데이터의 CRUD / 통계 / 중복 조회를 담당한다.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TARGET_WIDTH = 1440
TARGET_HEIGHT = 3440


class Library:
    """PortraitFrame 이미지 라이브러리 — images.json 관리."""

    VERSION = 1

    def __init__(self, config: dict):
        lib_cfg = config["library"]
        self.root = Path(lib_cfg["path"]).resolve()
        self.images_dir = self.root / lib_cfg["images_dir"]
        self.originals_dir = self.root / lib_cfg["originals_dir"]
        self.json_path = self.root / "images.json"

        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.originals_dir.mkdir(parents=True, exist_ok=True)

        self._data = self._load()

    # ──────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────

    def _load(self) -> dict:
        if self.json_path.exists():
            with self.json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "images" not in data:
                data = {"version": self.VERSION, "images": []}
            return data
        return {"version": self.VERSION, "images": []}

    def save(self) -> None:
        """images.json 원자적 저장 (tmp → replace)."""
        tmp = self.json_path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.json_path)
        logger.debug("Library saved — %d images", len(self._data["images"]))

    # ──────────────────────────────────────────
    # ID 관리
    # ──────────────────────────────────────────

    def _next_id(self) -> str:
        images = self._data["images"]
        if not images:
            return "000001"
        last_id = max(int(img["id"]) for img in images)
        return f"{last_id + 1:06d}"

    # ──────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────

    def add(self, entry: dict) -> str:
        """이미지 엔트리 추가. 부여된 ID 반환."""
        img_id = self._next_id()
        entry = dict(entry)
        entry["id"] = img_id
        entry.setdefault("favorite", False)
        entry.setdefault("rejected", False)
        entry.setdefault(
            "created_at", datetime.now(timezone.utc).isoformat()
        )
        self._data["images"].append(entry)
        return img_id

    def update(self, img_id: str, **kwargs) -> bool:
        """기존 이미지 필드 업데이트. 찾으면 True."""
        for img in self._data["images"]:
            if img["id"] == img_id:
                img.update(kwargs)
                return True
        return False

    def get(self, img_id: str) -> Optional[dict]:
        for img in self._data["images"]:
            if img["id"] == img_id:
                return img
        return None

    def get_all(self) -> list[dict]:
        """rejected=False 인 이미지 전체 반환."""
        return [img for img in self._data["images"] if not img.get("rejected", False)]

    def get_active_paths(self) -> list[Path]:
        """유효한 이미지 파일 경로 목록."""
        return [
            self.images_dir / img["file"]
            for img in self.get_all()
            if (self.images_dir / img["file"]).exists()
        ]

    # ──────────────────────────────────────────
    # 중복 제거 헬퍼
    # ──────────────────────────────────────────

    def get_phashes(self) -> set[str]:
        return {img["phash"] for img in self._data["images"] if img.get("phash")}

    def get_sha256s(self) -> set[str]:
        return {img["sha256"] for img in self._data["images"] if img.get("sha256")}

    def has_source_url(self, url: str) -> bool:
        """이미 수집한 URL인지 확인."""
        return any(img.get("source_url") == url for img in self._data["images"])

    # ──────────────────────────────────────────
    # 통계
    # ──────────────────────────────────────────

    def stats(self) -> dict:
        images = self._data["images"]
        active = [img for img in images if not img.get("rejected", False)]
        rejected_list = [img for img in images if img.get("rejected", False)]
        favorites = [img for img in active if img.get("favorite", False)]

        # 디스크 사용량
        total_bytes = 0
        for img in active:
            p = self.images_dir / img["file"]
            if p.exists():
                total_bytes += p.stat().st_size

        # 소스별 통계
        source_stats: dict[str, dict] = {}
        for img in images:
            src = img.get("source", "unknown")
            if src not in source_stats:
                source_stats[src] = {"downloaded": 0, "accepted": 0}
            source_stats[src]["downloaded"] += 1
            if not img.get("rejected", False):
                source_stats[src]["accepted"] += 1

        return {
            "total": len(images),
            "active": len(active),
            "rejected": len(rejected_list),
            "favorites": len(favorites),
            "disk_bytes": total_bytes,
            "sources": source_stats,
        }
