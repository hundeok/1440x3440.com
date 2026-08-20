"""
app/controls.py
────────────────
Tkinter 키보드/마우스 바인딩.

키 요약:
  →/←       다음 / 이전
  Space      일시정지 / 재개
  F          즐겨찾기
  X          제거
  R          랜덤 모드
  S          순서 모드
  Tab        설정 패널 열기/닫기
  ESC        풀스크린 해제
  Q          종료
  더블클릭   풀스크린 토글
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable


def bind_controls(root: tk.Tk, viewer) -> None:
    bindings: list[tuple[str, Callable]] = [
        # 탐색
        ("<Right>",      viewer.show_next),
        ("<Left>",       viewer.show_previous),
        # 재생
        ("<space>",      viewer.toggle_pause),
        # 큐레이션
        ("f",            viewer.favorite_current),
        ("F",            viewer.favorite_current),
        ("x",            viewer.reject_current),
        ("X",            viewer.reject_current),
        # 모드
        ("r",            viewer.set_random_mode),
        ("R",            viewer.set_random_mode),
        ("s",            viewer.set_sequential_mode),
        ("S",            viewer.set_sequential_mode),
        # 설정 패널
        ("<Tab>",        viewer.toggle_settings),
        # 정보
        ("i",            viewer.show_info),
        ("I",            viewer.show_info),
        # 시스템
        ("<Escape>",     viewer.exit_fullscreen),
        ("q",            viewer.quit),
        ("Q",            viewer.quit),
    ]

    for key, handler in bindings:
        root.bind(key, lambda e, h=handler: h())
