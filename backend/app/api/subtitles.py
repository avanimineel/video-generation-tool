from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.core.models import CaptionItem, CaptionStyle, ProjectState, ProjectSettings
from app.services.project_manager import project_manager
from app.services.transcription_service import transcription_service
from app.services.translation_service import translation_service

router = APIRouter(prefix="/api/subtitles", tags=["subtitles"])

import os
from datetime import datetime
from app.core.config import settings

def get_or_create_project(project_id: str) -> ProjectState:
    state = project_manager.get_project(project_id)
    if state:
        return state

    now_str = datetime.now().isoformat()
    clean_name = project_id.replace("proj_", "").split("_")[0] or "Project"
    state = ProjectState(
        id=project_id,
        name=clean_name,
        created_at=now_str,
        updated_at=now_str,
        duration_seconds=15.0,
        settings=ProjectSettings(aspect_ratio="9:16"),
        captions=[],
        graphics=[],
        detected_language="en"
    )
    pdir = settings.projects_dir / project_id
    pdir.mkdir(parents=True, exist_ok=True)
    project_manager.save_project(state)
    return state

class TranscribeRequest(BaseModel):
    project_id: str
    raw_text: Optional[str] = None
    words_per_caption: int = 4
    task: Optional[str] = "transcribe"
    gemini_api_key: Optional[str] = None
    model_size: Optional[str] = "base"

class TranslateRequest(BaseModel):
    project_id: str

class SplitCaptionRequest(BaseModel):
    project_id: str
    caption_id: str
    split_time: float

class MergeCaptionsRequest(BaseModel):
    project_id: str
    caption_id_1: str
    caption_id_2: str

@router.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    state = get_or_create_project(req.project_id)

    # Locate audio or video media file
    pdir = settings.projects_dir / state.id
    media_file = None
    if state.source_media_path and os.path.exists(state.source_media_path):
        media_file = state.source_media_path
    elif state.source_media_path and (pdir / state.source_media_path).exists():
        media_file = str(pdir / state.source_media_path)
    elif state.source_media_path and (pdir / os.path.basename(state.source_media_path)).exists():
        media_file = str(pdir / os.path.basename(state.source_media_path))
    elif (pdir / "sub.mov").exists():
        media_file = str(pdir / "sub.mov")
    elif (pdir / "audio_16k.mp3").exists():
        media_file = str(pdir / "audio_16k.mp3")
    elif (pdir / "audio_extract.mp3").exists():
        media_file = str(pdir / "audio_extract.mp3")

    # Search for any video or audio file in project dir
    if not media_file or not os.path.exists(media_file):
        for pattern in ["*.mov", "*.mp4", "*.m4v", "*.webm", "*.mkv", "*.mp3", "*.wav"]:
            found = list(pdir.glob(pattern))
            if found:
                media_file = str(found[0])
                state.source_media_path = media_file
                break

    # If still not found and this is the demo/podcast project, search in sibling projects for sub.mov
    if not media_file or not os.path.exists(media_file):
        for sibling in settings.projects_dir.iterdir():
            if sibling.is_dir() and sibling.name != state.id:
                cand = sibling / "sub.mov"
                if cand.exists():
                    # Copy to current project so it's locally available
                    import shutil
                    local_dest = pdir / "sub.mov"
                    shutil.copyfile(str(cand), str(local_dest))
                    media_file = str(local_dest)
                    state.source_media_path = media_file
                    break

    if req.raw_text and req.raw_text.strip():
        lang, captions = transcription_service.transcribe_audio_or_text(
            req.raw_text.strip(),
            start_offset=0.0,
            words_per_caption=req.words_per_caption
        )
    elif media_file and os.path.exists(media_file):
        # 1. Local Faster-Whisper (Zero keys, Apple Silicon accelerated, offline)
        task_mode = req.task or "translate"
        try:
            lang, captions = transcription_service.transcribe_with_whisper(
                media_file,
                words_per_caption=req.words_per_caption,
                task=task_mode,
                model_size=req.model_size or "base"
            )
        except Exception as e:
            print("Local whisper failed, attempting fallback:", e)
            lang, captions = 'en', []

        # Fallback to Gemini if requested and whisper produced no captions
        if not captions and (req.gemini_api_key or os.getenv("GEMINI_API_KEY")):
            key = req.gemini_api_key or os.getenv("GEMINI_API_KEY")
            audio_mp3 = pdir / "audio_extract.mp3"
            import subprocess
            subprocess.run([settings.ffmpeg_bin, "-y", "-i", media_file, "-vn", "-acodec", "libmp3lame", "-q:a", "4", str(audio_mp3)], capture_output=True)
            if audio_mp3.exists():
                lang, captions = transcription_service.transcribe_with_gemini(str(audio_mp3), key, req.words_per_caption)

        if not captions:
            lang, captions = transcription_service.generate_timeline_placeholders(state.duration_seconds or 15.0)
    else:
        lang, captions = transcription_service.generate_timeline_placeholders(state.duration_seconds or 15.0)

    state.detected_language = lang
    state.captions = captions
    if captions:
        state.duration_seconds = max(state.duration_seconds, captions[-1].end + 0.5)

    project_manager.save_project(state)
    return {
        'detected_language': lang,
        'caption_count': len(captions),
        'captions': [c.model_dump() for c in captions]
    }

