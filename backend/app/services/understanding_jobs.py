"""Read-only analysis jobs: separate artifacts, no project saves or asset downloads."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import json
from app.core.config import settings
from app.services.editorial_planner import run_editorial, safe_error
from app.services.project_manager import project_manager

_pool=ThreadPoolExecutor(max_workers=1)
_lock=Lock()
_jobs={}

def status(pid):
    folder=settings.projects_dir/pid/'understanding'
    job=dict(_jobs.get(pid,{}))
    report={}
    if (folder/'latest.json').exists():
        report=json.loads((folder/'latest.json').read_text())
        import re
        run=report.get('run_id','')
        if re.fullmatch(r'[0-9T]+-[a-f0-9]+',run):
            report['stages']={p.stem:json.loads(p.read_text()) for p in sorted((folder/run).glob('0*.json'))}
        if report.get('status')=='running' and not job:
            report.update(status='interrupted',errors=['Backend restarted during analysis. Run Analyze understanding again.'])
    if job.get('status') in ('queued','running','failed'):
        report['status']=job['status']
        if not report.get('stage') or job['status']=='queued':report['stage']=job.get('stage')
        if job.get('errors'):report['errors']=job['errors']
    if not report:report={'status':'not_run','decisions':[]}
    from app.services.finished_reel_understanding import load_profile, editor_reference
    profile=load_profile()
    report['reference_profile']={k:profile[k] for k in ('id','name','method','alignment','examples','rules')}
    project = project_manager.get_project(pid)
    report['editor_reference'] = editor_reference(project.source_media_path if project else None)
    return report

def start(pid):
    from app.services.auto_jobs import active
    if active(pid):raise ValueError('Wait for automatic editing to finish before reviewing understanding.')
    project=project_manager.get_project(pid)
    if not project or not project.source_media_path or not project.captions:raise ValueError('Upload and transcribe a video before analyzing its meaning.')
    with _lock:
        if _jobs.get(pid,{}).get('status') in ('queued','running'):return dict(_jobs[pid])
        job={'status':'queued','stage':'waiting'};_jobs[pid]=job
    def work():
        try:
            job.update(status='running',stage='video_understanding')
            _,_,report=run_editorial(project,project.source_media_path,[g for g in project.graphics if not g.parameters.get('editorial_generated')],plan_only=True)
            job.update(status=report['status'],stage=report['stage'])
        except Exception as e:job.update(status='failed',errors=[safe_error(e)])
    _pool.submit(work)
    return dict(job)
