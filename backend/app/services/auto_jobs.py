"""Server-owned automatic edits survive browser navigation and expose progress."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime, timezone
import json
from pathlib import Path
from app.core.config import settings
from app.services.project_manager import project_manager
from app.services.editorial_planner import write_json,safe_error

_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='automatic-edit')
_lock=Lock()
_jobs={}

def _path(pid):return settings.projects_dir/pid/'auto_job.json'
def status(pid):
    with _lock:job=dict(_jobs.get(pid,{}))
    if not job and _path(pid).exists():
        job=json.loads(_path(pid).read_text())
        if job.get('status') in ('queued','running'):
            job.update(status='interrupted',error='The backend restarted during processing. Resume automatic editing to continue; saved captions are retained.')
    report=settings.projects_dir/pid/'editorial'/'latest.json'
    if job.get('status')=='running' and report.exists() and report.stat().st_mtime>=job.get('started_epoch',0):
        current=json.loads(report.read_text())
        job['stage']=current.get('stage',job.get('stage'))
        run_id=current.get('run_id','')
        if run_id and Path(run_id).name==run_id:
            progress=report.parent/run_id/'progress.json'
            if progress.exists():
                try:job['progress']=json.loads(progress.read_text())
                except (ValueError,OSError):pass
    return job or {'status':'none'}
def active(pid):return status(pid).get('status') in ('queued','running')
def _save(pid,**changes):
    with _lock:
        _jobs[pid].update(changes);write_json(_path(pid),_jobs[pid])
def start(pid,force=False,model_size='small'):
    if not project_manager.get_project(pid):raise ValueError('Project not found')
    with _lock:
        if _jobs.get(pid,{}).get('status') in ('queued','running'):return dict(_jobs[pid])
        _jobs[pid]={'status':'queued','stage':'waiting','started_epoch':datetime.now(timezone.utc).timestamp()}
        write_json(_path(pid),_jobs[pid])
    def work():
        from app.services.auto_production_service import auto_production_service
        _save(pid,status='running',stage='transcription_and_translation')
        try:
            result=auto_production_service.run_pipeline(pid,force,model_size)
            report=result.get('editorial_report', {})
            # Skipped ideas are normal editorial output; only a run that produced no
            # visuals, or was blocked, needs the user's attention.
            needs_attention=report.get('status') in ('blocked', 'conflict', 'needs_review', 'needs_configuration') or report.get('outcome')=='needs_attention' or (bool(report.get('needs_review')) and not report.get('inserted'))
            error='; '.join(report.get('errors', [])) or result.get('error')
            # Prefer pipeline stage (e.g. whisper_transcribe) over generic finished/review.
            finished_stage=result.get('stage') or (report.get('stage', 'review') if needs_attention else 'finished')
            payload={
                'status':'needs_attention' if needs_attention else ('complete' if result.get('success') else 'failed'),
                'stage':finished_stage,
                'result':result,
                'error':error,
                'outcome':report.get('outcome'),
                'scorecard':report.get('scorecard'),
            }
            # Persist cause fields on auto_job.json / status API (not only buried in result).
            error_cause=result.get('error_cause')
            if error_cause:
                payload['error_cause']=error_cause
            error_detail=result.get('error_detail')
            if error_detail:
                payload['error_detail']=error_detail
            elif error and not result.get('success'):
                payload['error_detail']={'type':'PipelineError','message':str(error)[:1500]}
                payload.setdefault('error_cause', str(error)[:1500])
            _save(pid,**payload)

        except Exception as exc:
            _save(pid,status='failed',stage='auto_job_worker',error=safe_error(exc),
                  error_cause=safe_error(exc),
                  error_detail={'type':type(exc).__name__,'message':safe_error(exc),'stage':'auto_job_worker'})
    _executor.submit(work)
    return status(pid)