@router.post("/translate")
async def translate(req: TranslateRequest):
    state = get_or_create_project(req.project_id)

    from starlette.concurrency import run_in_threadpool
    from app.services.editorial_planner import safe_error
    try:
        updated_captions = await run_in_threadpool(
            translation_service.translate_captions_list, state.captions,
            checkpoint_dir=settings.projects_dir/state.id/'transcription'/'translation_checkpoints')
    except Exception as exc:
        raise HTTPException(503, detail=safe_error(exc))
    state.captions = updated_captions
    project_manager.save_project(state)
    return {'caption_count':len(updated_captions),'captions':[c.model_dump() for c in updated_captions]}

@router.post("/split")
async def split_caption(req: SplitCaptionRequest):
    state = project_manager.get_project(req.project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    target_idx = None
    for idx, c in enumerate(state.captions):
        if c.id == req.caption_id:
            target_idx = idx
            break

    if target_idx is None:
        raise HTTPException(status_code=404, detail="Caption not found")

    cap = state.captions[target_idx]
    if not (cap.start < req.split_time < cap.end):
        raise HTTPException(status_code=400, detail="Split time must be between caption start and end")

    # Split words according to split_time
    words1 = [w for w in cap.words if w.end <= req.split_time or w.start < req.split_time]
    words2 = [w for w in cap.words if w.start >= req.split_time]

    if not words1:
        words1 = cap.words[:max(1, len(cap.words)//2)]
        words2 = cap.words[max(1, len(cap.words)//2):]

    cap1 = CaptionItem(
        id=f"{cap.id}_a",
        start=cap.start,
        end=req.split_time,
        text=" ".join(w.word for w in words1),
        pos_x=cap.pos_x,
        pos_y=cap.pos_y,
        words=words1,
        style=cap.style,
        source_language=cap.source_language
    )

    cap2 = CaptionItem(
        id=f"{cap.id}_b",
        start=req.split_time,
        end=cap.end,
        text=" ".join(w.word for w in words2),
        pos_x=cap.pos_x,
        pos_y=cap.pos_y,
        words=words2,
        style=cap.style,
        source_language=cap.source_language
    )

    state.captions[target_idx:target_idx+1] = [cap1, cap2]
    project_manager.save_project(state)
    return {'captions': [c.model_dump() for c in state.captions]}

@router.post("/merge")
async def merge_captions(req: MergeCaptionsRequest):
    state = project_manager.get_project(req.project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    cap1 = next((c for c in state.captions if c.id == req.caption_id_1), None)
    cap2 = next((c for c in state.captions if c.id == req.caption_id_2), None)
    if not cap1 or not cap2:
        raise HTTPException(status_code=404, detail="One or both captions not found")

    merged = CaptionItem(
        id=f"merged_{cap1.id}",
        start=min(cap1.start, cap2.start),
        end=max(cap1.end, cap2.end),
        text=f"{cap1.text} {cap2.text}",
        pos_x=cap1.pos_x,
        pos_y=cap1.pos_y,
        words=sorted(cap1.words + cap2.words, key=lambda w: w.start),
        style=cap1.style,
        source_language=cap1.source_language
    )

    state.captions = [c for c in state.captions if c.id not in (req.caption_id_1, req.caption_id_2)]
    state.captions.append(merged)
    state.captions.sort(key=lambda c: c.start)

    project_manager.save_project(state)
    return {'captions': [c.model_dump() for c in state.captions]}

class DetectKeywordsRequest(BaseModel):
    project_id: str

@router.post("/detect-keywords")
async def detect_keywords(req: DetectKeywordsRequest):
    state = get_or_create_project(req.project_id)

    enriched = transcription_service.enrich_captions_with_keywords(state.captions)
    state.captions = enriched
    project_manager.save_project(state)

    keyword_count = sum(1 for c in enriched for w in c.words if w.is_keyword)
    return {
        'keyword_count': keyword_count,
        'captions': [c.model_dump() for c in state.captions]
    }

class DetectDimensionsAndCuesRequest(BaseModel):
    project_id: str
    auto_apply: bool = True

@router.post("/detect-dimensions-and-cues")
async def detect_dimensions_and_cues_endpoint(req: DetectDimensionsAndCuesRequest):
    state = get_or_create_project(req.project_id)

    res = transcription_service.detect_dimensions_and_cues(state.captions, project_id=req.project_id)
    if len(res) == 3:
        cues, graphics, reasoning_log = res
    else:
        cues, graphics = res
        reasoning_log = [c.get("reasoning", {}) for c in cues if "reasoning" in c]

    if req.auto_apply:
        # Preserve user custom graphics, replace prior auto-generated cues
        manual_graphics = [g for g in state.graphics if not (g.id.startswith("split_") or g.id.startswith("dim_"))]
        state.graphics = manual_graphics + (graphics or [])
        project_manager.save_project(state)

    return {
        'detected_count': len(cues),
        'cues': cues,
        'graphics': [g.model_dump() for g in state.graphics],
        'reasoning_log': reasoning_log
    }

