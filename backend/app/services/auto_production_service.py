import os
import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.core.config import settings
from app.core.models import ProjectState, CaptionItem, MotionGraphicItem, WordTiming
from app.services.project_manager import project_manager
from app.services.proxy_generator import proxy_generator
from app.services.transcription_service import transcription_service
from app.services.translation_service import translation_service
from app.services.twelve_labs_service import twelve_labs_service
from app.services.media_search_service import media_search_service

def compute_file_hash(file_path: str) -> str:
    """
    Computes a full-file SHA-256 hash. Fast and collision-free on proxy-sized media.
    """
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


class AutoProductionService:
    def __init__(self):
        self._lock = threading.Lock()

    def get_ingestion_status(self, project_id: str) -> Dict[str, Any]:
        state = project_manager.get_project(project_id)
        if not state:
            return {"status": "none", "is_completed": False}
        ingestion = state.ai_ingestion or {}
        return {
            "status": ingestion.get("status", "none"),
            "video_hash": ingestion.get("video_hash", ""),
            "completed_at": ingestion.get("completed_at"),
            "is_completed": ingestion.get("status") == "completed",
            "summary": ingestion.get("summary", {})
        }

    def run_pipeline(self, project_id, force=False, model_size="base"):
        if not self._lock.acquire(blocking=False):
            return {'success':False,'error':'An automatic edit is already running. Wait for it to finish.'}
        try:return self._run_pipeline(project_id,force,model_size)
        finally:self._lock.release()

    def _run_pipeline(
        self,
        project_id: str,
        force: bool = False,
        model_size: str = "base"
    ) -> Dict[str, Any]:
        """
        Executes the zero-click auto-production pipeline:
        1. Checks video hash to ensure it runs strictly once per newly uploaded video file.
        2. Whisper dialogue transcription with word timestamps.
        3. Keyword analysis & emphasis for high-contrast badges and subtitle pop.
        4. Neural & dictionary translation (Hindi/Hinglish -> English).
        5. Twelve Labs Multimodal video analysis & credit metering.
        6. Multimodal visual placement:
           - Dimension callouts (e.g., '7 CM', '10 mm') with animated HUD ticks
           - 50/50 vertical split screens with licensed visual proof & citations
           - Cutaway B-roll video inserts with CRT scanlines & badges
           - Reconstructed article / investigative report screens
        7. Saves project state and marks ingestion completed.
        """
        state = project_manager.get_project(project_id)
        if not state:
            return {"success": False, "error": f"Project {project_id} not found"}

        initial_content=state.model_dump(include={"source_media_path","captions","graphics","settings"})
        pdir = settings.projects_dir / project_id
        media_file = None
        if state.source_media_path and os.path.exists(state.source_media_path):
            media_file = state.source_media_path
        elif (pdir / "sub.mov").exists():
            media_file = str(pdir / "sub.mov")
        else:
            for pat in ["*.mp4", "*.mov", "*.m4v", "*.webm"]:
                cand = list(pdir.glob(pat))
                if cand:
                    media_file = str(cand[0])
                    state.source_media_path = media_file
                    break

        if not media_file or not os.path.exists(media_file):
            return {"success": False, "error": "No source video media found in project"}

        video_hash = compute_file_hash(media_file)

        from app.services.finished_reel_understanding import source_role
        if source_role(digest=video_hash)=='finished_reference':
            return {'success':False,'project':state.model_dump(),'error':'113.mov is your finished reference, not raw footage. Upload sub.mov as the source; the finished-reel reference style is already configured. Existing timeline preserved.'}

        # Idempotency check: Skip if already executed for this exact video hash
        current_ingestion = state.ai_ingestion or {}
        if not force and current_ingestion.get("status") == "completed" and current_ingestion.get("editorial_run") and current_ingestion.get("video_hash") == video_hash:
            print(f"[AutoProduction] Video {project_id} with hash {video_hash[:8]} already auto-produced. Skipping duplicate run.")
            return {
                "success": True,
                "already_produced": True,
                "project": state.model_dump(),
                "message": "Project video has already been auto-produced. Skipped to preserve Twelve Labs credits.",
                "ingestion": current_ingestion
            }

        print(f"[AutoProduction] Starting zero-click auto-production pipeline for project '{project_id}'...")

        from app.services.editorial_planner import write_json
        from uuid import uuid4
        write_json(pdir/'recovery'/('before-auto-'+uuid4().hex+'.json'),state.model_dump())

        # 0. Ensure duration and proxy exist
        if state.duration_seconds <= 1.0:
            dur, wf = proxy_generator.extract_waveform_and_duration(media_file)
            state.duration_seconds = max(1.0, dur)
            if wf:
                state.waveform_data = wf

        if not state.captions:
            state.ai_ingestion = {**(state.ai_ingestion or {}), 'caption_layout_pending': True}
            # Phase 1: Dialogue Transcription (Whisper)
            print(f"[AutoProduction] Phase 1: Transcribing dialogue via Whisper ({model_size})...")
            detected_lang = "en"
            captions: List[CaptionItem] = []
            try:
                detected_lang, captions = transcription_service.transcribe_with_whisper(
                    media_file,
                    words_per_caption=3,
                    task="transcribe",
                    model_size=model_size
                )
            except Exception as e:
                print(f"[AutoProduction] Whisper transcription notice: {e}")
                if not captions:
                    return {'success':False,'error':'Speech transcription failed. Existing project was preserved; no placeholder dialogue was generated.'}

            # Keep original speech for audit and cross-language cue alignment.
            write_json(pdir/'transcription'/'native_source.json', {
                'video_hash': video_hash, 'language': detected_lang,
                'captions': [c.model_dump() for c in captions],
                'timing_basis': 'ASR word estimates; not independently certified'
            })
            if detected_lang == 'en':
                for caption in captions:
                    caption.translated_text = caption.text
            state.detected_language = detected_lang
            state.captions = captions
            if captions:
                state.duration_seconds = max(state.duration_seconds, captions[-1].end + 0.5)

        # Never ask translation to invent words from structurally corrupt ASR.
        from app.services.transcript_quality import transcript_issues
        speech_issues = transcript_issues(state.captions)
        if speech_issues:
            write_json(pdir/'transcription'/'rejected_source.json', {
                'video_hash': video_hash, 'issues': speech_issues,
                'captions': [c.model_dump() for c in state.captions]})
            try:
                repaired_lang, repaired = transcription_service.transcribe_with_whisper(
                    media_file, words_per_caption=3, task='transcribe', model_size='medium')
                remaining = transcript_issues(repaired)
                if not repaired or remaining:
                    raise ValueError('; '.join(remaining[:5]) or 'No speech recognized')
                state.ai_ingestion = {**(state.ai_ingestion or {}), 'caption_layout_pending': True}
                state.detected_language = repaired_lang
                state.captions = repaired
                write_json(pdir/'transcription'/'native_source.json', {
                    'video_hash': video_hash, 'language': repaired_lang,
                    'captions': [c.model_dump() for c in repaired],
                    'recovery_model': 'medium', 'timing_basis': 'ASR estimates; not independently certified'})
            except Exception as exc:
                from app.services.editorial_planner import safe_error
                return {'success': False, 'project': state.model_dump(),
                        'error': 'Speech recognition produced unreadable text or invalid timings. Stronger local retry failed: ' + safe_error(exc)}

        # Ensure subtitle translation runs for non-English or Devanagari speech
        translation_errors = []
        needs_translation = (
            state.detected_language != 'en'
            or any(translation_service.is_devanagari(c.text) for c in state.captions)
            or any(translation_service.is_devanagari(c.translated_text or '') for c in state.captions)
            or any(not (c.translated_text or '').strip() for c in state.captions)
        )
        is_already_translated = (
            state.detected_language != 'en'
            and all((c.translated_text or '').strip() for c in state.captions)
            and not any(translation_service.is_devanagari(c.translated_text or '') for c in state.captions)
            and any((c.translated_text or '') != c.text for c in state.captions)
        )
        if needs_translation and not is_already_translated:
            try:
                state.captions = translation_service.translate_captions_list(state.captions, checkpoint_dir=pdir/'transcription'/'translation_checkpoints')
            except Exception as exc:
                from app.services.editorial_planner import safe_error
                translation_errors.append('Subtitle translation failed: ' + safe_error(exc))

        if not translation_errors and (state.ai_ingestion or {}).get('caption_layout_pending'):
            from app.services.automatic_captions import layout_automatic_captions
            state.captions = layout_automatic_captions(state.captions)
            state.ai_ingestion['caption_layout_pending'] = False
            if state.captions and len(state.captions[-1].translated_text.split()) != 3:
                state.ai_ingestion['caption_layout_note'] = 'Final group contains fewer than three words; no speech was invented or removed.'

        latest=project_manager.get_project(project_id)
        if not latest or latest.model_dump(include={"source_media_path","captions","graphics","settings"}) != initial_content:
            report = {'status': 'conflict', 'run_id': 'subtitle-conflict', 'stage': 'subtitles',
                      'errors': ['Project changed while subtitles were processing. Existing edits were preserved.']}
            write_json(pdir/'editorial'/'latest.json', report)
            return {'success': False, 'project': latest.model_dump() if latest else state.model_dump(),
                    'editorial_report': report, 'error': report['errors'][0]}
        if latest:
            project_manager.save_project(state)
            initial_content=project_manager.get_project(project_id).model_dump(include={"source_media_path","captions","graphics","settings"})
            write_json(pdir/"editorial"/"checkpoint.json",initial_content)

        if translation_errors:
            report = {'status': 'blocked', 'run_id': 'translation-needs-review',
                      'errors': translation_errors, 'stage': 'translation', 'decisions': []}
            write_json(pdir/'editorial'/'latest.json', report)
            return {'success': False, 'project': state.model_dump(), 'editorial_report': report,
                    'error': 'Translation needs attention before graphics can be planned.'}

        # Separate video understanding, editorial planning and asset review.
        from app.services.editorial_planner import run_editorial, write_json
        protected=[g for g in state.graphics if not g.parameters.get('editorial_generated')]
        generated,reasoning_log,report=run_editorial(state,media_file,protected)
        if translation_errors:
            report['errors'] = report.get('errors', []) + translation_errors
            report['status'] = 'blocked'
            write_json(pdir/'editorial'/'latest.json', report)
        latest=project_manager.get_project(project_id)
        has_manual_conflicts = False
        if latest:
            manual_latest = [g.model_dump() for g in latest.graphics if not g.parameters.get('editorial_generated')]
            manual_init = [g for g in initial_content.get('graphics', []) if not g.get('parameters', {}).get('editorial_generated')]
            if manual_latest != manual_init:
                has_manual_conflicts = True
        if not latest or latest.model_dump(include={"source_media_path","captions","graphics","settings"})!=initial_content:
            report.update(status='conflict',errors=report.get('errors',[])+['Timeline content changed during processing. Saved results require review.'])
            write_json(pdir/'editorial'/'latest.json',report)
            return {'success':True,'project':latest.model_dump() if latest else state.model_dump(),'editorial_report':report,'reasoning_log':reasoning_log}
        if report['status']=='complete':
            current_protected = [g for g in (latest.graphics if latest else state.graphics) if not g.parameters.get('editorial_generated')]
            state.graphics=sorted(current_protected+generated,key=lambda g:g.start)
            project_manager.save_project(state)
        # On a cloud failure retain all existing graphics; successfully generated captions remain usable.
        write_json(pdir/'thumbnails'/'visual_reasoning_log.json',reasoning_log)
        summary={'captions_count':len(state.captions),'graphics_count':len(state.graphics),'inserted':len(state.graphics),'needs_review':report.get('needs_review',0),'outcome':report.get('outcome'),'scorecard':report.get('scorecard')}
        caption_note=(state.ai_ingestion or {}).get('caption_layout_note')
        state.ai_ingestion={'caption_layout_note':caption_note,'status':{'needs_attention':'needs_review','complete_with_gaps':'completed_with_gaps'}.get(report.get('outcome'),'needs_review' if report.get('needs_review') and not report.get('inserted') else 'completed') if report['status']=='complete' else 'needs_configuration','video_hash':video_hash,'completed_at':datetime.now().isoformat(),'summary':summary,'editorial_run':report['run_id'],'errors':report['errors']}
        project_manager.save_project(state)
        return {'success':True,'project':state.model_dump(),'ingestion':state.ai_ingestion,'summary':summary,'reasoning_log':reasoning_log,'editorial_report':report}

auto_production_service = AutoProductionService()
