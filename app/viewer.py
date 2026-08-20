"""
app/viewer.py
─────────────────────────────────────────────────────────────────
PortraitFrame Viewer — pygame / SDL2 기반
display.flip()이 원자적이므로 macOS gray-flash 구조적 불가능.
"""
from __future__ import annotations

import json
import logging
import random
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import pygame

from app.config import AppConfig

logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────
INIT_W = 400
INIT_H = int(INIT_W * 3440 / 1440)   # ≈ 955

BLACK     = (0,   0,   0)
WHITE     = (255, 255, 255)
GRAY      = (140, 140, 140)
DIM       = (60,  60,  60)
ACCENT    = (200, 200, 200)

INTERVALS       = [5, 10, 30, 60, 180, 300, 600, 1800, 3600]
INTERVAL_LABELS = ["5s", "10s", "30s", "1m", "3m", "5m", "10m", "30m", "1h"]
EFFECTS         = ["None", "Fade", "Dip", "Slide L", "Slide U", "Wipe R", "Wipe D", "Zoom", "Expand"]
TIMERS          = ["Off", "30m", "1h", "2h", "4h", "8h"]
TIMER_SECS      = [0, 1800, 3600, 7200, 14400, 28800]
ROW_LABELS      = ["⏱  Interval", "✦  Effect", "◔  Sleep", "☼  Wakelock"]

# pygame custom events
_EVT_IMG_READY  = pygame.USEREVENT + 1
_EVT_SLIDE      = pygame.USEREVENT + 2

SETTINGS_HIDE_MS = 4000
OSD_MS           = 2500


# ── 유틸 ─────────────────────────────────────────────────────────

def _load_surface_native(path: Path, W: int, H: int) -> pygame.Surface:
    """Pygame 네이티브 로더 (PIL 제거, GIL 우회).
    내부적으로 C레벨 하드웨어 가속을 통해 디코딩 및 스케일링 수행.
    """
    raw = pygame.image.load(str(path)).convert()
    iw, ih = raw.get_size()

    scale = min(W / iw, H / ih)
    nw = max(1, round(iw * scale))
    nh = max(1, round(ih * scale))

    if abs(scale - 1.0) > 0.005:
        raw = pygame.transform.smoothscale(raw, (nw, nh))

    return raw


# ── 메인 뷰어 ─────────────────────────────────────────────────────

