# 🔌 API Reference & Data Payloads Dictionary
**Complete REST API Specification • JSON Request/Response Schemas • Query Parameters**

All backend endpoints are served under `http://localhost:8002` and documented interactively at `http://localhost:8002/docs` (Swagger UI).

---

## 1. Projects API (`/api/projects`)

### 1.1 List Projects
* **Endpoint**: `GET /api/projects`
* **Response**: `200 OK`
  ```json
  [
    {
      "id": "proj_111sub_1789910026802",
      "name": "Project 111sub",
      "status": "ready",
      "duration_seconds": 88.75,
      "fps": 24,
      "aspect_ratio": "9:16",
      "created_at": "2026-09-20T12:00:00Z",
      "updated_at": "2026-09-22T14:00:00Z"
    }
  ]
  ```

### 1.2 Get Project Details
* **Endpoint**: `GET /api/projects/{project_id}`
* **Response**: `200 OK`
  ```json
  {
    "id": "proj_111sub_1789910026802",
    "name": "Project 111sub",
    "source_media_path": "/Users/sushil/.../make_the_video.mp4",
    "duration_seconds": 88.75,
    "fps": 24,
    "aspect_ratio": "9:16",
    "captions": [...],
    "tracks": [...],
    "settings": { ... }
  }
  ```

### 1.3 Create Project
* **Endpoint**: `POST /api/projects`
* **Payload**:
  ```json
  {
    "name": "My New Video",
    "aspect_ratio": "9:16"
  }
  ```
* **Response**: `201 Created`

### 1.4 Delete Project (with macOS Trash Cleanup)
* **Endpoint**: `DELETE /api/projects/{project_id}`
* **Behavior**: Uses macOS native `/usr/bin/trash` to safely move `backend/projects/{project_id}` to `~/.Trash`, deletes SQLite database records, and prevents orphan files on disk.
* **Response**: `200 OK` `{"success": true, "deleted_id": "..."}`

---

## 2. Media & Upload API (`/api/media`)

### 2.1 Native XHR Video Upload
* **Endpoint**: `POST /api/media/{project_id}/upload`
* **Headers**: `X-Filename: <encodeURIComponent(filename)>`
* **Body**: Raw binary stream (`application/octet-stream`).
* **Behavior**: Streams chunks directly to disk with atomic temporary file swap. Extracts 16kHz audio waveform and generates Apple Silicon proxy.
* **Response**: `200 OK`
  ```json
  {
    "success": true,
    "project_id": "proj_111sub_1789910026802",
    "filename": "camera_master.mp4",
    "duration_seconds": 88.75,
    "has_audio": true,
    "proxy_url": "/api/media/proj_111sub_1789910026802/proxy"
  }
  ```

### 2.2 Zero-Click Auto Production
* **Endpoint**: `POST /api/media/{project_id}/auto-produce`
* **Behavior**: Runs Whisper speech recognition, Twelve Labs Pegasus 1.5 reasoning, Gemini 2.5 Flash stock reranking, duration clamping ($\le 1.0$s), and places clips onto tracks V1–V5.
* **Response**: `200 OK`
  ```json
  {
    "success": true,
    "cues_count": 8,
    "captions_count": 43,
    "already_produced": false,
    "message": "Auto-production completed successfully"
  }
  ```

### 2.3 Stream Source Video
* **Endpoint**: `GET /api/media/{project_id}/source-video`
* **Headers Supported**: `Range: bytes=start-end`
* **Response**: `200 OK` or `206 Partial Content` with `Accept-Ranges: bytes`.

### 2.4 Multi-Provider Stock Media Search
* **Endpoint**: `GET /api/media/search`
* **Query Parameters**:
  * `query`: Search keywords (e.g. `medical doctor stethoscope`)
  * `type`: `'all' | 'image' | 'video'`
  * `provider`: `'all' | 'pexels' | 'pixabay' | 'wikimedia'`
  * `project_id`: Optional project context for downloading
* **Response**: `200 OK`
  ```json
  {
    "query": "medical doctor stethoscope",
    "results": [
      {
        "id": "px_12345",
        "provider": "pexels",
        "type": "image",
        "title": "Doctor checking patient chart",
        "url": "https://images.pexels.com/...",
        "thumbnail_url": "https://images.pexels.com/..._thumb.jpg",
        "width": 1920,
        "height": 1080
      }
    ]
  }
  ```

### 2.5 Burn-In MP4 Video Render
* **Endpoint**: `POST /api/media/render`
* **Payload**:
  ```json
  {
    "project_id": "proj_111sub_1789910026802",
    "burn_subtitles": true,
    "quality": "high",
    "resolution": "1080x1920"
  }
  ```
* **Response**: `200 OK` `{"job_id": "rnd_98712", "status": "rendering"}`

---

## 3. Twelve Labs Multimodal API (`/api/media/twelve-labs`)

### 3.1 Get Live Credit Quota
* **Endpoint**: `GET /api/media/twelve-labs/credits`
* **Response**: `200 OK`
  ```json
  {
    "has_api_key": true,
    "total_credit_minutes": 600.0,
    "consumed_minutes": 24.2,
    "consumed_seconds": 1451.5,
    "remaining_minutes": 575.8,
    "one_minute_videos_left": 575,
    "percent_used": 4.0,
    "expiry_date": "2026-12-20",
    "days_remaining": 89,
    "is_expired": false
  }
  ```

