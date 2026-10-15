# 🛠️ Setup Runbook, Development Workflow & Troubleshooting
**Environment Configuration • Server Operations • Verification Checklist • Debugging Runbook**

This runbook guides new engineers through setting up a development workstation, running servers, and troubleshooting common issues.

---

## 1. Prerequisites & System Requirements

* **Operating System**: macOS (Darwin, Apple Silicon M1/M2/M3/M4 recommended for VideoToolbox GPU acceleration).
* **Python**: Python 3.10+ (Current runtime: Python 3.12 at `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`).
* **Node.js**: Node 18+ and npm 9+.
* **FFmpeg**: Must have `h264_videotoolbox` enabled (standard on macOS Homebrew: `brew install ffmpeg`).
* **DaVinci Resolve**: DaVinci Resolve Studio or Free edition (optional, required only for native timeline IPC sync).

---

## 2. Environment Configuration (`backend/.env`)

Create or verify `backend/.env` with the active project API keys:

```env
# Stock Media API Keys
PEXELS_API_KEY="[configured in backend/.env — value omitted]"
PIXABAY_API_KEY="[configured in backend/.env — value omitted]"

# Google Gemini API Key (Gemini 2.5 Flash Vision Reranker)
GEMINI_API_KEY="[configured in backend/.env — value omitted]"

# Twelve Labs API Key (Marengo 3.0 & Pegasus 1.5)
TWELVE_LABS_API_KEY="[configured in backend/.env — value omitted]"
```

---

## 3. Installation & Server Operations

### 3.1 Install Dependencies

#### Backend
```bash
cd /Users/sushil/.gemini/antigravity/scratch/davinci-companion/backend
python3 -m pip install -r requirements.txt
python3 -m pip install resvg-py google-genai
```

#### Frontend
```bash
cd /Users/sushil/.gemini/antigravity/scratch/davinci-companion/frontend
npm install
```

---

### 3.2 Starting the Servers

#### Method A: One-Touch Script
```bash
cd /Users/sushil/.gemini/antigravity/scratch/davinci-companion
./start_companion.sh
```

#### Method B: Dedicated Terminal Processes

**Terminal 1 (FastAPI Backend)**:
```bash
cd /Users/sushil/.gemini/antigravity/scratch/davinci-companion/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```
* Status check: Visit `http://localhost:8002/docs`

**Terminal 2 (Vite Frontend)**:
```bash
cd /Users/sushil/.gemini/antigravity/scratch/davinci-companion/frontend
npm run dev
```
* Studio URL: Visit `http://localhost:5174`

---

## 4. Verification Checklist

Run these quick checks after starting the servers:

1. **Backend Health & Credit Sync**:
   ```bash
   curl -s http://localhost:8002/api/media/twelve-labs/credits
   ```
   * Expected: `{"has_api_key": true, "remaining_minutes": 575.8, ...}`
2. **Feedback API Statistics**:
   ```bash
   curl -s http://localhost:8002/api/feedback/stats
   ```
   * Expected: `{"total_decisions": 124, "summary_text": "124 decisions → 71 kept | 31 cut | 22 modified", ...}`
3. **Frontend Production Build**:
   ```bash
   cd /Users/sushil/.gemini/antigravity/scratch/davinci-companion/frontend
   npm run build
   ```
   * Expected: `✓ built in 1.13s` with 0 TypeScript errors.

---

## 5. Practical Troubleshooting Runbook

### Issue 1: `NameResolutionError: Failed to resolve 'api.twelvelabs.io'`
* **Symptom**: Popup alert appears saying `Failed to resolve 'api.twelvelabs.io' ([Errno 8] nodename nor servname provided, or not known)`.
* **Root Cause**: The backend process was launched in an isolated sandbox or container without outbound network privileges, blocking DNS lookups.
* **Fix**: Ensure the backend server is launched with network permissions (`BypassSandbox: true`). Test connectivity using:
  ```bash
  python3 -c "import socket; print(socket.gethostbyname('api.twelvelabs.io'))"
  ```
  Should return `52.32.20.235`.

---

### Issue 2: `Indexing asset failed (202)`
* **Symptom**: Twelve Labs index call fails with `Indexing asset failed (202): {"_id": "...", "asset_id": "..."}`.
* **Root Cause**: Twelve Labs returns `HTTP 202 Accepted` for asynchronous asset indexing. If the client only checks for `[200, 201]`, it treats 202 as an error.
* **Fix**: In `twelve_labs_service.py`, ensure line 322 includes 202:
  ```python
  if resp.status_code not in [200, 201, 202]:
  ```

---

### Issue 3: `OSError: [Errno 28] No space left on device`
* **Symptom**: Uploading a video crashes with disk space errors.
* **Root Cause**: Host Mac disk is near 100% capacity and duplicate 850MB video proxies were filling storage.
* **Fix**:
  1. Check free disk space: `df -h /`
  2. The system now uses APFS relative symlinks and hardware CRF 28 transcoding, requiring only ~14MB per video.
  3. Delete obsolete projects via the UI trash button (safely moves project directories to `~/.Trash`).

---

### Issue 4: Port `8002` or `5174` Already in Use
* **Symptom**: `ERROR: [Errno 48] Address already in use`
* **Fix**: Identify and kill the stale process:
  ```bash
  lsof -ti :8002 | xargs kill -9
  lsof -ti :5174 | xargs kill -9
  ```

---

### Issue 5: Georgia Font Missing in Burn-In Rendering
* **Symptom**: Exported MP4 falls back to default sans-serif font or throws font file not found.
* **Fix**: On macOS, verify the system Georgia TrueType fonts exist:
  ```bash
  ls -l "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
  ls -l "/System/Library/Fonts/Supplemental/Georgia.ttf"
  ```
  `burnin_renderer.py` includes automatic fallbacks to `/Library/Fonts/` and `Helvetica`.

---

### Issue 6: `TypeError: Cannot read properties of undefined (reading 'aspect_ratio')`
* **Symptom**: Browser crashes with a white screen when opening an empty project.
* **Fix**: Ensure all components (`VideoViewer`, `CanvasOverlay`) use optional chaining:
  ```typescript
  const ratio = project?.aspect_ratio || "9:16";
  ```
