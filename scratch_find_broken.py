import os
import shutil
import numpy as np
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import json

def find_broken_images(library_dir):
    images_dir = Path(library_dir) / "images"
    json_path = Path(library_dir) / "images.json"
    broken_dir = Path(library_dir) / "broken_candidates"
    broken_dir.mkdir(exist_ok=True)
    
    files = list(images_dir.glob("*.webp"))
    broken_files = []
    
    print(f"Scanning {len(files)} images for grey truncation artifacts...")
    for f in tqdm(files):
        try:
            img = Image.open(f).convert("RGB")
            # 맨 아래 20줄 픽셀 가져오기
            arr = np.array(img)
            bottom_rows = arr[-20:, :, :]
            
            # 색상 편차(노이즈) 계산
            std = np.std(bottom_rows)
            mean_color = np.mean(bottom_rows, axis=(0, 1))
            
            # 편차가 거의 0(완전한 단색)이고, 회색(128부근)이거나 검은색인 경우
            if std < 1.0:
                broken_files.append((f, std, mean_color))
                # 일단 격리 폴더로 이동 (삭제 전 확인용)
                shutil.move(str(f), str(broken_dir / f.name))
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    print("\n[Result]")
    print(f"Found {len(broken_files)} broken/truncated images.")
    for bf, std, color in broken_files:
        print(f"  - {bf.name} (std: {std:.2f}, color: {color})")

    if broken_files:
        # Update images.json
        print("Removing broken images from images.json...")
        with open(json_path, "r", encoding="utf-8") as jf:
            db = json.load(jf)
        
        broken_names = {bf[0].name for bf in broken_files}
        new_images = [img for img in db.get("images", []) if img.get("file") not in broken_names]
        
        db["images"] = new_images
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(db, jf, indent=2, ensure_ascii=False)
        print("images.json updated.")

if __name__ == "__main__":
    find_broken_images("/Users/hdchom4/dev/portrait_frame/library")
