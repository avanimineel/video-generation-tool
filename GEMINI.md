# DaVinci Resolve Companion — Workspace Rules & Guidelines

Welcome to the **DaVinci Resolve AI Editing Companion** project directory.

## Core Operational Directives

1. **Light Theme Design System**:
   * Maintain the clean, modern light-theme UI tokens across all React components (`bg-white`, `border-neutral-200`, `text-neutral-900`, neutral hover states).
   * Ensure sidebar columns retain their collapsible behavior and toggle state.

2. **Media Search Priority Order**:
   * Media provider orchestration strictly follows:
     1. **Pexels**
     2. **Pixabay**
     3. **Wikimedia Commons** (only as a fallback when commercial stock sources return 0 items)
   * Never re-order Wikimedia ahead of Pexels or Pixabay.

3. **Subtitles & Acoustic Syllable Sync**:
   * All caption segments must be acoustically aligned with audio bursts.
   * Hindi-to-English translations must be coherent, context-aware, and natural. Avoid fragmented chops or literal non-idiomatic translations.
   * Karaoke word highlights require per-word timing arrays in `captions.json`.

4. **Resilient AI Visuals & Quota Handling**:
   * Cloud image diffusion models (`gemini-3.1-flash-image`) may encounter `429 RESOURCE_EXHAUSTED` on Free Tier keys.
   * In `google_ai.py`, always maintain the procedural graphic generator fallback (`create_procedural_graphic`) using PIL TrueType fonts. Never allow unhandled exceptions or 500 error banners to surface to the user.

5. **Sandbox & Network Rules**:
   * When launching backend servers, unit tests, or scripts that make external network requests (Pexels, Pixabay, Google AI API, or DNS lookups), always run with `BypassSandbox: true` to avoid macOS `[Errno 8] nodename nor servname provided, or not known`.

6. **FFmpeg & Export Standards**:
   * Use hardware-accelerated Apple VideoToolbox (`h264_videotoolbox`) whenever available on macOS.
   * All visible timeline elements (subtitles, 50/50 vertical split B-roll, AI graphics, dynamic cards) must be properly composited into the exported MP4.

## Quick Commands

* **Start both Backend and Frontend**: `./start_companion.sh`
* **Start Backend**: `cd backend && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload`
* **Start Frontend**: `cd frontend && npm run dev`
* **Build Frontend**: `cd frontend && npm run build`
* **Test Media Search**: `python3 backend/tests/test_media_acquisition.py`
