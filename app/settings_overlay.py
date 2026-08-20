"""
app/settings_overlay.py
────────────────────────
하단 설정 오버레이 (Tab 키로 열기/닫기).

구성:
  ⏱  Interval  ◀  10s  ▶
  ✦  Effect    ◀  None  ▶
  ◔  Sleep     ◀  Off   ▶

- 마지막 조작 4초 후 자동 닫힘
- Sleep 타이머: 카운트다운 → macOS sleep 명령
- 순수 Tkinter, 추가 패키지 없음
"""
from __future__ import annotations

import subprocess
import tkinter as tk
from typing import Callable, Optional


INTERVALS = [5, 10, 30, 60, 180, 300, 600, 1800, 3600]
INTERVAL_LABELS = ["5s", "10s", "30s", "1m", "3m", "5m", "10m", "30m", "1h"]

EFFECTS = ["None", "Fade"]
EFFECT_STEPS = [0, 6]
EFFECT_MS = [0, 800]

TIMERS = ["Off", "30m", "1h", "2h", "4h", "8h"]
TIMER_SECS = [0, 1800, 3600, 7200, 14400, 28800]

_BG = "#0f0f0f"
_FG = "#aaaaaa"
_BRIGHT = "#ffffff"
_BTN = "#222222"
_BORDER = "#2a2a2a"
_FONT = ("Helvetica", 13)
_FONT_B = ("Helvetica", 13, "bold")
_FONT_VAL = ("SF Mono", 13, "bold") if True else ("Courier", 13, "bold")


def _fmt_secs(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, sc = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sc:02d}"
    return f"{m}:{sc:02d}"


