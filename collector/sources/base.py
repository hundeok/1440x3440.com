"""
collector/sources/base.py
──────────────────────────
소스 어댑터 추상 기반 클래스.

각 소스(Wallhaven, Reddit 등)는 이 클래스를 상속하여
discover() 를 구현한다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ImageCandidate:
    """소스에서 발견된 이미지 후보."""
    source: str              # 소스 이름 ("wallhaven", "reddit", ...)
    source_url: str          # 월페이퍼 페이지 URL
    image_url: str           # 직접 다운로드 URL
    width: int               # 원본 가로
    height: int              # 원본 세로
    title: str = ""
    category: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # 소스별 추가 메타데이터


class BaseSourceAdapter(ABC):
    """소스 어댑터 추상 기반 클래스."""

    def __init__(self, config: dict):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """소스 식별자 (예: 'wallhaven')."""
        ...

    @abstractmethod
    def discover(self, query: str, limit: int = 50) -> list[ImageCandidate]:
        """
        주어진 쿼리로 이미지 후보 목록을 반환한다.
        HTTP 오류 등 실패 시 빈 목록 반환 (전체 중단 X).
        """
        ...

    def get_queries(self) -> list[dict]:
        """
        기본 검색 쿼리 목록 반환.
        각 항목은 {'q': ..., ...} 형태의 파라미터 딕셔너리.
        """
        return []

    def is_enabled(self) -> bool:
        return self.config.get("sources", {}).get(self.name, {}).get("enabled", False)
