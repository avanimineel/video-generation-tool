from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import subprocess
import re
from pydantic import BaseModel
from pathlib import Path
from app.services.davinci_bridge import davinci_bridge
from app.services.project_manager import project_manager
from app.core.config import settings

router = APIRouter(prefix="/api/davinci", tags=["davinci"])

class SyncRequest(BaseModel):
    project_id: str

@router.get("/status")
async def get_davinci_status():
    return davinci_bridge.get_status()

@router.post("/sync")
async def sync_to_davinci(req: SyncRequest):
    state = project_manager.get_project(req.project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    pdir = settings.projects_dir / req.project_id
    res = davinci_bridge.sync_to_resolve(
        project_id=req.project_id,
        captions=state.captions,
        graphics=state.graphics,
        project_dir=pdir
    )

    if res.get('project_name'):
        state.settings.davinci_project_name = res['project_name']
    if res.get('timeline_name'):
        state.settings.davinci_timeline_name = res['timeline_name']
    project_manager.save_project(state)

    return res

@router.post("/{project_id}/export-bundle")
async def export_project_bundle(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    result = davinci_bridge.export_davinci_project_bundle(state)
    return result

@router.get("/{project_id}/download-bundle")
async def download_project_bundle(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', state.name or "Resolve_Project")
    bundle_name = f"{clean_name}_DaVinci_Resolve"
    zip_path = settings.projects_dir / project_id / "exports" / f"{bundle_name}.zip"

    if not zip_path.exists():
        davinci_bridge.export_davinci_project_bundle(state)

    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="Bundle ZIP archive not found")

    return FileResponse(
        path=str(zip_path),
        filename=f"{bundle_name}.zip",
        media_type="application/zip"
    )

@router.post("/{project_id}/open-in-resolve")
async def open_project_in_resolve(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', state.name or "Resolve_Project")
    bundle_name = f"{clean_name}_DaVinci_Resolve"
    
    # Check ~/Movies first, then fallback to backend projects dir
    movies_dir = Path.home() / "Movies" / bundle_name
    backend_dir = settings.projects_dir / project_id / bundle_name

    if not movies_dir.exists() and not backend_dir.exists():
        davinci_bridge.export_davinci_project_bundle(state)

    target_dir = movies_dir if movies_dir.exists() else backend_dir
    cmd_script = target_dir / "open_in_resolve.command"
    if cmd_script.exists():
        try:
            subprocess.Popen(["/bin/bash", str(cmd_script)])
            subprocess.Popen(["open", "-a", "DaVinci Resolve"])
            return {"success": True, "message": f"Prepared {bundle_name} and opened DaVinci Resolve.", "bundle_dir": str(target_dir)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Launcher script not found"}

@router.post("/{project_id}/open-in-finder")
async def open_project_in_finder(project_id: str):
    state = project_manager.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")

    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', state.name or "Resolve_Project")
    bundle_name = f"{clean_name}_DaVinci_Resolve"

    movies_dir = Path.home() / "Movies" / bundle_name
    backend_dir = settings.projects_dir / project_id / bundle_name

    if not movies_dir.exists() and not backend_dir.exists():
        davinci_bridge.export_davinci_project_bundle(state)

    target_dir = movies_dir if movies_dir.exists() else backend_dir
    try:
        subprocess.Popen(["open", str(target_dir)])
        return {"success": True, "bundle_dir": str(target_dir)}
    except Exception as e:
        return {"success": False, "error": str(e)}

