import json
import logging
import os
import random
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import (QPropertyAnimation, QRectF, Qt, QThread, QTimer,
                          QVariantAnimation, pyqtSignal)
from PyQt6.QtGui import (QColor, QFont, QImage, QImageReader, QKeySequence,
                         QMouseEvent, QPainter, QPixmap, QShortcut)
from PyQt6.QtWidgets import (QGraphicsOpacityEffect, QGraphicsPixmapItem,
                             QGraphicsRectItem, QGraphicsScene,
                             QGraphicsTextItem, QGraphicsView, QMainWindow)

from app.config import AppConfig

logger = logging.getLogger(__name__)

INTERVALS = [5, 10, 30, 60, 180, 300, 600, 1800, 3600]
INTERVAL_LABELS = ["5s", "10s", "30s", "1m", "3m", "5m", "10m", "30m", "1h"]
EFFECTS = ["None", "Fade", "Dip", "Slide L", "Slide U", "Wipe R", "Wipe D", "Zoom", "Expand"]
TIMERS = ["Off", "30m", "1h", "2h", "4h", "8h"]
TIMER_SECS = [0, 1800, 3600, 7200, 14400, 28800]
ROW_LABELS = ["⏱  Interval", "✦  Effect", "◔  Sleep", "☼  Wakelock"]


class ImageLoader(QThread):
    ready = pyqtSignal(dict, QImage, bool, float)

    def __init__(self, cfg: AppConfig, entry: dict, is_first: bool):
        super().__init__()
        self.cfg = cfg
        self.entry = entry
        self.is_first = is_first

    def _manage_cache_size(self, cache_dir: Path, max_bytes: int = 500 * 1024 * 1024):
        try:
            files = [f for f in cache_dir.glob("*") if f.is_file()]
            files.sort(key=lambda x: x.stat().st_atime)
            total_size = sum(f.stat().st_size for f in files)
            while total_size > max_bytes and files:
                f = files.pop(0)
                total_size -= f.stat().st_size
                f.unlink()
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

    def run(self):
        try:
            t0 = time.time()
            filename = self.entry["file"]

            if self.cfg.cloud.enabled:
                cache_dir = Path(os.path.expanduser("~/Library/Caches/1440x3440/library/images"))
                cache_dir.mkdir(parents=True, exist_ok=True)
                path = str(cache_dir / filename)

                if not os.path.exists(path):
                    # images_dir 이름(예: 1440x3440 images)을 URL 인코딩하여 동적 적용
                    import urllib.parse
                    folder_name = urllib.parse.quote(self.cfg.images_dir.name)
                    file_name_encoded = urllib.parse.quote(filename)
                    url = f"{self.cfg.cloud.base_url}/{folder_name}/{file_name_encoded}"
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, context=ctx) as response, open(path, 'wb') as out_file:
                        out_file.write(response.read())
                    self._manage_cache_size(cache_dir)
                else:
                    # Update atime
                    os.utime(path, None)
            else:
                path = str(self.cfg.images_dir / filename)

            reader = QImageReader(path)
            reader.setAutoTransform(True)
            img = reader.read()

            if not img.isNull():
                img = img.convertToFormat(QImage.Format.Format_RGB32)

            load_ms = (time.time() - t0) * 1000
            self.ready.emit(self.entry, img, self.is_first, load_ms)
        except Exception as e:
            logger.error(f"Image load error: {e}")