### 3.2 Save Twelve Labs API Key
* **Endpoint**: `POST /api/media/twelve-labs/set-key`
* **Payload**: `{"api_key": "tlk_..."}`
* **Response**: `200 OK` `{"success": true, "message": "API Key verified and saved"}`

### 3.3 Trigger Twelve Labs Video Analysis
* **Endpoint**: `POST /api/media/{project_id}/twelve-labs/analyze`
* **Behavior**: Uploads video via direct `POST /assets`, indexes into `Resolve-Companion-Index`, and performs non-streaming Pegasus 1.5 analysis.
* **Response**: `200 OK`
  ```json
  {
    "success": true,
    "task_id": "6ab27c5dbdedca43a782f41e",
    "asset_id": "6ab27c1f06875b074c80d0d3",
    "status": "ready",
    "credits": { ... }
  }
  ```

### 3.4 Poll Asset / Index Status
* **Endpoint**: `GET /api/media/twelve-labs/task/{task_id}`
* **Response**: `200 OK`
  ```json
  {
    "success": true,
    "status": "ready",
    "video_id": "6ab27c1f06875b074c80d0d3",
    "process": { ... }
  }
  ```

---

## 4. Editorial Feedback & Training API (`/api/feedback`)

### 4.1 Append Review Decision
* **Endpoint**: `POST /api/feedback/decisions`
* **Payload**:
  ```json
  {
    "project_id": "proj_111sub",
    "decision": "keep",
    "start_sec": 14.5,
    "end_sec": 15.5,
    "original_graphic_type": "article_reconstruction",
    "original_search_query": "NIH study on microplastics in human blood",
    "strength": 0.92,
    "reasoning": "Speaker directly references the landmark trial.",
    "transcript_excerpt": "the clinical trial by the NIH proved this",
    "modified_graphic_type": null,
    "modified_search_query": null,
    "editor_notes": "Spot on visual match"
  }
  ```
* **Response**: `200 OK` `{"success": true, "decision_id": "fbc_7b08e562..."}`

### 4.2 Get Filtered Decisions
* **Endpoint**: `GET /api/feedback/decisions`
* **Query Parameters**:
  * `project_id`: Optional project filter
  * `decision`: `'keep' | 'cut' | 'swap'`
  * `graphic_type`: Optional template type
  * `limit`: Integer (default `100`)
* **Response**: `200 OK` `[ { ...decision object... } ]`

### 4.3 Get Aggregate Feedback Statistics
* **Endpoint**: `GET /api/feedback/stats`
* **Response**: `200 OK`
  ```json
  {
    "total_decisions": 124,
    "kept": 71,
    "cut": 31,
    "swapped": 22,
    "keep_rate": 57.3,
    "cut_rate": 25.0,
    "swap_rate": 17.7,
    "summary_text": "124 decisions → 71 kept | 31 cut | 22 modified"
  }
  ```

### 4.4 Get Few-Shot Training Export
* **Endpoint**: `GET /api/feedback/few-shot-export`
* **Response**: `200 OK`
  ```json
  {
    "total_samples": 10,
    "kept_samples": 6,
    "cut_samples": 4,
    "markdown_prompt": "# FEW-SHOT EDITORIAL EXAMPLES\n\n## POSITIVE (KEEP) EXAMPLES: ... \n\n## NEGATIVE (CUT) EXAMPLES: ..."
  }
  ```

---

## 5. Subtitles & Visual Reasoning API (`/api/subtitles`)

### 5.1 Get Captions
* **Endpoint**: `GET /api/subtitles/{project_id}`
* **Response**: `200 OK`
  ```json
  [
    {
      "id": "cap_0",
      "start": 0.0,
      "end": 0.5,
      "text": "Samay Raina,",
      "words": [
        {"word": "Samay", "start": 0.0, "end": 0.25},
        {"word": "Raina,", "start": 0.25, "end": 0.5}
      ]
    }
  ]
  ```

### 5.2 Get Visual Reasoning Log
* **Endpoint**: `GET /api/subtitles/{project_id}/reasoning-log`
* **Response**: `200 OK`
  ```json
  [
    {
      "cue_id": "cue_1",
      "start_sec": 8.0,
      "end_sec": 9.0,
      "graphic_type": "split_screen_vertical",
      "title": "Rising Cancer Rates in Youth",
      "strength": 0.85,
      "search_query": "Medical graph showing declining age of diagnosis",
      "reasoning": "Speaker emphasizes rising cancer rates in younger demographics; split screen provides visual proof.",
      "rerank_justification": "Candidate #2 shows clinical demographic chart."
    }
  ]
  ```

---

## 6. DaVinci Resolve Integration API (`/api/davinci`)

### 6.1 Sync Timeline to DaVinci Resolve
* **Endpoint**: `POST /api/davinci/{project_id}/sync`
* **Payload**: `{"timeline_name": "AI Edit Master", "target_framerate": 24}`
* **Response**: `200 OK` `{"success": true, "resolve_timeline_id": "tl_102"}`

### 6.2 Export FCPXML Timeline
* **Endpoint**: `GET /api/davinci/{project_id}/fcpxml`
* **Response**: `200 OK` (`application/xml`) — Fully compliant Apple Final Cut Pro XML (FCPXML 1.8) mapping all visual layers and audio.
