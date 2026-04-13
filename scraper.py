import asyncio
import subprocess
import time
import os
import json
import base64
import socket
import sys
import urllib.request
from datetime import datetime
from playwright.async_api import async_playwright

USER_DATA_DIR = os.path.join(os.getcwd(), 'chrome_profile')
GALLERY_DIR = os.path.join(os.getcwd(), 'gallery')

job_timestamps = {}  # 'job' here actually refers to request_id

def ensure_gallery_dir():
    if not os.path.exists(GALLERY_DIR):
        os.makedirs(GALLERY_DIR)
        
    video_dir = os.path.join(os.getcwd(), 'video-gallery')
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)

async def on_download(download):
    filename = download.suggested_filename.lower()
    if filename.endswith(".mp4"):
        print(f"\n[{time.strftime('%H:%M:%S')}] 🎬 Intercepted video download: {download.suggested_filename}")
        video_dir = os.path.join(os.getcwd(), 'video-gallery')
        path = os.path.join(video_dir, download.suggested_filename)
        await download.save_as(path)
        print(f"[{time.strftime('%H:%M:%S')}] 💾 Video saved successfully: video-gallery/{download.suggested_filename}")
    elif filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
        print(f"\n[{time.strftime('%H:%M:%S')}] 🖼️ Intercepted image download: {download.suggested_filename}")
        image_dir = os.path.join(os.getcwd(), 'gallery', 'manual_downloads')
        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
        path = os.path.join(image_dir, download.suggested_filename)
        await download.save_as(path)
        print(f"[{time.strftime('%H:%M:%S')}] 💾 Image saved successfully: gallery/manual_downloads/{download.suggested_filename}")

async def on_websocket(ws):
    print(f"\n[{time.strftime('%H:%M:%S')}] 🔌 Detected WebSocket connection: {ws.url}")
    
    # Listen to all connections to grok.com
    if "grok.com" in ws.url:
        print(f"[{time.strftime('%H:%M:%S')}] 🎯 Interceptor mounted! Monitoring content...")
        
        def handle_message(payload):
            text = ""
            try:
                text = payload.decode('utf-8') if isinstance(payload, bytes) else payload
                
                # If it's a JSON string, try to parse it
                if text.strip().startswith('{'):
                    data = json.loads(text)
                    
                    # Whether receiving an image or progress, process uniformly if there is a request_id to catch the worst-case scenario of 0 images
                    req_id = data.get("request_id")
                    if req_id:
                        # Use the earliest appearance time of req_id as the batch timestamp
                        if req_id not in job_timestamps:
                            job_timestamps[req_id] = datetime.now().strftime("%Y%m%d_%H%M%S")
                            
                        folder_name = f"{req_id}_{job_timestamps[req_id]}"
                        folder_path = os.path.join(GALLERY_DIR, folder_name)
                        
                        if not os.path.exists(folder_path):
                            os.makedirs(folder_path)
                            
                        # Save prompt.txt
                        prompt = data.get("full_prompt") or data.get("prompt", "")
                        prompt_path = os.path.join(folder_path, "prompt.txt")
                        if not os.path.exists(prompt_path) and prompt:
                            with open(prompt_path, "w", encoding="utf-8") as f:
                                f.write(prompt)
                        
                        # Check if it contains an image URL, if so, download it
                        image_url = data.get("url")
                        if image_url and str(image_url).startswith("http"):
                            image_id = data.get("id", data.get("job_id", "image"))
                            image_path = os.path.join(folder_path, f"{image_id}.jpg")
                            
                            if not os.path.exists(image_path):
                                try:
                                    import urllib.request
                                    req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                                    with urllib.request.urlopen(req) as resp:
                                        with open(image_path, "wb") as f:
                                            f.write(resp.read())
                                    print(f"[{time.strftime('%H:%M:%S')}] 💾 Image successfully downloaded: gallery/{folder_name}/{image_id}.jpg")
                                except Exception as e:
                                    print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed to download image: {e}")
                                    
                        elif data.get("type") == "json" and data.get("current_status"):
                            # Only print the status, ensuring folders and prompt.txt are already created earlier
                            print(f"[{time.strftime('%H:%M:%S')}] ⏳ Image generation status update: {data.get('current_status')}")

                            
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Error: {e}")

        ws.on("framereceived", handle_message)

async def main(args):
    ensure_gallery_dir()
    
    gui_proc = None
    gui_port = 8000
    if args.start_gallery:
        print("Starting background GUI gallery server...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            gui_port = s.getsockname()[1]
            
        gui_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api:app", "--port", str(gui_port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print(f"Waiting for GUI server to be ready on port {gui_port}...")
        start_wait = time.time()
        while time.time() - start_wait < 15:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{gui_port}/") as r:
                    if r.status == 200:
                        break
            except Exception:
                pass
            await asyncio.sleep(1)
            
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    browser_path = chrome_path if os.path.exists(chrome_path) else edge_path
    if not os.path.exists(browser_path):
        print("Could not find Chrome or Edge browser!")
        return

    print("Starting standalone browser (Anti-Bot CDP Mode)...")
    
    # Dynamically get an available port to avoid Windows Hyper-V reserved ranges (like 9222)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        free_port = s.getsockname()[1]

    proc = subprocess.Popen([
        browser_path, 
        f"--remote-debugging-port={free_port}", 
        f"--user-data-dir={USER_DATA_DIR}",
        "--new-window"
    ])
    
    print(f"Waiting for browser to start and internal port ({free_port})...")
    async with async_playwright() as p:
        browser = None
        for attempt in range(15):
            # Check if the subprocess ended unexpectedly
            if proc.poll() is not None:
                print(f"Browser process ended prematurely! Exit Code: {proc.returncode}")
                # Give up connection, break retry loop
                break
                
            try:
                browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{free_port}")
                print("Connection successful! Everything is ready.")
                break
            except Exception:
                await asyncio.sleep(1)
                
        if not browser:
            print(f"Connection failed: Cannot connect to 127.0.0.1:{free_port} or browser didn't start correctly.")
            if proc.poll() is None:
                proc.terminate()
            return
            
        contexts = browser.contexts
        # Bind listeners to all currently existing tabs (prevents Chrome restoring old tabs leading to mount failure)
        target_page = None
        def setup_page(p):
            p.on("websocket", on_websocket)
            p.on("download", on_download)

        for context in contexts:
            for page in context.pages:
                setup_page(page)
                if target_page is None:
                    target_page = page
            # Automatically bind listeners to newly opened tabs in the future
            context.on("page", setup_page)

        if target_page:
            try:
                await target_page.goto("https://grok.com/")
            except Exception:
                pass
            
            if args.start_gallery:
                try:
                    gallery_page = await contexts[0].new_page()
                    await gallery_page.goto(f"http://127.0.0.1:{gui_port}/")
                    print("🖼️ Opened a new gallery tab!")
                    # Ensure focus returns to the original Grok page so users can generate images directly
                    await target_page.bring_to_front()
                except Exception as e:
                    print(f"Failed to open gallery tab: {e}")

        print("\n" + "="*50)
        print("🟢 System is ready!")
        print("Please operate freely in the browser (feel free to open new tabs).")
        print("As long as you see 'Detected WebSocket connection', the hook is successful.")
        print("Generated images will be automatically saved to gallery/!")
        print("="*50 + "\n")
        
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            proc.terminate()
            if gui_proc:
                gui_proc.terminate()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grok Scraper - Manual Image Generation Interceptor")
    parser.add_argument("--start-gallery", action="store_true", help="Start Web UI gallery simultaneously and open a new tab")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
