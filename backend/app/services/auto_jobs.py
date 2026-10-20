"""Server-owned automatic edits survive browser navigation and expose progress."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime, timezone
import json
from pathlib import Path
from app.core.config import settings
from app.core.logging_setup import (
    format_exception_detail,
    get_logger,
    log_context,
)
from app.services.project_manager import project_manager
from app.services.editorial_planner import write_json, safe_error

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='automatic-edit')
_lock = Lock()
_jobs = {}


def _path(pid):
    return settings.projects_dir / pid / 'auto_job.json'


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


def start(pid, force=False, model_size='small'):
    if not project_manager.get_project(pid):
        raise ValueError('Project not found')
    with _lock:
        if _jobs.get(pid, {}).get('status') in ('queued', 'running'):
            return dict(_jobs[pid])
        _jobs[pid] = {
            'status': 'queued',
            'stage': 'waiting',
            'started_epoch': datetime.now(timezone.utc).timestamp(),
        }
        write_json(_path(pid), _jobs[pid])
    logger.info(
        "auto_job_queued",
        event="auto_job_queued",
        project_id=pid,
        force=force,
        model_size=model_size,
    )

    def work():
        from app.services.auto_production_service import auto_production_service

        with log_context(project_id=pid, job_stage='transcription_and_translation'):
            _save(pid, status='running', stage='transcription_and_translation')
            logger.info(
                "auto_job_stage",
                event="stage_transition",
                stage="transcription_and_translation",
                project_id=pid,
                force=force,
                model_size=model_size,
            )
            try:
                result = auto_production_service.run_pipeline(pid, force, model_size)
                report = result.get('editorial_report', {}) or {}
                # Skipped ideas are normal editorial output; only a run that produced no
                # visuals, or was blocked, needs the user's attention.
                needs_attention = (
                    report.get('status') in ('blocked', 'conflict', 'needs_review', 'needs_configuration')
                    or report.get('outcome') == 'needs_attention'
                    or (bool(report.get('needs_review')) and not report.get('inserted'))
                )
                error = '; '.join(report.get('errors', [])) or result.get('error')
                error_detail = result.get('error_detail')
                final_status = (
                    'needs_attention'
                    if needs_attention
                    else ('complete' if result.get('success') else 'failed')
                )
                final_stage = report.get('stage', 'review') if needs_attention else 'finished'
                payload = dict(
                    status=final_status,
                    stage=final_stage,
                    result=result,
                    error=error,
                    outcome=report.get('outcome'),
                    scorecard=report.get('scorecard'),
                )
                if error_detail:
                    payload['error_detail'] = error_detail
                elif error and not result.get('success'):
                    payload['error_detail'] = {
                        'type': 'PipelineError',
                        'message': str(error)[:1500],
                    }
                _save(pid, **payload)
                logger.info(
                    "auto_job_finished",
                    event="auto_job_finished",
                    project_id=pid,
                    status=final_status,
                    stage=final_stage,
                    success=bool(result.get('success')),
                )
            except Exception as exc:
                detail = format_exception_detail(exc)
                logger.exception(
                    "auto_job_failed",
                    event="auto_job_failed",
                    project_id=pid,
                    stage="transcription_and_translation",
                    force=force,
                    model_size=model_size,
                    error_detail=detail,
                )
                _save(
                    pid,
                    status='failed',
                    error=safe_error(exc),
                    error_detail=detail,
                    stage='failed',
                )

    _executor.submit(work)
    return status(pid)