class SettingsOverlay:
    """하단 슬라이드인 설정 패널."""

    def __init__(
        self,
        root: tk.Tk,
        on_interval: Callable[[int], None],
        on_effect: Callable[[int, int], None],
        on_osd: Callable[[str], None],
        get_stats: Optional[Callable[[], dict]] = None,
    ):
        self.root = root
        self._on_interval = on_interval
        self._on_effect = on_effect
        self._on_osd = on_osd
        self._get_stats = get_stats

        self._visible = False
        self._hide_job: Optional[str] = None
        self._timer_job: Optional[str] = None
        self._timer_remaining: int = 0

        # 현재 선택 인덱스
        self._iv = 1   # 10s
        self._ef = 0   # None
        self._tm = 0   # Off

        self._val_labels: dict[str, tk.Label] = {}
        self._build()

    # ── UI 구성 ───────────────────────────────────

    def _build(self) -> None:
        self.frame = tk.Frame(self.root, bg=_BG)

        # 상단 구분선
        tk.Frame(self.frame, bg=_BORDER, height=1).pack(fill=tk.X)

        inner = tk.Frame(self.frame, bg=_BG)
        inner.pack(fill=tk.X, padx=20, pady=6)

        # 라이브러리 통계 행
        self._stats_label = tk.Label(
            inner, text="", bg=_BG, fg="#666666",
            font=("Helvetica", 11), anchor="w"
        )
        self._stats_label.pack(fill=tk.X, pady=(0, 4))

        rows = [
            ("⏱  Interval", INTERVAL_LABELS, "_iv"),
            ("✦  Effect", EFFECTS, "_ef"),
            ("◔  Sleep", TIMERS, "_tm"),
        ]

        for label, options, attr in rows:
            self._make_row(inner, attr, label, options)

    def _make_row(self, parent: tk.Frame, attr: str, label: str, options: list[str]) -> None:
        row = tk.Frame(parent, bg=_BG)
        row.pack(fill=tk.X, pady=2)

        # 레이블
        tk.Label(row, text=label, bg=_BG, fg=_FG, font=_FONT,
                 anchor="w", width=14).pack(side=tk.LEFT)

        # ◀ 버튼
        tk.Button(
            row, text="◀", bg=_BG, fg=_FG, relief="flat", bd=0,
            activebackground=_BTN, activeforeground=_BRIGHT,
            font=_FONT, cursor="hand2", padx=6,
            command=lambda a=attr, o=options: self._step(a, o, -1),
        ).pack(side=tk.LEFT)

        # 값 레이블
        idx = getattr(self, attr)
        val = tk.Label(row, text=options[idx], bg=_BG, fg=_BRIGHT,
                       font=_FONT_B, width=9, anchor="center")
        val.pack(side=tk.LEFT)
        self._val_labels[attr] = val

        # ▶ 버튼
        tk.Button(
            row, text="▶", bg=_BG, fg=_FG, relief="flat", bd=0,
            activebackground=_BTN, activeforeground=_BRIGHT,
            font=_FONT, cursor="hand2", padx=6,
            command=lambda a=attr, o=options: self._step(a, o, +1),
        ).pack(side=tk.LEFT)

    # ── 값 변경 ───────────────────────────────────

    def _step(self, attr: str, options: list[str], delta: int) -> None:
        idx = (getattr(self, attr) + delta) % len(options)
        setattr(self, attr, idx)
        self._val_labels[attr].config(text=options[idx])
        self._apply(attr, idx)
        self._reset_autohide()

    def _apply(self, attr: str, idx: int) -> None:
        if attr == "_iv":
            self._on_interval(INTERVALS[idx])
        elif attr == "_ef":
            self._on_effect(EFFECT_STEPS[idx], EFFECT_MS[idx])
        elif attr == "_tm":
            self._start_timer(TIMER_SECS[idx])

    # ── Sleep 타이머 ──────────────────────────────

    def _start_timer(self, secs: int) -> None:
        # 기존 타이머 취소
        if self._timer_job:
            self.root.after_cancel(self._timer_job)
            self._timer_job = None

        if secs <= 0:
            self._timer_remaining = 0
            self._val_labels["_tm"].config(text="Off")
            return

        self._timer_remaining = secs
        self._tick()

    def _tick(self) -> None:
        self._timer_remaining -= 1

        # 레이블 업데이트
        if self._timer_remaining > 0:
            label = _fmt_secs(self._timer_remaining)
            self._val_labels["_tm"].config(text=label)

            # 5분 이하 → OSD 경고
            if self._timer_remaining in (300, 60, 30, 10):
                m, s = divmod(self._timer_remaining, 60)
                msg = f"◔ Sleep in {m}m {s:02d}s" if m else f"◔ Sleep in {s}s"
                self._on_osd(msg, 4000)

            self._timer_job = self.root.after(1000, self._tick)
        else:
            self._on_osd("💤 Sleeping…", 3000)
            self.root.after(1500, self._do_sleep)

    @staticmethod
    def _do_sleep() -> None:
        subprocess.Popen(["pmset", "sleepnow"])

    # ── 표시/숨김 ─────────────────────────────────

    def show(self) -> None:
        self._visible = True
        # 통계 업데이트
        if self._get_stats:
            try:
                s = self._get_stats()
                total = s.get("active", 0)
                fav = s.get("favorites", 0)
                rej = s.get("rejected", 0)
                self._stats_label.config(
                    text=f"Library: {total} images  ♥ {fav}  ✕ {rej}"
                )
            except Exception:
                pass
        self.frame.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)
        self.frame.lift()
        self._reset_autohide()

    def hide(self) -> None:
        self._visible = False
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
            self._hide_job = None
        self.frame.place_forget()

    def toggle(self) -> None:
        self.hide() if self._visible else self.show()

    def _reset_autohide(self) -> None:
        if self._hide_job:
            self.root.after_cancel(self._hide_job)
        self._hide_job = self.root.after(4000, self.hide)

    @property
    def is_visible(self) -> bool:
        return self._visible

    # 외부에서 현재 설정값 읽기
    @property
    def current_interval(self) -> int:
        return INTERVALS[self._iv]

    @property
    def current_steps(self) -> int:
        return EFFECT_STEPS[self._ef]

    @property
    def current_ms(self) -> int:
        return EFFECT_MS[self._ef]