class PortraitViewer:

    def __init__(self, config: AppConfig):
        self.cfg = config
        self.vc  = config.viewer

        # ── pygame 초기화 ─────────────────────────────────────────
        pygame.init()
        pygame.display.set_caption("PortraitFrame")

        self.W, self.H = INIT_W, INIT_H
        self._fs        = False
        self._prev_size = (INIT_W, INIT_H)
        self.screen = pygame.display.set_mode(
            (self.W, self.H), pygame.RESIZABLE
        )

        # ── 폰트 ─────────────────────────────────────────────────
        pygame.font.init()
        self._font    = self._make_font(16, bold=True)
        self._font_sm = self._make_font(13, bold=False)

        # ── 이미지 상태 ───────────────────────────────────────────
        self._playlist:   list[dict]               = []
        self._db:         dict                     = {}
        self._idx:        int                      = 0
        self._cur_surf:   Optional[pygame.Surface] = None
        self._cur_entry:  Optional[dict]           = None
        self._paused:     bool                     = False

        # preload
        self._pre_lock  = threading.Lock()
        self._pre_surf:  Optional[pygame.Surface] = None
        self._pre_entry: Optional[dict]           = None

        # ── 설정 패널 상태 ────────────────────────────────────────
        self._settings_visible = False
        self._settings_hide_at = 0
        self._settings_row     = 0
        try:
            self._iv = INTERVALS.index(self.vc.interval)
        except ValueError:
            self._iv = INTERVALS.index(60) if 60 in INTERVALS else 3
        try:
            self._ef = EFFECTS.index(self.vc.effect)
        except ValueError:
            self._ef = 1  # Fade
        self._tm = 0

        # ── OSD ──────────────────────────────────────────────────
        self._osd_text    = ""
        self._osd_hide_at = 0
        self._show_debug  = False
        self._last_load_ms= 0.0

        # ── 더블클릭 추적 ─────────────────────────────────────────
        self._click_time = 0
        self._click_pos  = (0, 0)

        # ── 수면 타이머 ───────────────────────────────────────────
        self._sleep_timer: Optional[threading.Timer] = None

        # ── 트랜지션 상태 ─────────────────────────────────────────
        self._prev_surf:  Optional[pygame.Surface] = None
        self._trans_start: int  = 0   # ticks
        self._in_trans:    bool = False

        # ── 전원 관리 (Wakelock) ──────────────────────────────────
        self._caffeinate_proc: Optional[subprocess.Popen] = None
        self._apply_wakelock(self.vc.wakelock)

        # ── 데이터 로드 ───────────────────────────────────────────
        self._load_playlist()

    # ── 진입점 ───────────────────────────────────────────────────

    def run(self) -> None:
        self.clock = pygame.time.Clock()

        if not self._playlist:
            self._osd("Library is empty.\nRun:  python -m collector collect", ms=99999)
        else:
            if self.vc.mode == "random":
                random.shuffle(self._playlist)
            self._load_async(self._idx, first=True)

        while True:
            now = pygame.time.get_ticks()
            active_anim = self._in_trans or self._settings_visible or self._osd_text or self._show_debug

            if active_anim:
                for ev in pygame.event.get():
                    self._handle(ev, now)
            else:
                ev = pygame.event.wait()
                self._handle(ev, pygame.time.get_ticks())
                for ev in pygame.event.get():
                    self._handle(ev, pygame.time.get_ticks())

            now = pygame.time.get_ticks()

            # 자동 숨기기
            if self._settings_visible and now > self._settings_hide_at:
                self._settings_visible = False
            if self._osd_text and now > self._osd_hide_at:
                self._osd_text = ""

            # ── 렌더링 ────────────────────────────────────────────
            self.screen.fill(BLACK)

            if self._in_trans and self._prev_surf and self._cur_surf:
                t = min(1.0, (now - self._trans_start) / max(1, self.vc.transition_ms))
                effect = EFFECTS[self._ef]

                if effect == "Fade":
                    self.screen.blit(self._prev_surf, (0, 0))
                    self._cur_surf.set_alpha(int(t * 255))
                    self.screen.blit(self._cur_surf, (0, 0))
                    self._cur_surf.set_alpha(255)

                elif effect == "Dip":
                    if t < 0.5:
                        self.screen.blit(self._prev_surf, (0, 0))
                        overlay = pygame.Surface((self.W, self.H))
                        overlay.fill(BLACK)
                        overlay.set_alpha(int((t * 2.0) * 255))
                        self.screen.blit(overlay, (0, 0))
                    else:
                        self.screen.blit(self._cur_surf, (0, 0))
                        overlay = pygame.Surface((self.W, self.H))
                        overlay.fill(BLACK)
                        overlay.set_alpha(int((1.0 - (t - 0.5) * 2.0) * 255))
                        self.screen.blit(overlay, (0, 0))

                elif effect == "Slide L":
                    offset = int(t * self.W)
                    self.screen.blit(self._prev_surf, (-offset, 0))
                    self.screen.blit(self._cur_surf,  (self.W - offset, 0))

                elif effect == "Slide U":
                    offset = int(t * self.H)
                    self.screen.blit(self._prev_surf, (0, -offset))
                    self.screen.blit(self._cur_surf,  (0, self.H - offset))

                elif effect == "Wipe R":
                    self.screen.blit(self._prev_surf, (0, 0))
                    w = int(t * self.W)
                    if w > 0:
                        crop = self._cur_surf.subsurface((0, 0, w, self.H))
                        self.screen.blit(crop, (0, 0))

                elif effect == "Wipe D":
                    self.screen.blit(self._prev_surf, (0, 0))
                    h = int(t * self.H)
                    if h > 0:
                        crop = self._cur_surf.subsurface((0, 0, self.W, h))
                        self.screen.blit(crop, (0, 0))

                elif effect == "Zoom":
                    s = 1.0 + t * 0.08
                    ow = int(self.W * s)
                    oh = int(self.H * s)
                    zoomed = pygame.transform.smoothscale(self._prev_surf, (ow, oh))
                    self.screen.blit(zoomed, (-(ow - self.W)//2, -(oh - self.H)//2))
                    self._cur_surf.set_alpha(int(t * 255))
                    self.screen.blit(self._cur_surf, (0, 0))
                    self._cur_surf.set_alpha(255)

                elif effect == "Expand":
                    self.screen.blit(self._prev_surf, (0, 0))
                    s = t
                    if s > 0:
                        ow = max(1, int(self.W * s))
                        oh = max(1, int(self.H * s))
                        scaled = pygame.transform.scale(self._cur_surf, (ow, oh))
                        self.screen.blit(scaled, ((self.W - ow)//2, (self.H - oh)//2))

                if t >= 1.0:
                    self._in_trans = False
                    self._prev_surf = None

            elif self._cur_surf:
                cw, ch = self._cur_surf.get_size()
                self.screen.blit(self._cur_surf, ((self.W - cw)//2, (self.H - ch)//2))
            else:
                self._draw_loading()

            if self._osd_text:
                self._draw_osd()
            if self._settings_visible:
                self._draw_settings(now)
            if self._show_debug:
                self._draw_debug(now, active_anim)

            pygame.display.flip()

            if active_anim:
                self.clock.tick(60)

    # ── 이벤트 처리 ──────────────────────────────────────────────

    def _handle(self, ev, now: int) -> None:
        t = ev.type

        if t == pygame.QUIT:
            self._quit()

        elif t == _EVT_IMG_READY:
            # 트랜지션 시작
            is_refresh = getattr(ev, 'is_refresh', False)
            if EFFECTS[self._ef] != "None" and self._cur_surf and not getattr(ev, 'first', False) and not is_refresh:
                self._prev_surf   = self._cur_surf
                self._trans_start = pygame.time.get_ticks()
                self._in_trans    = True
            self._cur_surf  = ev.surf
            self._cur_entry = ev.entry
            if getattr(ev, "first", False):
                self._start_timer()
            self._kick_preload()

        elif t == _EVT_SLIDE:
            if not self._paused:
                self._advance(+1)

        elif t == pygame.KEYDOWN:
            self._on_key(ev)

        elif t == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self._on_click(ev.pos, now)

        elif t == pygame.VIDEORESIZE:
            if not self._fs:
                self.W, self.H = ev.w, ev.h
                self.screen = pygame.display.set_mode(
                    (self.W, self.H), pygame.RESIZABLE
                )
            self._refresh()

    def _on_key(self, ev) -> None:
        """scancode 기반 — 한/영 IME 무관."""
        sc  = ev.scancode
        key = ev.key  # 방향키·ESC 등 특수키용

        if self._settings_visible:
            if key == pygame.K_UP:
                self._settings_row = (self._settings_row - 1) % len(ROW_LABELS)
                self._bump_settings(); return
            if key == pygame.K_DOWN:
                self._settings_row = (self._settings_row + 1) % len(ROW_LABELS)
                self._bump_settings(); return
            if key == pygame.K_LEFT:
                self._change_setting(self._settings_row, -1)
                self._bump_settings(); return
            if key == pygame.K_RIGHT:
                self._change_setting(self._settings_row, +1)
                self._bump_settings(); return

        if sc == pygame.KSCAN_TAB or key == pygame.K_TAB:
            self._toggle_settings()
        elif sc == pygame.KSCAN_SPACE or key == pygame.K_SPACE:
            self._toggle_pause()
        elif key == pygame.K_RIGHT:
            self._advance(+1)
        elif key == pygame.K_LEFT:
            self._advance(-1)
        elif sc == pygame.KSCAN_F:
            self._favorite()
        elif sc == pygame.KSCAN_X:
            self._reject()
        elif sc == pygame.KSCAN_I:
            self._show_info()
        elif sc == pygame.KSCAN_ESCAPE or key == pygame.K_ESCAPE:
            if self._fs:
                self._set_fullscreen(False)
        elif key == pygame.K_F3:
            self._show_debug = not self._show_debug
        elif sc == pygame.KSCAN_Q:
            self._quit()

    def _on_click(self, pos, now: int) -> None:
        dt = now - self._click_time
        dx = abs(pos[0] - self._click_pos[0])
        dy = abs(pos[1] - self._click_pos[1])

        if dt < 400 and dx < 30 and dy < 30:
            self._set_fullscreen(not self._fs)
        elif self._settings_visible:
            self._handle_settings_click(pos)

        self._click_time = now
        self._click_pos  = pos

    # ── 슬라이드쇼 ───────────────────────────────────────────────

    def _start_timer(self) -> None:
        pygame.time.set_timer(_EVT_SLIDE, self.vc.interval * 1000)

    def _stop_timer(self) -> None:
        pygame.time.set_timer(_EVT_SLIDE, 0)

    def _advance(self, delta: int) -> None:
        n = len(self._playlist)
        if not n:
            return
        if self.vc.mode == "random":
            self._idx = random.randint(0, n - 1)
        else:
            self._idx = (self._idx + delta) % n
        self._load_async(self._idx)
        self._start_timer()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._stop_timer()
            self._osd("⏸  Paused")
        else:
            self._start_timer()
            self._osd("▶  Playing")

    # ── 이미지 로드 ──────────────────────────────────────────────

    def _load_async(self, idx: int, first: bool = False) -> None:
        entry = self._playlist[idx] if self._playlist else None
        if not entry:
            return
        W, H = self.W, self.H

        # preload 사용 가능?
        with self._pre_lock:
            pre_s = self._pre_surf
            pre_e = self._pre_entry
            if pre_s and pre_e is entry and not first:
                self._pre_surf  = None
                self._pre_entry = None
            else:
                pre_s = None

        if pre_s:
            # preloaded → 즉시 표시 (zero lag)
            self._cur_surf  = pre_s
            self._cur_entry = entry
            if first:
                self._start_timer()
            self._kick_preload()
            return

        def _bg() -> None:
            surf = self._open_surf(entry, W, H)
            ev = pygame.event.Event(
                _EVT_IMG_READY, surf=surf, entry=entry, first=first
            )
            pygame.event.post(ev)

        threading.Thread(target=_bg, daemon=True, name="img-load").start()

    def _kick_preload(self) -> None:
        if len(self._playlist) <= 1:
            return
        n = len(self._playlist)
        if self.vc.mode == "random":
            nxt_idx = random.randint(0, n - 1)
        else:
            nxt_idx = (self._idx + 1) % n
        nxt_entry = self._playlist[nxt_idx]
        W, H = self.W, self.H

        def _bg() -> None:
            surf = self._open_surf(nxt_entry, W, H)
            with self._pre_lock:
                self._pre_surf  = surf
                self._pre_entry = nxt_entry

        threading.Thread(target=_bg, daemon=True, name="preload").start()

    def _open_surf(self, entry: dict, W: int, H: int) -> Optional[pygame.Surface]:
        try:
            t0 = time.time()
            path = self.cfg.images_dir / entry["file"]
            surf = _load_surface_native(path, W, H)
            self._last_load_ms = (time.time() - t0) * 1000
            return surf
        except Exception as e:
            logger.warning("open_surf: %s", e)
            return None

    def _refresh(self) -> None:
        """창 리사이즈 후 현재 이미지를 새 크기로 재로드."""
        entry = self._cur_entry
        if not entry:
            return
        W, H = self.W, self.H

        def _bg() -> None:
            surf = self._open_surf(entry, W, H)
            ev = pygame.event.Event(
                _EVT_IMG_READY, surf=surf, entry=entry, first=False, is_refresh=True
            )
            pygame.event.post(ev)

        threading.Thread(target=_bg, daemon=True, name="refresh").start()

    # ── 풀스크린 ─────────────────────────────────────────────────

    def _set_fullscreen(self, on: bool) -> None:
        if on == self._fs:
            return
        if on:
            self._prev_size = (self.W, self.H)
            self.screen = pygame.display.set_mode(
                (0, 0), pygame.FULLSCREEN
            )
            self.W, self.H = self.screen.get_size()
            self._fs = True
        else:
            self.W, self.H = self._prev_size
            self.screen = pygame.display.set_mode(
                (self.W, self.H), pygame.RESIZABLE
            )
            self._fs = False
        self._refresh()

    # ── 설정 ─────────────────────────────────────────────────────

    def _toggle_settings(self) -> None:
        self._settings_visible = not self._settings_visible
        if self._settings_visible:
            self._bump_settings()

    def _bump_settings(self) -> None:
        self._settings_hide_at = pygame.time.get_ticks() + SETTINGS_HIDE_MS

    def _change_setting(self, row: int, d: int) -> None:
        if row == 0:
            self._iv = (self._iv + d) % len(INTERVALS)
            self.vc.interval = INTERVALS[self._iv]
            self.cfg.save_viewer_settings()
            self._start_timer()
            self._osd(f"⏱  {INTERVAL_LABELS[self._iv]}")
        elif row == 1:
            self._ef = (self._ef + d) % len(EFFECTS)
            self.vc.effect = EFFECTS[self._ef]
            self.cfg.save_viewer_settings()
            self._osd(f"✦  {EFFECTS[self._ef]}")
        elif row == 2:
            old = self._tm
            self._tm = (self._tm + d) % len(TIMERS)
            if self._sleep_timer:
                self._sleep_timer.cancel()
            sec = TIMER_SECS[self._tm]
            if sec > 0:
                self._sleep_timer = threading.Timer(sec, lambda: self._quit(force_sleep=True))
                self._sleep_timer.daemon = True
                self._sleep_timer.start()
            self._osd(f"◔  Sleep: {TIMERS[self._tm]}")
        elif row == 3:
            self.vc.wakelock = not self.vc.wakelock
            self._apply_wakelock(self.vc.wakelock)
            self.cfg.save_viewer_settings()
            self._osd(f"☼  Wakelock: {'On' if self.vc.wakelock else 'Off'}")

    def _handle_settings_click(self, pos) -> None:
        panel_h  = 30 * len(ROW_LABELS) + 52
        panel_y  = self.H - panel_h
        row_start_y = panel_y + 28
        if pos[1] < row_start_y:
            return
        row = (pos[1] - row_start_y) // 30
        if 0 <= row < len(ROW_LABELS):
            self._settings_row = row
            cx = self.W // 2
            d = -1 if pos[0] < cx else +1
            self._change_setting(row, d)
            self._bump_settings()

    def _do_sleep(self) -> None:
        self._osd("Sleeping in 5s…", ms=5000)
        time.sleep(5)
        subprocess.Popen(["pmset", "sleepnow"])

    # ── 즐겨찾기 / 제거 ──────────────────────────────────────────

    def _favorite(self) -> None:
        e = self._cur_entry
        if not e:
            return
        e["favorite"] = not e.get("favorite", False)
        self._save()
        sym = "♥" if e["favorite"] else "♡"
        self._osd(f"{sym}  Favorite {'on' if e['favorite'] else 'off'}")

    def _reject(self) -> None:
        e = self._cur_entry
        if not e:
            return
        e["rejected"] = True
        self._save()
        self._osd("✕  Removed")
        self._advance(+1)

    def _show_info(self) -> None:
        e = self._cur_entry
        if not e:
            return
        src    = e.get("source", "?")
        score  = e.get("quality_score", 0) or 0
        ow     = e.get("original_width", 0)
        oh     = e.get("original_height", 0)
        native = "native" if e.get("native_1440x3440") else "scaled"
        title  = (e.get("title") or "")[:40]
        lines  = [
            f"📷  {src}   q={score:.2f}   {native}",
            f"🖼   {ow}×{oh}",
        ]
        if title:
            lines.append(f"📝  {title}")
        self._osd("\n".join(lines), ms=5000)

    # ── 렌더링 ───────────────────────────────────────────────────

    def _draw_loading(self) -> None:
        txt = self._font.render("Loading…", True, DIM)
        self.screen.blit(
            txt,
            (self.W // 2 - txt.get_width() // 2,
             self.H // 2 - txt.get_height() // 2),
        )

    def _draw_osd(self) -> None:
        y = 14
        for line in self._osd_text.split("\n"):
            if not line:
                y += 6
                continue
            shadow = self._font.render(line, True, BLACK)
            text   = self._font.render(line, True, WHITE)
            self.screen.blit(shadow, (15, y + 1))
            self.screen.blit(text,   (14, y))
            y += text.get_height() + 4

    def _draw_settings(self, now: int) -> None:
        row_h   = 30
        pad     = 14
        stats_h = 22
        panel_h = stats_h + row_h * 4 + pad * 2
        panel_y = self.H - panel_h

        # 반투명 배경
        panel = pygame.Surface((self.W, panel_h), pygame.SRCALPHA)
        panel.fill((8, 8, 8, 215))
        self.screen.blit(panel, (0, panel_y))
        pygame.draw.line(self.screen, DIM, (0, panel_y), (self.W, panel_y))

        # 통계 행
        st = self._get_stats()
        st_str = (f"Library: {st.get('active', 0)}  "
                  f"♥ {st.get('favorites', 0)}  "
                  f"✕ {st.get('rejected', 0)}")
        st_s = self._font_sm.render(st_str, True, DIM)
        self.screen.blit(st_s, (pad, panel_y + 6))

        # 설정 행 4개
        vals = [INTERVAL_LABELS[self._iv], EFFECTS[self._ef], TIMERS[self._tm], "On" if self.vc.wakelock else "Off"]
        for i, (label, val) in enumerate(zip(ROW_LABELS, vals)):
            y       = panel_y + stats_h + pad // 2 + i * row_h
            is_sel  = (i == self._settings_row)

            if is_sel:
                hl = pygame.Surface((self.W, row_h), pygame.SRCALPHA)
                hl.fill((255, 255, 255, 20))
                self.screen.blit(hl, (0, y))

            lc = ACCENT if is_sel else GRAY
            l_s = self._font.render(label, True, lc)
            v_s = self._font.render(val,   True, WHITE)
            a_l = self._font.render("◀",   True, DIM)
            a_r = self._font.render("▶",   True, DIM)

            cx = self.W // 2
            self.screen.blit(l_s, (pad, y + (row_h - l_s.get_height()) // 2))
            vx = cx - v_s.get_width() // 2
            self.screen.blit(a_l, (vx - a_l.get_width() - 6,
                                   y + (row_h - a_l.get_height()) // 2))
            self.screen.blit(v_s, (vx, y + (row_h - v_s.get_height()) // 2))
            self.screen.blit(a_r, (vx + v_s.get_width() + 6,
                                   y + (row_h - a_r.get_height()) // 2))

    def _draw_debug(self, now: int, active_anim: bool) -> None:
        fps = self.clock.get_fps()
        state = "ACTIVE (60 FPS)" if active_anim else "IDLE (0% CPU)"
        lines = [
            "[ Performance Monitor ]",
            f"FPS: {fps:.1f}",
            f"State: {state}",
            f"Last Load Time: {self._last_load_ms:.1f} ms",
            f"Resolution: {self.W}x{self.H}"
        ]
        y = 10
        for line in lines:
            color = (50, 255, 50) if "IDLE" in line else (255, 255, 50)
            if "FPS" in line: color = WHITE
            if "Load" in line: color = (100, 200, 255)
            s = self._font_sm.render(line, True, color)
            bg = pygame.Surface(s.get_size(), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            self.screen.blit(bg, (self.W - s.get_width() - 10, y))
            self.screen.blit(s, (self.W - s.get_width() - 10, y))
            y += s.get_height() + 4

    # ── OSD ──────────────────────────────────────────────────────

    def _osd(self, text: str, ms: int = OSD_MS) -> None:
        self._osd_text    = text
        self._osd_hide_at = pygame.time.get_ticks() + ms

    # ── 데이터 ───────────────────────────────────────────────────

    def _load_playlist(self) -> None:
        jp = self.cfg.images_json_path()
        if not jp.exists():
            return
        with jp.open("r", encoding="utf-8") as f:
            self._db = json.load(f)
        self._playlist = [
            img for img in self._db.get("images", [])
            if not img.get("rejected", False)
            and (self.cfg.images_dir / img.get("file", "")).exists()
        ]
        logger.info("Playlist: %d images", len(self._playlist))

    def _save(self) -> None:
        jp  = self.cfg.images_json_path()
        tmp = jp.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._db, f, ensure_ascii=False, indent=2)
        tmp.replace(jp)

    def _get_stats(self) -> dict:
        images = self._db.get("images", [])
        return {
            "active":    sum(1 for i in images if not i.get("rejected")),
            "favorites": sum(1 for i in images if i.get("favorite")),
            "rejected":  sum(1 for i in images if i.get("rejected")),
        }

    # ── 유틸 ─────────────────────────────────────────────────────

    @staticmethod
    def _make_font(size: int, bold: bool = False) -> pygame.font.Font:
        for name in ("Helvetica Neue", "Helvetica", "Arial", "SF Pro Display"):
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                pass
        return pygame.font.Font(None, size + 6)

    def _quit(self, force_sleep: bool = False) -> None:
        if self._sleep_timer:
            self._sleep_timer.cancel()
        
        # Wakelock 해제
        self._apply_wakelock(False)

        pygame.quit()

        if force_sleep:
            subprocess.run(["pmset", "displaysleepnow"], check=False)

        import sys
        sys.exit(0)

    def _apply_wakelock(self, enable: bool) -> None:
        if enable:
            if not self._caffeinate_proc:
                try:
                    self._caffeinate_proc = subprocess.Popen(["caffeinate", "-d"])
                except Exception as e:
                    logger.warning("caffeinate 실행 실패: %s", e)
        else:
            if self._caffeinate_proc:
                self._caffeinate_proc.terminate()
                self._caffeinate_proc.wait()
                self._caffeinate_proc = None
