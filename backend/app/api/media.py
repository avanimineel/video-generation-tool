from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import time
from app.core.config import settings, reload_env, save_env_key as _save_env_key
from app.core.models import ProjectState, ProjectSettings
from app.services.project_manager import project_manager
from app.services.proxy_generator import proxy_generator
from app.services.burnin_renderer import burnin_renderer
from app.services.media_search_service import media_search_service
from app.services.asset_downloader import asset_downloader
from app.services.media_providers.google_ai import GoogleAIProvider, google_ai_provider
from app.services.auto_production_service import auto_production_service

router = APIRouter(prefix="/api/media", tags=["media"])

class ImportMediaRequest(BaseModel):
    project_id: str
    video_path: str

class AutoMatchRequest(BaseModel):
    caption_text: str
    exclude_urls: Optional[List[str]] = None

class DownloadAssetRequest(BaseModel):
    id: Optional[str] = None
    provider: Optional[str] = "web"
    url: Optional[str] = None
    download_url: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = "image"
    title: Optional[str] = ""
    source_credit: Optional[str] = ""
    author: Optional[str] = ""
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    duration: Optional[float] = 0.0

def save_env_key(key, value):
    try:
        _save_env_key(key, value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except (OSError, RuntimeError):
        raise HTTPException(status_code=503, detail='Provider key could not be saved. Existing credentials were preserved; check backend storage permissions.') from None

class GenerateAIImageRequest(BaseModel):
    project_id: str
    prompt: str
    aspect_ratio: str = "9:16"
    gemini_api_key: Optional[str] = None

class GenerateAIVideoRequest(BaseModel):
    project_id: str
    prompt: str
    aspect_ratio: str = "9:16"
    duration: int = 5
    camera_motion: str = "push_in"
    gemini_api_key: Optional[str] = None
    overlay_text: Optional[str] = ""

class ProviderKeysRequest(BaseModel):
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

# 1. Provider Status & Configuration
@router.get("/providers/configuration")
async def get_provider_configuration():
    from app.core.config import get_provider_key
    return {'gemini_saved': bool(get_provider_key('GEMINI_API_KEY'))}

@router.get("/providers/status")
async def get_providers_status():
    reload_env()
    return media_search_service.get_providers_status()

@router.post("/providers/keys")
async def save_provider_keys(req: ProviderKeysRequest):
    if req.pexels_api_key is not None:
        save_env_key("PEXELS_API_KEY", req.pexels_api_key.strip())
    if req.pixabay_api_key is not None:
        save_env_key("PIXABAY_API_KEY", req.pixabay_api_key.strip())
    if req.gemini_api_key is not None:
        save_env_key("GEMINI_API_KEY", req.gemini_api_key.strip())
    reload_env()
    return {
        "success": True,
        "status": media_search_service.get_providers_status()
    }

# 2. Multi-Provider Media Search
@router.get("/search")
async def search_media_endpoint(
    query: str = Query(..., description="Topic search term (e.g. 'doctor hospital', 'cancer', 'rocket')"),
    type: str = Query("image", description="Media type: image, video, or all"),
    media_type: Optional[str] = Query(None, description="Alias for type parameter"),
    provider: str = Query("all", description="Provider: all, pexels, pixabay, wikimedia"),
    orientation: Optional[str] = Query(None, description="Orientation: portrait, landscape, square"),
    limit: int = Query(12, description="Number of results")
):
    reload_env()
    effective_type = (media_type or type or "image").lower()
    try:
        results = media_search_service.search_media(
            query=query,
            media_type=effective_type,
            provider=provider,
            orientation=orientation,
            limit=limit
        )
        diag = getattr(media_search_service, "last_search_diagnostics", {})
        return {
            "query": query,
            "type": effective_type,
            "provider": provider,
            "provider_used": diag.get("provider_used"),
            "waterfall_step": diag.get("waterfall_step"),
            "diagnostics": {
                "search": diag,
                "pexels": getattr(media_search_service.pexels, "last_diagnostic", {}),
                "pixabay": getattr(media_search_service.pixabay, "last_diagnostic", {})
            },
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto-match")
async def auto_match_endpoint(req: AutoMatchRequest):
    try:
        match_data = media_search_service.auto_match_for_caption(req.caption_text, exclude_urls=req.exclude_urls)
        return match_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Local Asset Downloader Endpoint (Deduplication + Metadata)
@router.post("/{project_id}/download-asset")
async def download_asset_endpoint(project_id: str, req: DownloadAssetRequest):
    try:
        asset_info = req.model_dump()
        result = asset_downloader.download_asset(project_id, asset_info)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Asset download error: {str(e)}")

# 4. Serve Downloaded Media Files with HTTP Range Support
@router.api_route("/{project_id}/asset/downloaded/{filename}", methods=["GET", "HEAD"])
async def get_downloaded_asset_file(project_id: str, filename: str):
    pdir = settings.projects_dir / project_id / "media" / "downloaded"
    target = pdir / filename
    if target.exists():
        ext = filename.lower().split('.')[-1]
        mime_map = {
            "wav": "audio/wav",
            "svg": "image/svg+xml",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "webm": "video/webm",
            "m4v": "video/mp4",
        }
        media_type = mime_map.get(ext, "application/octet-stream")
        return FileResponse(
            str(target),
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    raise HTTPException(status_code=404, detail=f"Downloaded asset '{filename}' not found")

# 5. Dedicated Google AI Image Generation Endpoint
@router.post("/generate-ai-image")
async def generate_ai_image_endpoint(req: GenerateAIImageRequest):
    if req.gemini_api_key and req.gemini_api_key.strip():
        save_env_key("GEMINI_API_KEY", req.gemini_api_key.strip())
        reload_env()
    provider = GoogleAIProvider(api_key=req.gemini_api_key)
    if not provider.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Google Gemini API key is not configured. Please enter your key in Media Settings or set GEMINI_API_KEY in .env"
        )

    out_dir = asset_downloader.get_download_dir(req.project_id)
    timestamp = int(time.time() * 1000)
    out_file = out_dir / f"google_ai_img_{timestamp}.jpg"

    try:
        res = provider.generate_image(
            prompt=req.prompt,
            aspect_ratio=req.aspect_ratio,
            output_path=out_file
        )
        media_url = f"/api/media/{req.project_id}/asset/downloaded/{out_file.name}"
        return {
            "success": True,
            "filename": out_file.name,
            "local_path": str(out_file),
            "media_url": media_url,
            "full_url": f"http://localhost:8002{media_url}",
            "media_type": "image",
            "title": req.prompt[:40].title(),
            "source_credit": res.get("engine", "Generated with Google AI"),
            "model": res.get("model", "imagen-3.0"),
            "aspect_ratio": res.get("aspect_ratio", "9:16"),
            "duration": 4.0,
            "engine": res.get("engine", "google_ai_image"),
            "note": res.get("note", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual Generation Error: {str(e)}")

# 6. Dedicated Google AI Video Generation Endpoint
@router.post("/generate-ai-video")
async def generate_ai_video_endpoint(req: GenerateAIVideoRequest):
    if req.gemini_api_key and req.gemini_api_key.strip():
        save_env_key("GEMINI_API_KEY", req.gemini_api_key.strip())
        reload_env()
    provider = GoogleAIProvider(api_key=req.gemini_api_key)
    if not provider.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Google Gemini API key is not configured. Please enter your key in Media Settings or set GEMINI_API_KEY in .env"
        )

    out_dir = asset_downloader.get_download_dir(req.project_id)
    timestamp = int(time.time() * 1000)
    out_file = out_dir / f"google_ai_vid_{timestamp}.mp4"

    try:
        res = provider.generate_video(
            prompt=req.prompt,
            aspect_ratio=req.aspect_ratio,
            duration=req.duration,
            output_path=out_file,
            camera_motion=req.camera_motion
        )
        media_url = f"/api/media/{req.project_id}/asset/downloaded/{out_file.name}"
        return {
            "success": True,
            "filename": out_file.name,
            "local_path": str(out_file),
            "media_url": media_url,
            "full_url": f"http://localhost:8002{media_url}",
            "video_url": media_url,
            "media_type": "video",
            "title": req.prompt[:40].title(),
            "source_credit": "Generated with Google AI Video",
            "model": res.get("model", "google_ai"),
            "engine": res.get("engine", "google_ai_video"),
            "duration": res.get("duration", req.duration),
            "note": res.get("note", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google AI Video Generation Error: {str(e)}")

# 7. Backward-Compatible Omni Motion Generate
class OmniMotionGenerateRequest(BaseModel):
    project_id: str
    current_time: float = 0.0
    mode: str = "text_to_video"
    prompt: Optional[str] = ""
    camera_motion: Optional[str] = "push_in"
    motion_intensity: Optional[str] = "cinematic"
    base64_frame: Optional[str] = None
    overlay_text: Optional[str] = ""
    motion_instructions: str
    gemini_api_key: Optional[str] = None
    duration: int = 5
    aspect_ratio: str = "9:16"
    resolution: str = "720p"

@router.post("/omni-motion-generate")
async def omni_motion_generate(req: OmniMotionGenerateRequest):
    if req.gemini_api_key and req.gemini_api_key.strip():
        save_env_key("GEMINI_API_KEY", req.gemini_api_key.strip())
    reload_env()
    provider = GoogleAIProvider(api_key=req.gemini_api_key)
    out_dir = asset_downloader.get_download_dir(req.project_id)
    timestamp = int(time.time() * 1000)
    out_video = out_dir / f"omni_{timestamp}.mp4"

    raw_query = req.prompt or req.motion_instructions or req.overlay_text or "documentary visual"
    clean_query = re.sub(r'^(make\s+a\s+video\s+of|generate\s+a\s+video\s+of|add\s+a\s+video\s+of|video\s+of|footage\s+of|clip\s+of|an?\s+)\s+', '', raw_query, flags=re.IGNORECASE).strip()
    duration_s = max(3, min(10, req.duration or 5))

    if provider.is_configured():
        try:
            res = provider.generate_video(
                prompt=clean_query,
                aspect_ratio=req.aspect_ratio,
                duration=duration_s,
                output_path=out_video,
                camera_motion=req.camera_motion or "push_in"
            )
            media_url = f"/api/media/{req.project_id}/asset/downloaded/{out_video.name}"
            return {
                "success": True,
                "video_url": media_url,
                "media_url": media_url,
                "media_type": "video",
                "overlay_text": req.overlay_text or clean_query.title(),
                "duration": duration_s,
                "engine": res.get("engine", "google_ai_video"),
                "note": res.get("note", "")
            }
        except Exception as e:
            # Report the exact technical error instead of hiding it!
            raise HTTPException(
                status_code=500,
                detail=f"Google AI Video Generation failed: {str(e)}"
            )

    raise HTTPException(
        status_code=400,
        detail="Google Gemini API key is not configured. Please provide a key in settings or .env"
    )


# 2. Media Import Endpoint
@router.post("/import")
async def import_media(req: ImportMediaRequest):
    state = project_manager.get_project(req.project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    source_path = req.video_path
    if not os.path.exists(source_path):
        if not source_path.startswith('/'):
            source_path = str(settings.projects_dir / req.project_id / source_path)

    duration, waveform = proxy_generator.extract_waveform_and_duration(source_path)
    state.source_media_path = source_path
    state.duration_seconds = max(15.0, duration)
    state.waveform_data = waveform

    pdir = settings.projects_dir / req.project_id
    proxy_path = str(pdir / "proxies" / "proxy_720p.mp4")
    if os.path.exists(source_path):
        res = proxy_generator.generate_proxy(source_path, proxy_path)
        if res.get('success'):
            state.proxy_media_path = proxy_path
    
    project_manager.save_project(state)
    return {
        'success': True,
        'duration_seconds': state.duration_seconds,
        'proxy_media_path': state.proxy_media_path,
        'waveform_length': len(waveform)
    }

# 3. Direct Streaming Video Upload Endpoint
@router.post("/{project_id}/upload")
async def upload_video_stream(project_id: str, request: Request):
    from app.services.auto_jobs import active
    if active(project_id):raise HTTPException(status_code=409,detail='Automatic editing is still running for this project.')
    from urllib.parse import unquote
    raw_filename = request.headers.get("x-filename", "uploaded_video.mp4")
    try:
        filename = os.path.basename(unquote(raw_filename)) or "uploaded_video.mp4"
    except Exception:
        filename = os.path.basename(raw_filename) or "uploaded_video.mp4"

    clean_title = os.path.splitext(filename)[0] or project_id

    state = project_manager.get_project(project_id)
    if not state:
        now_str = datetime.now().isoformat()
        state = ProjectState(
            id=project_id,
            name=clean_title,
            created_at=now_str,
            updated_at=now_str,
            duration_seconds=15.0,
            settings=ProjectSettings(aspect_ratio="9:16"),
            captions=[],
            graphics=[],
            detected_language="en"
        )

    pdir = settings.projects_dir / state.id
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "proxies").mkdir(parents=True, exist_ok=True)
    (pdir / "thumbnails").mkdir(parents=True, exist_ok=True)
    (pdir / "exports").mkdir(parents=True, exist_ok=True)

    from uuid import uuid4
    dest_path = pdir / (uuid4().hex[:8]+"_"+filename)
    temp_path = pdir / f".upload_{filename}.tmp"
    free_bytes = shutil.disk_usage(pdir).free

    total_bytes = 0
    try:
        with open(temp_path, "wb") as f:
            async for chunk in request.stream():
                total_bytes += len(chunk)
                if total_bytes > (free_bytes - 100 * 1024 * 1024):
                    if temp_path.exists():
                        temp_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=507,
                        detail=f"Insufficient disk space to save uploaded video ({total_bytes // (1024*1024)}MB received, {free_bytes // (1024*1024)}MB free)."
                    )
                f.write(chunk)
        if temp_path.exists():
            if dest_path.exists():
                dest_path.unlink(missing_ok=True)
            temp_path.replace(dest_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if isinstance(e, HTTPException):
            raise e
        print(f"[Upload Error] Stream write failure: {e}")
        raise HTTPException(status_code=400, detail=f"Upload stream interrupted: {str(e)}")

    from app.services.editorial_planner import write_json
    from uuid import uuid4
    write_json(pdir/'recovery'/('before-upload-'+uuid4().hex+'.json'),state.model_dump())
    state.captions=[]
    state.graphics=[]
    state.ai_ingestion={}
    duration, waveform = await run_in_threadpool(proxy_generator.extract_waveform_and_duration,str(dest_path))
    state.name = clean_title
    state.source_media_path = str(dest_path)
    state.duration_seconds = max(1.0, duration) if duration > 0 else 15.0
    state.waveform_data = waveform
    # Save project state immediately so transcription can find the media file right away!
    project_manager.save_project(state)

    proxy_path = str(pdir / "proxies" / "proxy_720p.mp4")
    res = await run_in_threadpool(proxy_generator.generate_proxy,str(dest_path),proxy_path)
    if res.get('success'):
        state.proxy_media_path = proxy_path
    else:
        state.proxy_media_path = str(dest_path)

    project_manager.save_project(state)
    from app.services.auto_jobs import start
    start(state.id,force=True)
    return {
        "success": True,
        "id": state.id,
        "project_id": state.id,
        "name": state.name,
        "filename": filename,
        "duration_seconds": state.duration_seconds,
        "proxy_path": state.proxy_media_path,
        "waveform": state.waveform_data,
        "project": state.model_dump()
    }

# 3B. Zero-Click Ingestion & Auto-Production Endpoint
class AutoProduceRequest(BaseModel):
    force: bool = False
    model_size: str = "small"

@router.post("/{project_id}/auto-produce")
def run_auto_produce_endpoint(project_id: str, req: AutoProduceRequest = AutoProduceRequest()):
    from app.services.auto_jobs import start
    try:return {'success':True,'job':start(project_id,req.force,req.model_size)}
    except ValueError as exc:raise HTTPException(status_code=404,detail=str(exc))

@router.get("/{project_id}/auto-produce/status")
def get_auto_produce_status_endpoint(project_id: str):
    from app.services.auto_jobs import status
    return status(project_id)

@router.get("/{project_id}/editorial-report")
def editorial_report(project_id: str):
    import json
    if not project_manager.get_project(project_id):raise HTTPException(status_code=404,detail='Project not found')
    folder=settings.projects_dir/project_id/'editorial'
    path=folder/'latest.json'
    if not path.exists():
        from app.services.editorial_planner import configured_key
        missing=[k for k in ('GEMINI_API_KEY','TWELVE_LABS_API_KEY') if not configured_key(k)]
        return {'status':'not_run','decisions':[],'errors':[k+' is missing or a test placeholder. Configure a working key before planning.' for k in missing]}
    report=json.loads(path.read_text())
    run_id=report.get('run_id','')
    if re.fullmatch(r'[0-9T]+-[a-f0-9]+',run_id):
        report['stages']={f.stem:json.loads(f.read_text()) for f in sorted((folder/run_id).glob('0*.json'))}
    return report

@router.get("/{project_id}/visual-reasoning-log")
def get_visual_reasoning_log_endpoint(project_id: str):
    import json
    pdir = settings.projects_dir / project_id
    log_file = pdir / "thumbnails" / "visual_reasoning_log.json"
    if log_file.exists():
        try:
            return {"success": True, "reasoning_log": json.loads(log_file.read_text(encoding="utf-8"))}
        except Exception as e:
            print("[get_visual_reasoning_log] Warning reading log file:", e)
    folder = pdir / "editorial"
    path = folder / "latest.json"
    if path.exists():
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            run_id = report.get("run_id", "")
            placement = folder / run_id / "05_placement.json"
            if placement.exists():
                rows = json.loads(placement.read_text(encoding="utf-8"))
                logs = [
                    dict(
                        cue_index=i+1,
                        graphic_id=r.get("graphic_id") or f"editorial_{run_id}_{i}",
                        template_id=r.get("strategy") or "split_screen_vertical",
                        template_name=r.get("asset", {}).get("semantic_target") or r.get("display_text") or r.get("intent"),
                        timestamp_start=r.get("start_sec", 0.0),
                        timestamp_end=r.get("end_sec", 1.0),
                        timestamp_formatted=f"{int(r.get('start_sec', 0.0)//60):02d}:{r.get('start_sec', 0.0)%60:05.2f}",
                        duration_sec=round(r.get("end_sec", 1.0) - r.get("start_sec", 0.0), 2),
                        trigger_term=r.get("anchor_phrase", ""),
                        cue_category=r.get("intent", "General"),
                        timestamp_logic=r.get("timing_method", ""),
                        image_logic=r.get("rationale") or r.get("decision_reason", ""),
                        layout_logic=json.dumps(r.get("realized_composition") or r.get("composition") or {}),
                        pacing_logic=r.get("decision_reason", ""),
                        search_query=r.get("asset", {}).get("retrieval_query", ""),
                        source_provider="",
                        media_url="",
                        media_type="image",
                        strength=r.get("utility", 0.8),
                        reasoning=r.get("rationale", "")
                    )
                    for i, r in enumerate(rows) if r.get("status") in ("inserted", "planned")
                ]
                return {"success": True, "reasoning_log": logs}
        except Exception as e:
            print("[get_visual_reasoning_log] Warning fallback to report:", e)
    return {"success": True, "reasoning_log": []}


# 4. Burn-in Rendering & Export Endpoints
@router.post("/{project_id}/render-burnin")
async def render_burnin(project_id: str, request: Request):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    body = {}
    try:
        if request.headers.get("content-type") == "application/json":
            body = await request.json()
    except Exception:
        body = {}

    # If the client sent their latest in-memory ProjectState, save it immediately before rendering!
    has_custom_state = False
    if "project_state" in body and isinstance(body["project_state"], dict):
        from app.services.auto_jobs import active
        if active(project_id):raise HTTPException(409, 'Wait for automatic editing to finish before exporting.')
        from pydantic import ValidationError
        try:
            updated_state = ProjectState(**body['project_state'])
        except ValidationError as exc:
            raise HTTPException(422, 'Invalid export project state') from exc
        if updated_state.id != project_id:raise HTTPException(400, 'Export project does not match the selected project')
        project_manager.save_project(updated_state)
        state = updated_state
        has_custom_state = True

    subtitles_only = bool(body.get("subtitles_only", False))
    force_rerender = bool(body.get("force_rerender", False)) or has_custom_state

    pdir = settings.projects_dir / project_id
    target_filename = f"{state.name}_subtitled.mp4" if subtitles_only else f"{state.name}_burned.mp4"
    target_path = pdir / "exports" / target_filename

    from app.services.export_cache import fingerprint, cache_matches, remember
    signature=fingerprint(state,subtitles_only)
    if not force_rerender and cache_matches(target_path,signature):
        return {
            "success": True,
            "already_cached": True,
            "download_url": f"/api/media/{project_id}/download-mp4?subtitles_only={str(subtitles_only).lower()}",
            "output_path": str(target_path),
            "file_size": target_path.stat().st_size
        }

    res = await run_in_threadpool(burnin_renderer.render_burned_video, state, subtitles_only=subtitles_only)
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error", "Rendering failed"))

    remember(res["output_path"],signature)
    return {
        "success": True,
        "download_url": f"/api/media/{project_id}/download-mp4?subtitles_only={str(subtitles_only).lower()}",
        "output_path": res.get("output_path"),
        "file_size": res.get("file_size")
    }

@router.get("/{project_id}/render-progress")
async def get_render_progress(project_id: str):
    return burnin_renderer.get_progress(project_id)

@router.api_route("/{project_id}/download-mp4", methods=["GET", "HEAD"])
async def download_burned_mp4(project_id: str, subtitles_only: bool = False):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    pdir = settings.projects_dir / project_id
    target_filename = f"{state.name}_subtitled.mp4" if subtitles_only else f"{state.name}_burned.mp4"
    output_mp4 = pdir / "exports" / target_filename

    from app.services.export_cache import fingerprint, cache_matches, remember
    signature=fingerprint(state,subtitles_only)
    if not cache_matches(output_mp4,signature):
        res = await run_in_threadpool(burnin_renderer.render_burned_video, state, subtitles_only=subtitles_only)
        if not res.get('success'):raise HTTPException(500, detail=res.get('error','Video export failed'))
        output_mp4=Path(res['output_path'])
        remember(output_mp4,signature)

    clean_download_name = f"{state.name}_{'subtitled' if subtitles_only else 'burned'}.mp4"
    return FileResponse(
        str(output_mp4),
        media_type="video/mp4",
        filename=clean_download_name,
        headers={
            "Content-Disposition": f'attachment; filename="{clean_download_name}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS"
        }
    )

@router.api_route("/{project_id}/source-video", methods=["GET", "HEAD"])
async def get_source_video(project_id: str):
    state = project_manager.get_project(project_id)
    if state and state.source_media_path and os.path.exists(state.source_media_path):
        return FileResponse(
            state.source_media_path,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    pdir = settings.projects_dir / project_id
    for mp4 in pdir.glob("*.mp4"):
        if mp4.is_file():
            return FileResponse(
                str(mp4),
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "*"
                }
            )
    raise HTTPException(status_code=404, detail="Source video not found")

@router.get("/{project_id}/proxy")
async def get_proxy_video(project_id: str):
    pdir = settings.projects_dir / project_id
    proxy_file = pdir / "proxies" / "proxy_720p.mp4"
    if proxy_file.exists():
        return FileResponse(str(proxy_file), media_type="video/mp4", headers={"Cache-Control":"no-store"})
    
    state = project_manager.get_project(project_id)
    if state and state.source_media_path and os.path.exists(state.source_media_path):
        return FileResponse(state.source_media_path, media_type="video/mp4")
    
    raise HTTPException(status_code=404, detail="No video proxy available")

@router.get("/{project_id}/waveform")
async def get_waveform(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return {'waveform': state.waveform_data, 'duration': state.duration_seconds}

@router.api_route("/{project_id}/omni-video/{filename}", methods=["GET", "HEAD"])
async def get_omni_video(project_id: str, filename: str):
    pdir = settings.projects_dir / project_id
    target = pdir / filename
    if target.exists():
        return FileResponse(
            str(target),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    raise HTTPException(status_code=404, detail="Omni video not found")

# 5. Custom Asset Upload & Serving (B-roll, Documents, Overlays)
@router.post("/{project_id}/upload-asset")
async def upload_custom_asset(project_id: str, request: Request):
    from urllib.parse import unquote
    raw_filename = request.headers.get("x-filename", "custom_asset.png")
    filename = unquote(raw_filename)
    safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(filename)) or "custom_asset.png"
    pdir = settings.projects_dir / project_id / "assets"
    pdir.mkdir(parents=True, exist_ok=True)

    dest = pdir / safe_filename
    content = await request.body()
    with open(dest, "wb") as f:
        f.write(content)

    ext = safe_filename.lower().split('.')[-1]
    is_video = ext in ['mp4', 'mov', 'webm', 'm4v']
    media_url = f"http://localhost:8002/api/media/{project_id}/asset/{safe_filename}"

    return {
        "success": True,
        "filename": safe_filename,
        "media_url": media_url,
        "media_type": "video" if is_video else "image",
        "title": os.path.splitext(safe_filename)[0].replace('_', ' ').title(),
        "source_credit": "Source: User Custom Upload"
    }

@router.api_route("/{project_id}/asset/{filename}", methods=["GET", "HEAD"])
async def get_custom_asset(project_id: str, filename: str):
    pdir = settings.projects_dir / project_id / "assets"
    target = pdir / filename
    if target.exists():
        ext = filename.lower().split('.')[-1]
        mime_map = {
            "wav": "audio/wav",
            "svg": "image/svg+xml",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "webp": "image/webp",
            "gif": "image/gif",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
            "webm": "video/webm",
            "m4v": "video/mp4",
        }
        media_type = mime_map.get(ext, "application/octet-stream")
        return FileResponse(
            str(target),
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    raise HTTPException(status_code=404, detail="Asset not found")

# 6. Twelve Labs Semantic Video Understanding & Live Credit Meter
@router.get("/twelve-labs/credits")
async def get_twelve_labs_credits():
    from app.services.twelve_labs_service import twelve_labs_service
    return twelve_labs_service.get_credits_status()

@router.post("/twelve-labs/set-key")
async def set_twelve_labs_key(request: Request):
    data = await request.json()
    key = data.get("api_key", "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Missing api_key")
    save_env_key("TWELVE_LABS_API_KEY", key)
    from app.services.twelve_labs_service import twelve_labs_service
    return twelve_labs_service.get_credits_status()

@router.post("/{project_id}/twelve-labs/analyze")
async def analyze_with_twelve_labs(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    pdir = settings.projects_dir / project_id
    video_path = state.source_media_path
    if not video_path or not os.path.exists(video_path):
        for cand in ["sub.mov", "sub.mp4", "uploaded_video.mp4"]:
            if (pdir / cand).exists():
                video_path = str(pdir / cand)
                break

    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="Source video file not found for Twelve Labs analysis")

    from app.services.twelve_labs_service import twelve_labs_service
    duration = state.duration_seconds or 60.0
    res = twelve_labs_service.analyze_video(video_path, video_duration=duration)
    return res

@router.get("/twelve-labs/tasks/{task_id}")
async def get_twelve_labs_task_status(task_id: str):
    from app.services.twelve_labs_service import twelve_labs_service
    return twelve_labs_service.get_task_status(task_id)


@router.post('/{project_id}/understanding-review')
def start_understanding_review(project_id: str):
    from app.services.understanding_jobs import start
    if not project_manager.get_project(project_id):raise HTTPException(404,'Project not found')
    try:return start(project_id)
    except ValueError as e:raise HTTPException(409,str(e))

@router.get('/{project_id}/understanding-review')
def get_understanding_review(project_id: str):
    from app.services.understanding_jobs import status
    if not project_manager.get_project(project_id):raise HTTPException(404,'Project not found')
    return status(project_id)
