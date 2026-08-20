import os
import json
import shutil
import random

src_images_dir = "library/images"
src_json = "library/images.json"

dest_root = "mini_upload_pack"
dest_images_dir = os.path.join(dest_root, "images")
dest_json = os.path.join(dest_root, "images.json")

os.makedirs(dest_images_dir, exist_ok=True)

with open(src_json, "r") as f:
    data = json.load(f)

valid_images = [img for img in data.get("images", []) if not img.get("rejected", False)]
selected_images = random.sample(valid_images, min(100, len(valid_images)))

for img in selected_images:
    filename = img["file"]
    src_path = os.path.join(src_images_dir, filename)
    if os.path.exists(src_path):
        shutil.copy2(src_path, os.path.join(dest_images_dir, filename))

with open(dest_json, "w") as f:
    json.dump({"images": selected_images}, f, indent=4)

print("mini_upload_pack created successfully!")
