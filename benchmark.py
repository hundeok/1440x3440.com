import time
from pathlib import Path
import pygame
from PIL import Image

def test_pil(path):
    t0 = time.time()
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    scale = min(1440 / iw, 3440 / ih)
    nw = max(1, round(iw * scale))
    nh = max(1, round(ih * scale))
    if abs(scale - 1.0) > 0.005:
        img = img.resize((nw, nh), Image.LANCZOS)
    raw = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
    return time.time() - t0

def test_pygame(path):
    t0 = time.time()
    raw = pygame.image.load(str(path)).convert()
    iw, ih = raw.get_size()
    scale = min(1440 / iw, 3440 / ih)
    nw = max(1, round(iw * scale))
    nh = max(1, round(ih * scale))
    if abs(scale - 1.0) > 0.005:
        raw = pygame.transform.smoothscale(raw, (nw, nh))
    return time.time() - t0

# Pygame needs a display context for .convert()
pygame.init()
pygame.display.set_mode((100, 100), pygame.HIDDEN)

import glob
files = glob.glob("library/images/*.webp")
if not files:
    print("No images found for benchmark")
else:
    path = files[0]
    print(f"--- Benchmark Results on {Path(path).name} ---")
    
    # Warmup
    test_pil(path)
    test_pygame(path)
    
    # Average of 5 runs
    pil_total = sum(test_pil(path) for _ in range(5)) / 5.0
    pyg_total = sum(test_pygame(path) for _ in range(5)) / 5.0
    
    print(f"Old (PIL + LANCZOS) Load Time:  {pil_total*1000:.1f} ms")
    print(f"New (Pygame native) Load Time:  {pyg_total*1000:.1f} ms")
    print(f"Performance Speedup:            {pil_total/pyg_total:.1f}x Faster")
