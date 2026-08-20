"""
collector/collector.py
────────────────────────
PortraitFrame 메인 오케스트레이터.

흐름:
  1. Source Adapter 로 이미지 후보 발견
  2. 이미 수집한 URL 인지 확인 (skip)
  3. 임시 디렉토리에 다운로드
  4. 파일 검증 (크기, 해상도, portrait 방향)
  5. 중복 검사 (SHA256 + pHash)
  6. Normalizer 로 1440×3440 WebP 변환
  7. Quality 검사
  8. Library 에 등록 + images.json 저장

invariant: library/images/ 에는 1440×3440 파일만 존재한다.
"""
from __future__ import annotations

import logging
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from tqdm import tqdm
from colorama import Fore, Style, init as colorama_init

from collector.library import Library, TARGET_WIDTH, TARGET_HEIGHT
from collector.downloader import Downloader, DownloadError
from collector.normalizer import Normalizer, NormalizerError
from collector.quality import QualityFilter
from collector.dedupe import Deduper
from collector.sources.base import ImageCandidate
from collector.sources.wallhaven import WallhavenAdapter
from collector.sources.reddit import RedditAdapter
from collector.sources.flickr import FlickrAdapter
from collector.sources.artstation import ArtstationAdapter
from collector.sources.unsplash import UnsplashAdapter
from collector.sources.pexels import PexelsAdapter
from collector.sources.generic import GenericAdapter

colorama_init(autoreset=True)
logger = logging.getLogger(__name__)


