import os
import json
import sys

def generate_json(target_dir="library"):
    images_dir = None
    # Find the images directory inside the target directory
    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        if os.path.isdir(item_path):
            images_dir = item_path
            break
            
    if not images_dir:
        print(f"Error: Could not find any folder inside {target_dir}")
        sys.exit(1)
        
    print(f"Scanning folder: {images_dir}")
    
    images = []
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    
    for filename in os.listdir(images_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in valid_exts:
            images.append({
                "file": filename,
                "rejected": False
            })
            
    # Sort alphabetically
    images.sort(key=lambda x: x["file"])
    
    json_path = os.path.join(target_dir, "images.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"images": images}, f, indent=2, ensure_ascii=False)
        
    print(f"Success! Created {json_path} with {len(images)} images.")
    print(f"Now you can upload '{json_path}' and '{images_dir}' to Cloudflare!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "library"
    generate_json(target)
