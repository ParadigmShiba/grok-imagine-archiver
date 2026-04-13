# System Architecture and Technical Decisions (Architecture)

This document records the technical considerations, challenges encountered, and final solutions when implementing various major mechanisms in **Grok Imagine Collection**.

## 1. Cloudflare Anti-Bot Bypass Strategy
**Initial Attempt**: Used standard `playwright` (even combined with `playwright-stealth`) to launch a browser and attempted to use `page.on("websocket")`.
**Issue Encountered**: Grok has extremely strict Cloudflare validation in front of it. Standard headless or controlled Playwright browsers were immediately flagged as bots, resulting in an infinite Turnstile validation loop ("Verify you are human").
**Solution**:
Adopted the **CDP (Chrome DevTools Protocol) Standalone Process Mounting Mode**.
1. Used `subprocess.Popen` to natively launch a local `chrome.exe` via conventional command line, assigning a `--remote-debugging-port=<Dynamic_Port>` and a standalone `--user-data-dir` (ensuring login sessions are not polluted by the original browser and can be persisted).
2. **Port & Process Isolation Mechanism**:
   - Abandoned the hardcoded `9222` port and switched to using Python's underlying `socket` to find a random available Port. This completely solved the connection failure (`ECONNREFUSED`) issues caused by **Hyper-V or Docker reserved ranges (WSAEACCES 0x271D)** on Windows.
   - Added the `--new-window` launch parameter. When there's an already active background process (Background Apps) inside the `chrome_profile`, launching a new Chrome process defaults to delegating the web page task to the existing background app, and the new process immediately exits (`Exit Code 0`). Adding this parameter forces the creation of a standalone instance and mounts an independent DevTools listener.
3. Used `playwright.chromium.connect_over_cdp` to quietly intercept the legitimately running browser. This action completely erases Playwright fingerprints, achieving a 100% success rate in entering the site.

## 2. WSS Decoding and "Blank Shot" Protection
**Observed Phenomenon**:
- Image generation is not a one-step process; Grok continuously sends payloads via `wss://grok.com/ws/imagine/listen`.
- Initially mistaken to believe images would be natively embedded as base64 inside `imageBytes`, but they are actually public `url: "https://imagine-public..."`.
- If Prompts are flagged by the system as R-18 violations, a Request is still sent, but it might return **0 images**.
**Folder Archiving Mechanism Refactoring**:
If we relied solely on "receiving an image (`job_id`)" to create a folder, we would miss Prompts that failed to generate images.
Therefore, the system logic was changed to:
- **First Trigger Point**: As soon as a JSON payload contains a `request_id` (regardless of whether it contains images), immediately create a folder for that Request using the current Timestamp, and write `prompt.txt` simultaneously.
- **Second Trigger Point**: If subsequent WSS broadcasts carry the image URL for the same `request_id`, it is automatically downloaded to the created folder using the HTTP module. This ensures "One conversation round = One complete folder".

## 3. Web UI Frontend Architecture Rules (Event Delegation)
To prevent potential Memory Leaks caused by future feature additions, the project strictly enforces these rules for frontend development (`frontend/app.js`):
- **No Static Loop Binding**: It is strictly forbidden to attach `.addEventListener` individually to every `<img />` when rendering the image grid.
- **Adopt Event Delegation**: Attach a Click event only once to the single, static parent container (`#gallery-container`). Use `event.target` to deduce the clicked target and determine if it's a zoom-in action, achieving O(1) complexity and flawless DOM mounting.

## 4. Adaptive Flex Feed and Advanced Interactions
Evolved from an initial 2x2 layout to the final **Full-Size Feed Dynamic Wall**:
- **Vertical Feed Layout**: Changed `.gallery-grid` to `flex-direction: column`. Every Request independently occupies an entire horizontal block, and its child images are displayed side-by-side in a 1x4 layout (`object-fit: contain`) to guarantee 100% uncropped original proportions.
- **Cinematic Viewer (Pan & Zoom Modal)**:
   - Abandoned traditional frameworks; fully implemented using native events (`wheel`, `contextmenu`, `mousemove`).
   - Defaulted the main image to perfectly fill `75vw`, combined with pure CSS `will-change: transform` and JS mathematical calculations to achieve a zero-latency (GPU-accelerated) zoom experience and block **right-click triggered drag panning** functionality.
- **Smart Incremental Updates (Smart Polling)**:
   - The frontend and FastAPI perform background asynchronous polling every 3 seconds.
   - To prevent DOM re-render flickering from interrupting the user when zooming in on an image or copying text, the script only triggers a Re-render when the total `total_images` changes or the latest `request_id` changes.

## 5. API Incremental Caching Engine (mtime-based Incremental Caching)
**Issue Encountered**: When the number of folders in `gallery/` exceeded 2000, because the backend completely scanned all branches and read `prompt.txt` 2000 times strictly every 3 seconds, the API and frontend auto-polling experienced severe lag (up to 10 seconds).
**Solution**:
Introduced incremental scanning relying on the ultra-fast OS primitive `os.path.getmtime`:
- Maintains a `gallery_cache.json` alongside an in-memory dictionary. Upon receiving a new request, it only compares the `mtime` of all folders; unchanged ones are accessed natively in `O(1)` from cache.
- Dropped the IO cost of `os.listdir` and deep inner-file scanning to near zero. Through tests, the update time for 2000 data items plummeted from 10.6 seconds down to under **0.02 seconds**.

## 6. Historical Video Interception and Local Persistence (Native File Download Hook)
To fulfill the need to back up videos manually during active usage:
- Instead of complex analysis of frontend video players or Fetch API architectures, the script directly hooks into the low-level Playwright event: `page.on("download", on_download)`.
- Whether it is an original `<a href download>` redirect or a virtual download dispatched through the frontend executing `blob:`, it naturally triggers Playwright's core stream capture mechanism. The script merely checks for the `.mp4` string extension, allowing those videos to be safely routed directly into the local `./video-gallery/` folder.