class Collector:
    """PortraitFrame 이미지 수집 오케스트레이터."""

    def __init__(self, config: dict):
        self.config = config
        self.library = Library(config)
        self.downloader = Downloader(config)
        self.normalizer = Normalizer(config)
        self.quality_filter = QualityFilter(config)
        self.deduper = Deduper(config)
        self.deduper.load_from_library(self.library)
        self.sources = self._init_sources()
        # 병렬 다운로드용 lock (library/deduper write 보호)
        self._lib_lock = threading.Lock()
        c_cfg = config.get("collector", {})
        self._workers = int(c_cfg.get("workers", 3))

    # ──────────────────────────────────────────
    # 공개 커맨드
    # ──────────────────────────────────────────

    def collect(
        self,
        source_names: Optional[list[str]] = None,
        limit: Optional[int] = None,
    ) -> None:
        """이미지 수집."""
        targets = (
            {n: s for n, s in self.sources.items() if n in source_names}
            if source_names
            else self.sources
        )

        if not targets:
            logger.error("No enabled sources found. Check config.yaml")
            return

        for src_name, adapter in targets.items():
            logger.info("=== Source: %s ===", src_name)
            self._collect_from(adapter, limit=limit)

        self.library.save()
        self._print_brief_stats()

    def normalize(self) -> None:
        """
        originals/ 또는 임시 폴더에 있는 원본을
        library/images/ 에 1440×3440 WebP 로 재처리.
        (현재는 collect 시 자동 처리되므로 별도 실행 불필요)
        """
        logger.info("normalize: all images in library already normalized during collect.")
        self.audit()

    def audit(self) -> None:
        """라이브러리 무결성 검사 + 통계 출력."""
        print()
        print(f"{Fore.CYAN}{'─'*40}")
        print(f"{Fore.CYAN}  Library Audit")
        print(f"{Fore.CYAN}{'─'*40}")

        images_dir = self.library.images_dir
        all_files = list(images_dir.glob("*.webp"))

        broken = []
        wrong_size = []
        ok = []

        for f in tqdm(all_files, desc="Checking", unit="img", leave=False):
            try:
                from PIL import Image
                img = Image.open(f)
                w, h = img.size
                if w != TARGET_WIDTH or h != TARGET_HEIGHT:
                    wrong_size.append((f, w, h))
                else:
                    ok.append(f)
            except Exception as e:
                broken.append((f, str(e)))

        stats = self.library.stats()
        disk_mb = stats["disk_bytes"] / (1024 * 1024)

        print(f"  {'Images (DB):':<25} {stats['active']}")
        print(f"  {'Files on disk:':<25} {len(all_files)}")
        print(f"  {'Valid 1440×3440:':<25} {Fore.GREEN}{len(ok)}{Style.RESET_ALL}")
        print(f"  {'Wrong size:':<25} {Fore.RED}{len(wrong_size)}{Style.RESET_ALL}")
        print(f"  {'Broken:':<25} {Fore.RED}{len(broken)}{Style.RESET_ALL}")
        print(f"  {'Disk usage:':<25} {disk_mb:.1f} MB")
        print(f"  {'Favorites:':<25} {Fore.YELLOW}{stats['favorites']}{Style.RESET_ALL}")
        print(f"  {'Rejected:':<25} {stats['rejected']}")
        print()

        if stats["sources"]:
            print(f"  {'Source Stats':}")
            for src, s in stats["sources"].items():
                total = s["downloaded"]
                accepted = s["accepted"]
                rate = (accepted / total * 100) if total > 0 else 0
                print(f"    {src:<16} downloaded={total}  accepted={accepted}  rate={rate:.0f}%")
        print()

        if wrong_size:
            print(f"{Fore.RED}  ⚠ Wrong-size files:")
            for f, w, h in wrong_size:
                print(f"    {f.name}: {w}×{h}")
        if broken:
            print(f"{Fore.RED}  ⚠ Broken files:")
            for f, err in broken:
                print(f"    {f.name}: {err}")

        if not wrong_size and not broken:
            print(f"{Fore.GREEN}  ✓ Audit passed — all files are valid 1440×3440")
        print()

    # ──────────────────────────────────────────
    # 내부 수집 루프
    # ──────────────────────────────────────────

    def _collect_from(self, adapter, limit: Optional[int]) -> None:
        """단일 소스에서 이미지 수집 (병렬 처리)."""
        if hasattr(adapter, "discover_all"):
            candidates = adapter.discover_all(limit_per_query=limit or 50)
        else:
            candidates = adapter.discover(limit=limit or 50)

        if not candidates:
            logger.warning("[%s] No candidates discovered.", adapter.name)
            return

        logger.info("[%s] %d candidates → %d workers",
                    adapter.name, len(candidates), self._workers)

        accepted = skipped = rejected = 0
        lock = threading.Lock()  # 카운터 보호

        with tempfile.TemporaryDirectory(prefix="portrait_frame_") as tmpdir:
            tmp_path = Path(tmpdir)

            with ThreadPoolExecutor(max_workers=self._workers,
                                    thread_name_prefix="collector") as pool:
                futures = {
                    pool.submit(self._process_candidate, c, tmp_path): c
                    for c in candidates
                }

                pbar = tqdm(as_completed(futures),
                            total=len(futures),
                            desc=f"[{adapter.name}]",
                            unit="img")
                for future in pbar:
                    try:
                        result = future.result()
                    except Exception as e:
                        logger.error("Worker error: %s", e)
                        result = "rejected"
                    with lock:
                        if result == "accepted":
                            accepted += 1
                        elif result == "skipped":
                            skipped += 1
                        else:
                            rejected += 1
                    pbar.set_postfix(ok=accepted, skip=skipped, rej=rejected)

        logger.info(
            "[%s] Done — accepted=%d, skipped=%d, rejected=%d",
            adapter.name, accepted, skipped, rejected,
        )

    def _process_candidate(self, candidate: ImageCandidate, tmp_dir: Path) -> str:
        """단일 후보 처리 파이프라인. 성공시 'accepted', 거절시 'rejected', 중복시 'skipped'."""
        try:
            return self._process_candidate_internal(candidate, tmp_dir)
        except Exception as e:
            logger.warning("Pipeline error for %s: %s", candidate.source_url, e)
            return "rejected"

    def _process_candidate_internal(self, candidate: ImageCandidate, tmp_dir: Path) -> str:
        """
        단일 후보 처리.
        Returns: 'accepted' | 'skipped' | 'rejected'
        """
        # 이미 수집한 URL 인지 확인
        if self.library.has_source_url(candidate.source_url):
            logger.debug("Skip (already collected): %s", candidate.source_url)
            return "skipped"

        # 다운로드
        ext = self._guess_ext(candidate.image_url)
        tmp_file = tmp_dir / f"download{ext}"
        try:
            self.downloader.download(candidate.image_url, tmp_file)
        except DownloadError as e:
            logger.warning("Download failed: %s — %s", candidate.image_url, e)
            return "rejected"

        # PIL 열기
        try:
            from PIL import Image
            img = Image.open(tmp_file).convert("RGB")
        except Exception as e:
            logger.warning("Cannot open image: %s — %s", tmp_file, e)
            return "rejected"

        # 해상도/방향 사전 검사
        w, h = img.size
        if w < TARGET_WIDTH or h < TARGET_HEIGHT:
            logger.debug("Too small: %dx%d", w, h)
            return "rejected"
        if w > h:
            logger.debug("Not portrait: %dx%d", w, h)
            return "rejected"

        # 중복 검사 (lock 안에서)
        with self._lib_lock:
            is_dup, sha256, phash = self.deduper.is_duplicate(tmp_file, img)
            if is_dup:
                logger.debug("Duplicate: %s", candidate.source_url)
                return "skipped"

        # 정규화 (1440×3440 WebP) — lock 밖, CPU 집약 작업
        img_id_placeholder = f"tmp_{sha256[:8]}"
        # 스레드별 고유 파일명으로 충돌 방지
        import threading as _t
        tid = _t.get_ident() % 100000
        dst_tmp = tmp_dir / f"{img_id_placeholder}_{tid}.webp"
        try:
            norm_info = self.normalizer.process(tmp_file, dst_tmp)
        except NormalizerError as e:
            logger.warning("Normalization failed: %s — %s", candidate.source_url, e)
            return "rejected"

        # 품질 검사
        try:
            norm_img = Image.open(dst_tmp).convert("RGB")
            ok, quality_score, reason = self.quality_filter.is_acceptable(dst_tmp, norm_img)
        except Exception as e:
            logger.warning("Quality check error: %s", e)
            return "rejected"

        if not ok:
            logger.debug("Quality fail: %s — %s", candidate.source_url, reason)
            return "rejected"

        # Library 등록 + 파일 이동 (lock 안에서)
        with self._lib_lock:
            entry = {
                "file": "",
                "width": TARGET_WIDTH,
                "height": TARGET_HEIGHT,
                "source": candidate.source,
                "source_url": candidate.source_url,
                "original_url": candidate.image_url,
                "original_width": w,
                "original_height": h,
                "native_1440x3440": norm_info["native_1440x3440"],
                "phash": phash,
                "sha256": sha256,
                "category": candidate.category or [],
                "tags": candidate.tags or [],
                "quality_score": quality_score,
                "extra": candidate.extra,
            }
            img_id = self.library.add(entry)
            final_filename = f"{img_id}.webp"
            final_path = self.library.images_dir / final_filename
            shutil.move(str(dst_tmp), str(final_path))
            self.library.update(img_id, file=final_filename)
            self.deduper.register(sha256, phash)

        self._assert_final(final_path)
        logger.info("✓ Saved: %s  (%s, q=%.2f)", final_filename, norm_info["case"], quality_score)
        return "accepted"

    # ──────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────

    def _init_sources(self) -> dict:
        adapters = {
            "wallhaven": WallhavenAdapter,
            "reddit": RedditAdapter,
            "flickr": FlickrAdapter,
            "artstation": ArtstationAdapter,
            "unsplash": UnsplashAdapter,
            "pexels": PexelsAdapter,
            "generic": GenericAdapter,
        }
        result = {}
        for name, cls in adapters.items():
            adapter = cls(self.config)
            if adapter.is_enabled():
                result[name] = adapter
                logger.info("Source enabled: %s", name)
        return result

    @staticmethod
    def _guess_ext(url: str) -> str:
        url_lower = url.lower().split("?")[0]
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            if url_lower.endswith(ext):
                return ext
        return ".jpg"

    @staticmethod
    def _assert_final(path: Path) -> None:
        from PIL import Image
        img = Image.open(path)
        w, h = img.size
        if w != TARGET_WIDTH or h != TARGET_HEIGHT:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"INVARIANT VIOLATED: {path.name} is {w}×{h}")

    def _print_brief_stats(self) -> None:
        stats = self.library.stats()
        disk_mb = stats["disk_bytes"] / (1024 * 1024)
        print(f"\n{Fore.GREEN}Library: {stats['active']} images | {disk_mb:.1f} MB{Style.RESET_ALL}")