class PortraitViewer(QMainWindow):
    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg
        self.vc = cfg.viewer

        self.setWindowTitle("1440x3440.com")
        self.setStyleSheet("background-color: black;")

        # ── UI 셋업 ────────────────────────────────────────────────
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor(0, 0, 0))

        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.view.setStyleSheet("background: black; border: 0px;")
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setCentralWidget(self.view)

        # ── 아이템 레이어 ──────────────────────────────────────────
        self.prev_item = QGraphicsPixmapItem()
        self.cur_item = QGraphicsPixmapItem()
        self.scene.addItem(self.prev_item)
        self.scene.addItem(self.cur_item)

        # OSD
        self.osd_text_item = QGraphicsTextItem()
        self.osd_text_item.setDefaultTextColor(QColor(255, 255, 255))
        self.osd_text_item.setFont(QFont("Menlo", 14, QFont.Weight.Bold))
        self.osd_text_item.setZValue(100)
        self.scene.addItem(self.osd_text_item)

        # Settings
        self.settings_bg_item = QGraphicsRectItem()
        self.settings_bg_item.setBrush(QColor(8, 8, 8, 215))
        from PyQt6.QtGui import QPen
        self.settings_bg_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.settings_bg_item.setZValue(101)
        self.settings_bg_item.hide()
        self.scene.addItem(self.settings_bg_item)

        self.settings_text_item = QGraphicsTextItem()
        self.settings_text_item.setDefaultTextColor(QColor(255, 255, 255))
        self.settings_text_item.setFont(QFont("Menlo", 16, QFont.Weight.Bold))
        self.settings_text_item.setZValue(102)
        self.settings_text_item.hide()
        self.scene.addItem(self.settings_text_item)

        # ── 단축키 바인딩 (QShortcut 사용 - Tab 포커스 이슈 완벽 회피) ──────────
        QShortcut(QKeySequence("Tab"), self).activated.connect(self._toggle_settings)
        QShortcut(QKeySequence("Space"), self).activated.connect(lambda: self._on_right(force_next=True))
        QShortcut(QKeySequence("Right"), self).activated.connect(self._on_right)
        QShortcut(QKeySequence("Left"), self).activated.connect(self._on_left)
        QShortcut(QKeySequence("Up"), self).activated.connect(self._on_up)
        QShortcut(QKeySequence("Down"), self).activated.connect(self._on_down)
        QShortcut(QKeySequence("F2"), self).activated.connect(self._toggle_pause)
        QShortcut(QKeySequence("F3"), self).activated.connect(self._toggle_debug)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self._quit)
        QShortcut(QKeySequence("Q"), self).activated.connect(self._quit)

        # ── 애니메이션 ─────────────────────────────────────────────
        self.opacity_effect_cur = QGraphicsOpacityEffect()
        self.cur_item.setGraphicsEffect(self.opacity_effect_cur)
        self.opacity_effect_prev = QGraphicsOpacityEffect()
        self.prev_item.setGraphicsEffect(self.opacity_effect_prev)

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(self.vc.transition_ms)
        self.anim.valueChanged.connect(self._on_anim_step)
        self.anim.finished.connect(self._on_anim_finished)

        self._prev_base_scale = 1.0
        self._cur_base_scale = 1.0
        self._prev_base_pos = (0, 0)
        self._cur_base_pos = (0, 0)

        # ── 플레이리스트 & 상태 변수 ───────────────────────────────
        self._playlist = []
        self._db = {}
        self._idx = 0
        self._cur_entry: Optional[Dict] = None
        self._last_load_ms: float = 0.0

        self._paused: bool = False
        self._settings_visible: bool = False

        self._settings_row = 0
        self._iv = INTERVALS.index(self.vc.interval) if self.vc.interval in INTERVALS else 3
        self._ef = EFFECTS.index(self.vc.effect) if self.vc.effect in EFFECTS else 0
        self._tm = 0

        # ── 수면/전원 타이머 ───────────────────────────────────────
        self._sleep_timer: Optional[QTimer] = None
        self._caffeinate_proc: Optional[subprocess.Popen] = None
        self._apply_wakelock(self.vc.wakelock)

        # ── 갱신 타이머 ────────────────────────────────────────────
        self.slide_timer = QTimer(self)
        self.slide_timer.timeout.connect(self._on_slide_timeout)
        self.time_left = self.vc.interval

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.osd_text_item.hide)

        self.settings_hide_timer = QTimer(self)
        self.settings_hide_timer.setSingleShot(True)
        self.settings_hide_timer.timeout.connect(self._hide_menus)

        # ── Loading Screen (Neo Brutalism) ─────────────────────────
        self._is_loading = True
        self.loading_shadow = QGraphicsRectItem()
        self.loading_shadow.setBrush(QColor(0, 0, 0))
        self.loading_shadow.setPen(QPen(Qt.PenStyle.NoPen))
        self.loading_shadow.setZValue(199)
        self.scene.addItem(self.loading_shadow)

        self.loading_bg = QGraphicsRectItem()
        self.loading_bg.setBrush(QColor(255, 255, 255))
        self.loading_bg.setPen(QPen(QColor(0, 0, 0), 3))
        self.loading_bg.setZValue(200)
        self.scene.addItem(self.loading_bg)

        self.loading_text = QGraphicsTextItem()
        self.loading_text.setDefaultTextColor(QColor(0, 0, 0))
        self.loading_text.setFont(QFont("Menlo", 15, QFont.Weight.Bold))
        self.loading_text.setZValue(201)
        self.loading_text.setPlainText(" FETCHING \n 1440x3440... ")
        self.scene.addItem(self.loading_text)

        # 실행 시작 (세로 모니터 비율 1440x3440에 맞춰 400x955로 초기화)
        self.resize(400, 955)

        # UI가 확실히 그려질 수 있도록 500ms 딜레이를 주고 부팅 감성을 더함
        QTimer.singleShot(500, self._init_startup)

    def _init_startup(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()  # 강제로 UI 페인트 업데이트

        self._load_playlist()
        if self.vc.mode == "random":
            import random
            random.shuffle(self._playlist)
        self._load_next(first=True)

    def _hide_menus(self):
        self.osd_text_item.hide()
        self.settings_bg_item.hide()
        self.settings_text_item.hide()
        self._settings_visible = False

    def _osd(self, text: str, duration_sec: float = 2.0):
        self.osd_text_item.setPlainText(text)
        self.osd_text_item.adjustSize()
        self.osd_text_item.setPos(20, 20)
        self.osd_text_item.show()
        # 100ms 폴링 대신 정확한 타이머 사용으로 CPU 0% 유지
        self.hide_timer.start(int(duration_sec * 1000))

    # ── 플레이리스트 로직 ───────────────────────────────────────
    def _load_playlist(self) -> None:
        if self.cfg.cloud.enabled:
            url = f"{self.cfg.cloud.base_url}/images.json"
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, context=ctx) as response:
                    self._db = json.loads(response.read().decode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to fetch cloud images.json: {e}")
                self._db = {"images": []}
        else:
            jp = self.cfg.images_json_path()
            if not jp.exists():
                return
            with jp.open("r", encoding="utf-8") as f:
                self._db = json.load(f)

        self._playlist = [
            img for img in self._db.get("images", [])
            if not img.get("rejected", False)
        ]

        # 로컬 모드일 때만 실제 파일 존재 여부 검사
        if not self.cfg.cloud.enabled:
            self._playlist = [
                img for img in self._playlist
                if (self.cfg.images_dir / img.get("file", "")).exists()
            ]

        logger.info("Playlist: %d images", len(self._playlist))

    def _get_entry(self, delta: int) -> Optional[dict]:
        n = len(self._playlist)
        if not n:
            return None
        self._idx = (self._idx + delta) % n
        return self._playlist[self._idx]

    # ── 이미지 로딩 ─────────────────────────────────────────────
    def _load_next(self, first=False):
        entry = self._get_entry(+1 if not first else 0)
        if entry:
            self._start_loader(entry, first)

    def _load_prev(self):
        entry = self._get_entry(-1)
        if entry:
            self._start_loader(entry, False)

    def _start_loader(self, entry, first):
        self.loader = ImageLoader(self.cfg, entry, first)
        self.loader.ready.connect(self._on_image_ready)
        # [Optimization 2] 백그라운드 스레드 우선순위 강등: 메인 스레드 60fps 애니메이션 간섭 차단
        self.loader.start(QThread.Priority.LowPriority)

    def _on_image_ready(self, entry, qimg, is_first, load_ms):
        if getattr(self, '_is_loading', False):
            self.loading_shadow.hide()
            self.loading_bg.hide()
            self.loading_text.hide()
            self._is_loading = False

        self._last_load_ms = load_ms
        self._cur_entry = entry
        pixmap = QPixmap.fromImage(qimg)

        if EFFECTS[self._ef] != "None" and not is_first and not self.cur_item.pixmap().isNull():
            # 이전 이미지 백업
            self.prev_item.setPixmap(self.cur_item.pixmap())
            self._prev_base_scale = self.cur_item.scale()
            self._prev_base_pos = (self.cur_item.pos().x(), self.cur_item.pos().y())
            self.prev_item.setScale(self._prev_base_scale)
            self.prev_item.setPos(*self._prev_base_pos)
            self.prev_item.show()
            self.opacity_effect_prev.setOpacity(1.0)

            # 새 이미지 세팅
            self.cur_item.setPixmap(pixmap)
            self._fit_item(self.cur_item)
            self._cur_base_scale = self.cur_item.scale()
            self._cur_base_pos = (self.cur_item.pos().x(), self.cur_item.pos().y())

            # 애니메이션 시작
            self.anim.stop()
            self.anim.setStartValue(0.0)
            self.anim.setEndValue(1.0)
            self.anim.start()
        else:
            self.prev_item.hide()
            self.cur_item.setPixmap(pixmap)
            self.opacity_effect_cur.setOpacity(1.0)
            self._fit_images()

        if is_first:
            self.time_left = self.vc.interval
            self.slide_timer.start(1000)

    # ── 애니메이션 스텝 (매 프레임 호출) ────────────────────────
    def _on_anim_step(self, val: float):
        t = val
        effect = EFFECTS[self._ef]
        rect = self.view.viewport().rect()
        w, h = rect.width(), rect.height()

        if effect in ("Fade", "Wipe R", "Wipe D"):
            self.opacity_effect_cur.setOpacity(t)

        elif effect == "Dip":
            if t < 0.5:
                self.opacity_effect_prev.setOpacity(1.0 - (t * 2.0))
                self.cur_item.hide()
            else:
                self.cur_item.show()
                self.opacity_effect_cur.setOpacity((t - 0.5) * 2.0)

        elif effect == "Slide L":
            offset = t * w
            self.prev_item.setPos(self._prev_base_pos[0] - offset, self._prev_base_pos[1])
            self.cur_item.setPos(self._cur_base_pos[0] + w - offset, self._cur_base_pos[1])
            self.opacity_effect_cur.setOpacity(1.0)

        elif effect == "Slide U":
            offset = t * h
            self.prev_item.setPos(self._prev_base_pos[0], self._prev_base_pos[1] - offset)
            self.cur_item.setPos(self._cur_base_pos[0], self._cur_base_pos[1] + h - offset)
            self.opacity_effect_cur.setOpacity(1.0)

        elif effect == "Zoom":
            s = 1.0 + t * 0.08
            self.prev_item.setScale(self._prev_base_scale * s)
            px = self._prev_base_pos[0] - (self.prev_item.pixmap().width() * self._prev_base_scale * (s - 1.0)) / 2
            py = self._prev_base_pos[1] - (self.prev_item.pixmap().height() * self._prev_base_scale * (s - 1.0)) / 2
            self.prev_item.setPos(px, py)
            self.opacity_effect_cur.setOpacity(t)

        elif effect == "Expand":
            s = max(0.01, t)
            self.cur_item.setScale(self._cur_base_scale * s)
            px = self._cur_base_pos[0] + (self.cur_item.pixmap().width() * self._cur_base_scale * (1.0 - s)) / 2
            py = self._cur_base_pos[1] + (self.cur_item.pixmap().height() * self._cur_base_scale * (1.0 - s)) / 2
            self.cur_item.setPos(px, py)
            self.opacity_effect_cur.setOpacity(1.0)

    def _on_anim_finished(self):
        self.prev_item.hide()
        # [Optimization 1] VRAM 즉각 반환: 애니메이션 종료 직후 이전 이미지 텍스처 해제 (RAM/VRAM 50% 절감)
        self.prev_item.setPixmap(QPixmap())

        self.cur_item.setPos(*self._cur_base_pos)
        self.cur_item.setScale(self._cur_base_scale)
        self.opacity_effect_cur.setOpacity(1.0)

    # ── 창 크기 조절 (GPU 스케일링) ─────────────────────────────
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_images()

    def _fit_images(self):
        rect = self.view.viewport().rect()
        self.scene.setSceneRect(QRectF(rect))

        self._fit_item(self.prev_item)
        self._fit_item(self.cur_item)
        self._cur_base_scale = self.cur_item.scale()
        self._cur_base_pos = (self.cur_item.pos().x(), self.cur_item.pos().y())

        # Settings Text 위치 업데이트 (중앙 정렬)
        if self._settings_visible:
            w = self.settings_text_item.boundingRect().width()
            h = self.settings_text_item.boundingRect().height()
            text_y = rect.height() - h - 30
            self.settings_text_item.setPos((rect.width() - w) / 2, text_y)

            bg_h = h + 60
            
        if getattr(self, '_is_loading', False):
            tw = self.loading_text.boundingRect().width()
            th = self.loading_text.boundingRect().height()
            w, h = tw + 40, th + 20
            cx, cy = rect.width() / 2, rect.height() / 2
            
            self.loading_bg.setRect(cx - w/2, cy - h/2, w, h)
            self.loading_shadow.setRect(cx - w/2 + 6, cy - h/2 + 6, w, h)
            self.loading_text.setPos(cx - tw/2, cy - th/2)
            self.settings_bg_item.setRect(0, rect.height() - bg_h, rect.width(), bg_h)

    def _fit_item(self, item: QGraphicsPixmapItem):
        rect = self.view.viewport().rect()
        if not item.pixmap().isNull():
            pm = item.pixmap()
            scale = min(rect.width() / pm.width(), rect.height() / pm.height())
            item.setScale(scale)
            nw, nh = pm.width() * scale, pm.height() * scale
            item.setPos((rect.width() - nw) / 2, (rect.height() - nh) / 2)

    # ── 타이머 ──────────────────────────────────────────────────
    def _on_slide_timeout(self):
        if self._paused:
            return
        self.time_left -= 1
        if self.time_left <= 0:
            self.time_left = self.vc.interval
            self._load_next()

    # ── 설정 (Settings) ─────────────────────────────────────────
    def _toggle_settings(self):
        self._settings_visible = not self._settings_visible
        if self._settings_visible:
            self._bump_settings()
        else:
            self.settings_text_item.hide()
            self.settings_bg_item.hide()

    def _bump_settings(self):
        self.settings_hide_timer.start(4000)
        self._draw_settings()

    def _change_setting(self, row: int, d: int):
        if row == 0:
            self._iv = (self._iv + d) % len(INTERVALS)
            self.vc.interval = INTERVALS[self._iv]
            self.cfg.save_viewer_settings()
            self._osd(f"⏱  {INTERVAL_LABELS[self._iv]}")
        elif row == 1:
            self._ef = (self._ef + d) % len(EFFECTS)
            self.vc.effect = EFFECTS[self._ef]
            self.cfg.save_viewer_settings()
            self._osd(f"✦  {EFFECTS[self._ef]}")
        elif row == 2:
            self._tm = (self._tm + d) % len(TIMERS)
            if self._sleep_timer:
                self._sleep_timer.stop()
            sec = TIMER_SECS[self._tm]
            if sec > 0:
                self._sleep_timer = QTimer(self)
                self._sleep_timer.setSingleShot(True)
                self._sleep_timer.timeout.connect(self._do_sleep)
                self._sleep_timer.start(sec * 1000)
            self._osd(f"◔  Sleep: {TIMERS[self._tm]}")
        elif row == 3:
            self.vc.wakelock = not self.vc.wakelock
            self._apply_wakelock(self.vc.wakelock)
            self.cfg.save_viewer_settings()
            self._osd(f"☼  Wakelock: {'On' if self.vc.wakelock else 'Off'}")

    def _draw_settings(self):
        lines = []
        vals = [INTERVAL_LABELS[self._iv], EFFECTS[self._ef], TIMERS[self._tm], "On" if self.vc.wakelock else "Off"]
        for i, (label, val) in enumerate(zip(ROW_LABELS, vals)):
            prefix = "▶ " if i == self._settings_row else "  "
            lines.append(f"{prefix}{label:<15} {val}")

        self.settings_text_item.setPlainText("\n".join(lines))
        self.settings_text_item.show()

        rect = self.view.viewport().rect()
        w = self.settings_text_item.boundingRect().width()
        h = self.settings_text_item.boundingRect().height()
        text_y = rect.height() - h - 30
        self.settings_text_item.setPos((rect.width() - w) / 2, text_y)

        bg_h = h + 60
        self.settings_bg_item.setRect(0, rect.height() - bg_h, rect.width(), bg_h)
        self.settings_bg_item.show()

    # ── 이벤트 처리 (키보드 단축키 콜백, 마우스) ────────────────────────────
    def _on_up(self):
        if self._settings_visible:
            self._settings_row = (self._settings_row - 1) % len(ROW_LABELS)
            self._bump_settings()

    def _on_down(self):
        if self._settings_visible:
            self._settings_row = (self._settings_row + 1) % len(ROW_LABELS)
            self._bump_settings()

    def _on_left(self):
        if self._settings_visible:
            self._change_setting(self._settings_row, -1)
            self._bump_settings()
        else:
            self.time_left = self.vc.interval
            self._load_prev()

    def _on_right(self, force_next=False):
        if self._settings_visible and not force_next:
            self._change_setting(self._settings_row, +1)
            self._bump_settings()
        else:
            self.time_left = self.vc.interval
            self._load_next()

    def _toggle_pause(self):
        self._paused = not self._paused
        self._osd("⏸  Paused" if self._paused else "▶  Playing")

    def _toggle_debug(self):
        active = "ACTIVE" if self.anim.state() == QPropertyAnimation.State.Running else "IDLE"
        self._osd(f"Load: {self._last_load_ms:.1f}ms\nState: {active}", 3.0)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.time_left = self.vc.interval

    # ── Wakelock 관리 / 종료 ────────────────────────────────────
    def _apply_wakelock(self, enable: bool):
        if enable:
            if not self._caffeinate_proc:
                try:
                    self._caffeinate_proc = subprocess.Popen(["caffeinate", "-d"])
                    logger.info("Wakelock ON (caffeinate -d started)")
                except Exception as e:
                    logger.warning(f"caffeinate failed: {e}")
        else:
            if self._caffeinate_proc:
                self._caffeinate_proc.terminate()
                self._caffeinate_proc.wait()
                self._caffeinate_proc = None
                logger.info("Wakelock OFF")

    def _do_sleep(self):
        self._osd("Sleeping in 5s…", 5.0)
        time.sleep(5)
        subprocess.run(["pmset", "displaysleepnow"], check=False)
        self.close()

    def _quit(self):
        self.close()

    def closeEvent(self, event):
        # 1. 모든 타이머 정지 (메모리 릭 방지)
        if self._sleep_timer:
            self._sleep_timer.stop()
        self.slide_timer.stop()
        self.hide_timer.stop()
        if hasattr(self, 'settings_hide_timer'):
            self.settings_hide_timer.stop()

        # 2. 진행 중인 애니메이션 강제 종료 (QVariantAnimation C++ 파괴 충돌 방지)
        if hasattr(self, 'anim'):
            self.anim.stop()

        # 3. Wakelock 해제
        self._apply_wakelock(False)

        # 4. 백그라운드 스레드 안전 종료 대기 (Destroyed while thread is running 에러 방지)
        if hasattr(self, 'loader') and self.loader.isRunning():
            self.loader.quit()
            self.loader.wait()  # 200ms 시간 제한 해제 (대용량 이미지 읽기 완료 보장)

        super().closeEvent(event)
