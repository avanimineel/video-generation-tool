from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.models import ProjectState
from app.services.project_manager import project_manager, same_project_content

router = APIRouter(prefix="/api/projects", tags=["projects"])

class CreateProjectRequest(BaseModel):
    name: str
    aspect_ratio: str = "9:16"
    source_media_path: Optional[str] = None

class RenameProjectRequest(BaseModel):
    new_name: str

class RelinkMediaRequest(BaseModel):
    new_source_path: str

@router.get("")
async def list_projects():
    return {'projects': project_manager.list_projects()}

@router.post("")
async def create_project(req: CreateProjectRequest):
    project = project_manager.create_project(req.name, req.aspect_ratio, req.source_media_path)
    return project

class BulkDownloadRequest(BaseModel):
    project_ids: list[str]

@router.post('/bulk/download')
def bulk_download(req: BulkDownloadRequest):
    import json, tempfile, zipfile, re
    from pathlib import Path
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask
    from app.core.config import settings
    ids=list(dict.fromkeys(req.project_ids))
    if not ids:raise HTTPException(400,'Select at least one project.')
    states=[]
    for pid in ids:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',pid):raise HTTPException(400,'Invalid project identifier')
        state=project_manager.get_project(pid)
        if not state:raise HTTPException(404,'Selected project is unavailable')
        from app.services.auto_jobs import active
        if active(pid):raise HTTPException(409,'Wait for selected projects to finish processing.')
        states.append(state)
    handle=tempfile.NamedTemporaryFile(suffix='.zip',delete=False);target=Path(handle.name);handle.close()
    try:
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            for state in states:
                root=(settings.projects_dir/state.id).resolve()
                archive.writestr(state.id+'/project-state.json',state.model_dump_json(indent=2))
                for path in root.rglob('*'):
                    if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root) and not any(part.startswith('.') for part in path.relative_to(root).parts):
                        archive.write(path,state.id+'/'+path.relative_to(root).as_posix())
                source=Path(state.source_media_path or '')
                if source.is_file() and not source.is_symlink() and not source.resolve().is_relative_to(root):
                    archive.write(source,state.id+'/source/'+source.name)
            archive.writestr('README.txt','Saved project edits, local assets, and existing exports. No new MP4 render is started by this download. Source paths may need relinking on another computer.')
        return FileResponse(target,filename='selected-projects.zip',media_type='application/zip',background=BackgroundTask(target.unlink,missing_ok=True))
    except Exception:
        target.unlink(missing_ok=True);raise

@router.get("/{project_id}")
async def get_project(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return state

@router.put("/{project_id}")
async def save_project(project_id: str, state: ProjectState):
    if state.id != project_id:
        state.id = project_id
    from app.services.auto_jobs import active
    if active(project_id):raise HTTPException(status_code=409,detail='Automatic editing is running. Saved results are protected from stale browser state.')
    if not project_manager.get_project(project_id):raise HTTPException(404, 'Project not found')
    project_manager.save_project(state)
    return {'success': True, 'updated_at': state.updated_at}

@router.post("/{project_id}/autosave")
async def autosave_project(project_id: str, state: ProjectState):
    if state.id != project_id:
        state.id = project_id
    from app.services.auto_jobs import active
    if active(project_id):raise HTTPException(status_code=409,detail='Automatic editing is running. Saved results are protected from stale browser state.')
    latest=project_manager.get_project(project_id)
    if not latest:
        raise HTTPException(status_code=404, detail="Project not found or has been deleted.")
    if state.updated_at <= latest.updated_at and same_project_content(state, latest):
        return {'success': True, 'autosaved_at': latest.updated_at, 'subject_masks': {}}
    if state.updated_at != latest.updated_at:
        raise HTTPException(status_code=409,detail='A newer project version is saved. Reload it before editing.')
    from starlette.concurrency import run_in_threadpool
    from app.services.subject_layers import prepare_subject_layers
    await run_in_threadpool(prepare_subject_layers,state,state.graphics)
    current=project_manager.get_project(project_id)
    if not current or current.updated_at != latest.updated_at:
        raise HTTPException(status_code=409,detail='Project changed while preparing speaker masks. Reload before saving.')
    project_manager.save_project(state)
    masks={g.id:{k:g.parameters[k] for k in ('subject_mask','subject_mask_error') if k in g.parameters} for g in state.graphics if g.parameters.get('title_style') in ('behind_subject', 'cards_broll')}
    return {'success': True, 'autosaved_at': state.updated_at, 'subject_masks': masks}

@router.post("/{project_id}/rename")
async def rename_project(project_id: str, req: RenameProjectRequest):
    updated = project_manager.rename_project(project_id, req.new_name)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated

@router.post("/{project_id}/relink")
async def relink_media(project_id: str, req: RelinkMediaRequest):
    updated = project_manager.relink_media(project_id, req.new_source_path)
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated

class BulkDeleteProjectsRequest(BaseModel):
    project_ids: list[str]

@router.post("/bulk-delete")
async def bulk_delete_projects_endpoint(req: BulkDeleteProjectsRequest):
    res = project_manager.bulk_delete_projects(req.project_ids)
    return res

@router.delete("/{project_id}")
async def delete_project_endpoint(project_id: str):
    success = project_manager.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete project")
    return {"success": True, "project_id": project_id}

@router.post('/{project_id}/quality-preview')
def create_quality_preview(project_id: str):
    from app.services.quality_preview import start
    project=project_manager.get_project(project_id)
    if not project:raise HTTPException(404,'Project not found')
    try:return start(project)
    except ValueError as e:raise HTTPException(422,str(e))

@router.get('/{project_id}/quality-preview')
def quality_preview_status(project_id: str):
    from app.services.quality_preview import status
    if not project_manager.get_project(project_id):raise HTTPException(404,'Project not found')
    return status(project_id)

@router.get('/{project_id}/quality-preview/{revision}/video')
def quality_preview_video(project_id: str, revision: str):
    import re
    from fastapi.responses import FileResponse
    from app.core.config import settings
    if not project_manager.get_project(project_id) or not re.fullmatch(r'[a-f0-9]{16}',revision):raise HTTPException(404,'Preview not found')
    path=settings.projects_dir/project_id/'quality'/revision/'preview.mp4'
    if not path.exists():raise HTTPException(404,'Preview not ready')
    return FileResponse(path,media_type='video/mp4',filename='documentary-style-preview.mp4')

@router.get('/{project_id}/media-coverage')
def get_media_coverage(project_id: str):
    from app.services.high_density_media_service import calculate_media_coverage
    if not project_manager.get_project(project_id):
        raise HTTPException(404, 'Project not found')
    return calculate_media_coverage(project_id)

@router.post('/{project_id}/maximize-media-density')
def maximize_project_media_density(project_id: str):
    from app.services.high_density_media_service import maximize_media_density
    if not project_manager.get_project(project_id):
        raise HTTPException(404, 'Project not found')
    try:
        return maximize_media_density(project_id, target_coverage=0.85)
    except Exception as e:
        raise HTTPException(500, str(e))

