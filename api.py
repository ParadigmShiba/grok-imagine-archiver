import os
import json
import threading
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

GALLERY_CACHE_FILE = "gallery_cache.json"
gallery_cache_lock = threading.Lock()
gallery_cache_data = {}
cache_loaded = False

def init_cache():
    global gallery_cache_data, cache_loaded
    if not cache_loaded:
        if os.path.exists(GALLERY_CACHE_FILE):
            try:
                with open(GALLERY_CACHE_FILE, "r", encoding="utf-8") as f:
                    gallery_cache_data = json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
                gallery_cache_data = {}
        cache_loaded = True

def save_cache():
    try:
        with open(GALLERY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(gallery_cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("gallery", exist_ok=True)
os.makedirs("frontend", exist_ok=True)

app.mount("/gallery", StaticFiles(directory="gallery"), name="gallery")

@app.get("/api/gallery")
def get_gallery():
    global gallery_cache_data
    gallery_dir = "gallery"
    
    with gallery_cache_lock:
        init_cache()
        cache_updated = False
        
        # Get current actual folder list
        current_folders = set()
        try:
            entries = os.listdir(gallery_dir)
        except Exception:
            entries = []
            
        for folder_name in entries:
            folder_path = os.path.join(gallery_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
                
            current_folders.add(folder_name)
            
            try:
                current_mtime = os.path.getmtime(folder_path)
            except Exception:
                current_mtime = 0
                
            # Perform deep scan if folder is not in cache or mtime changed
            cached_info = gallery_cache_data.get(folder_name)
            if not cached_info or cached_info.get("mtime") != current_mtime:
                prompt = ""
                prompt_path = os.path.join(folder_path, "prompt.txt")
                if os.path.exists(prompt_path):
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        prompt = f.read()
                        
                images = []
                for file in os.listdir(folder_path):
                    if file.endswith((".jpg", ".png", ".jpeg")):
                        images.append(f"/gallery/{folder_name}/{file}")
                
                parts = folder_name.split("_")
                if len(parts) >= 3:
                    date_part = parts[-2]
                    time_part = parts[-1]
                    sort_key = f"{date_part}_{time_part}"
                    
                    display_time = ""
                    if len(time_part) == 6:
                        display_time = f"{time_part[0:2]}:{time_part[2:4]}:{time_part[4:6]}"
                else:
                    sort_key = folder_name
                    display_time = "Unknown"
                    
                gallery_cache_data[folder_name] = {
                    "mtime": current_mtime,
                    "data": {
                        "id": folder_name,
                        "prompt": prompt,
                        "images": images,
                        "sort_key": sort_key,
                        "display_time": display_time,
                        "image_count": len(images)
                    }
                }
                cache_updated = True
                
        # Remove cached folders that no longer exist
        folders_to_remove = [f for f in gallery_cache_data.keys() if f not in current_folders]
        if folders_to_remove:
            for f in folders_to_remove:
                del gallery_cache_data[f]
            cache_updated = True
            
        if cache_updated:
            save_cache()
            
        items = [info["data"] for info in gallery_cache_data.values()]
            
    # Sort by latest time
    items.sort(key=lambda x: x["sort_key"], reverse=True)
    return {"data": items}

# Mount frontend directory, 'html=True' allows pointing to index.html
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
