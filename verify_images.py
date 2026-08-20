import os
import json
from PIL import Image

library_dir = "library/images"
metadata_file = "library/images.json"
broken_dir = "library/broken_final"

os.makedirs(broken_dir, exist_ok=True)

if os.path.exists(metadata_file):
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
else:
    metadata = []

valid_images = []
broken_count = 0

for root, _, files in os.walk(library_dir):
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.avif', '.webp')):
            filepath = os.path.join(root, file)
            try:
                with Image.open(filepath) as img:
                    img.verify()
                valid_images.append(filepath)
            except Exception as e:
                broken_count += 1
                broken_path = os.path.join(broken_dir, file)
                os.rename(filepath, broken_path)
                print(f"Broken image found and moved: {file}")

print(f"Total valid images: {len(valid_images)}")
print(f"Total broken images: {broken_count}")
