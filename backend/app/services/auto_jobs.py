"""Server-owned automatic edits survive browser navigation and expose progress."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.core.logging_setup import get_logger, log_context
from app.services.project_manager import project_manager
from app.services.editorial_planner import write_json, safe_error

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='automatic-edit')
_lock = Lock()
_jobs = {}


def _path(pid):
    return settings.projects_dir / pid / 'auto_job.json'


def _resolve_produce_mode(request_mode: Optional[str] = None) -> str:
    """Prefer auto_produce_mode helper when present; else AUTO_PRODUCE_MODE env."""
    try:
        from app.services.auto_produce_mode import resolve_auto_produce_mode
        return resolve_auto_produce_mode(request_mode)
    except Exception:
        candidate = (request_mode or os.getenv("AUTO_PRODUCE_MODE") or "full").strip().lower()
        if candidate in ("captions_only", "captions-only", "offline_captions"):
            return "captions_only"
        if candidate in ("full", "auto_edit", "auto-edit"):
            return "full"
        return "full"


def status(pid):
    with _lock:
        job = dict(_jobs.get(pid, {}))
    if not job and _path(pid).exists():
        job = json.loads(_path(pid).read_text())
        if job.get('status') in ('queued', 'running'):
            job.update(
                status='interrupted',
                error='The backend restarted during processing. Resume automatic editing to continue; saved captions are retained.',
            )
    report = settings.projects_dir / pid / 'editorial' / 'latest.json'
    if job.get('status') == 'running' and report.exists() and report.stat().st_mtime >= job.get('started_epoch', 0):
        current = json.loads(report.read_text())
        job['stage'] = current.get('stage', job.get('stage'))
        run_id = current.get('run_id', '')
        if run_id and Path(run_id).name == run_id:
            progress = report.parent / run_id / 'progress.json'
            if progress.exists():
                try:
                    job['progress'] = json.loads(progress.read_text())
                except (ValueError, OSError):
                    pass
    return job or {'status': 'none'}


def active(pid):
    return status(pid).get('status') in ('queued', 'running')


def _save(pid, **changes):
    with _lock:
        _jobs[pid].update(changes)
        write_json(_path(pid), _jobs[pid])


def mark_stage(media_id: str, stage: str, status: str = 'running', **fields: Any) -> None:
    """Single place for auto-produce stage transitions (job JSON + INFO log)."""
    try:
        with _lock:
            if media_id in _jobs:
                _jobs[media_id].update(stage=stage, status=status)
                write_json(_path(media_id), _jobs[media_id])
    except Exception:
        pass
    payload = {
        'event': 'auto_produce_stage',
        'media_id': media_id,
        'project_id': media_id,
        'stage': stage,
        'status': status,
    }
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    logger.info('auto_produce_stage', **payload)


def start(pid, force=False, model_size='small', mode=None):
    if not project_manager.get_project(pid):
        raise ValueError('Project not found')
    produce_mode = _resolve_produce_mode(mode)
    with _lock:
        if _jobs.get(pid, {}).get('status') in ('queued', 'running'):
            return dict(_jobs[pid])
        _jobs[pid] = {
            'status': 'queued',
            'stage': 'waiting',
            'auto_produce_mode': produce_mode,
            'started_epoch': datetime.now(timezone.utc).timestamp(),
        }
        write_json(_path(pid), _jobs[pid])

    logger.info(
        'auto_produce_started',
        event='auto_produce_started',
        media_id=pid,
        project_id=pid,
        mode=produce_mode,
        force=bool(force),
        model_size=model_size,
    )

    def work():
        from app.services.auto_production_service import auto_production_service

        with log_context(project_id=pid, job_stage='transcription'):
            _save(pid, status='running', stage='transcription', auto_produce_mode=produce_mode)
            try:
                try:
                    result = auto_production_service.run_pipeline(
                        pid, force, model_size, mode=produce_mode
                    )
                except TypeError:
                    # Older pipeline signature without mode= kwarg.
                    result = auto_production_service.run_pipeline(pid, force, model_size)
                report = result.get('editorial_report', {}) or {}
                captions_only = (
                    report.get('outcome') == 'captions_only'
                    or report.get('stage') == 'captions_only_complete'
                    or produce_mode == 'captions_only'
                )
                needs_attention = (
                    not captions_only
                    and (
                        report.get('status') in (
                            'blocked', 'conflict', 'needs_review', 'needs_configuration'
                        )
                        or report.get('outcome') == 'needs_attention'
                        or (bool(report.get('needs_review')) and not report.get('inserted'))
                    )
                )
                error = '; '.join(report.get('errors', [])) or result.get('error')
                if needs_attention:
                    final_status = 'needs_attention'
                    final_stage = report.get('stage', 'review')
                elif result.get('success'):
                    final_status = 'complete'
                    final_stage = 'captions_only_complete' if captions_only else 'complete'
                else:
                    final_status = 'failed'
                    final_stage = report.get('stage') or 'failed'
                _save(
                    pid,
                    status=final_status,
                    stage=final_stage,
                    result=result,
                    error=error,
                    outcome=report.get('outcome'),
                    scorecard=report.get('scorecard'),
                    auto_produce_mode=report.get('auto_produce_mode', produce_mode),
                )
                mark_stage(
                    pid,
                    final_stage,
                    status=final_status,
                    mode=produce_mode,
                    success=bool(result.get('success')),
                )
            except Exception as exc:
                mark_stage(pid, 'failed', status='failed', mode=produce_mode, error=safe_error(exc))
                _save(pid, status='failed', error=safe_error(exc), stage='failed')
                logger.exception(
                    'auto_produce_failed',
                    event='auto_produce_failed',
                    media_id=pid,
                    project_id=pid,
                    stage='failed',
                    status='failed',
                    mode=produce_mode,
                    force=bool(force),
                    model_size=model_size,
                )

    _executor.submit(work)
    return status(pid)
