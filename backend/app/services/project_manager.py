import json
import re
import os
import fcntl
from functools import wraps
from threading import RLock
from uuid import uuid4

class ProjectConflict(ValueError):
    pass

def same_project_content(left, right):
    return left.model_dump(exclude={"updated_at"}) == right.model_dump(exclude={"updated_at"})

def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    try:
        with temp.open('w') as handle:
            handle.write(text); handle.flush(); os.fsync(handle.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

def project_locked(fn):
    @wraps(fn)
    def wrapped(self, value, *args, **kwargs):
        pid=value.id if hasattr(value, 'id') else value
        if not re.fullmatch(r'[A-Za-z0-9_-]+', pid):
            raise ValueError('Invalid project identifier')
        locks=self.projects_dir/'.locks';locks.mkdir(parents=True, exist_ok=True)
        with self._io_lock, (locks/(pid+'.lock')).open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:return fn(self,value,*args,**kwargs)
            finally:fcntl.flock(handle,fcntl.LOCK_UN)
    return wrapped
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from app.core.config import settings
from app.core.models import ProjectState, ProjectRecord, CaptionItem, MotionGraphicItem, ProjectSettings
from app.core.database import engine

def sanitize_folder_name(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', name.strip())
    return cleaned or 'Untitled_Project'

class ProjectManager:
    def __init__(self, projects_dir: Path = settings.projects_dir):
        self._io_lock = RLock()
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _get_project_dir(self, project_id: str) -> Path:
        pdir = self.projects_dir / project_id
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / 'proxies').mkdir(parents=True, exist_ok=True)
        (pdir / 'thumbnails').mkdir(parents=True, exist_ok=True)
        return pdir

    def create_project(self, name: str, aspect_ratio: str = '9:16', source_media_path: Optional[str] = None) -> ProjectState:
        now_str = datetime.now().isoformat()
        project_id = f"{sanitize_folder_name(name)}_{int(datetime.now().timestamp())}_{uuid4().hex[:8]}"
        pdir = self._get_project_dir(project_id)

        state = ProjectState(
            id=project_id,
            name=name,
            created_at=now_str,
            updated_at=now_str,
            source_media_path=source_media_path,
            duration_seconds=0.0,
            settings=ProjectSettings(aspect_ratio=aspect_ratio),
            captions=[],
            graphics=[],
            detected_language='en'
        )

        self.save_project(state)
        return state

    @project_locked
    def save_project(self, state: ProjectState) -> None:
        existing=self.projects_dir/state.id/'project.json'
        if existing.exists():
            old=json.loads(existing.read_text())
            if 'snapshot' in old and state.updated_at <= old.get('updated_at', '') and same_project_content(state, ProjectState.model_validate(old['snapshot'])):
                state.updated_at = old['updated_at']
                return
            if state.updated_at != old.get('updated_at'):
                raise ProjectConflict('A newer project revision exists. Reload before saving; your saved edits were preserved.')
            # Bootstrap legacy projects into an atomic snapshot BEFORE changing mirrors.
            if 'snapshot' not in old:
                root=existing.parent
                snapshot=dict(old)
                for key in ('settings','captions','graphics'):
                    f=root/(key+'.json')
                    snapshot[key]=json.loads(f.read_text()) if f.exists() else ({} if key=='settings' else [])
                wf=root/'thumbnails'/'waveform.json'
                snapshot['waveform_data']=json.loads(wf.read_text()) if wf.exists() else []
                old['snapshot']=snapshot
                atomic_text(existing,json.dumps(old,ensure_ascii=False))
            atomic_text(existing.parent/'recovery'/'last-good-state.json',json.dumps(old['snapshot'],ensure_ascii=False))
        state.updated_at = datetime.now().isoformat()
        pdir = self._get_project_dir(state.id)

        # 1. project.json (Core metadata)
        meta = {
            'id': state.id,
            'name': state.name,
            'created_at': state.created_at,
            'updated_at': state.updated_at,
            'source_media_path': state.source_media_path,
            'proxy_media_path': state.proxy_media_path,
            'duration_seconds': state.duration_seconds,
            'fps': state.fps,
            'detected_language': state.detected_language,
            'ai_ingestion': state.ai_ingestion or {}
        }
        meta['snapshot'] = state.model_dump()

        # 2. settings.json
        atomic_text((pdir / 'settings.json'), json.dumps(state.settings.model_dump(), indent=2))

        # 3. captions.json
        captions_data = [c.model_dump() for c in state.captions]
        atomic_text((pdir / 'captions.json'), json.dumps(captions_data, indent=2))

        # 4. transcript.json & translation.json
        transcript_data = {
            'language': state.detected_language,
            'segments': [
                {'id': c.id, 'start': c.start, 'end': c.end, 'text': c.text, 'words': [w.model_dump() for w in c.words]}
                for c in state.captions
            ]
        }
        atomic_text((pdir / 'transcript.json'), json.dumps(transcript_data, indent=2))

        translation_data = {
            'segments': [
                {'id': c.id, 'start': c.start, 'end': c.end, 'translated_text': c.translated_text}
                for c in state.captions if c.translated_text
            ]
        }
        atomic_text((pdir / 'translation.json'), json.dumps(translation_data, indent=2))

        # 5. graphics.json
        graphics_data = [g.model_dump() for g in state.graphics]
        atomic_text((pdir / 'graphics.json'), json.dumps(graphics_data, indent=2))

        # 6. waveform.json
        if state.waveform_data:
            atomic_text((pdir / 'thumbnails' / 'waveform.json'), json.dumps(state.waveform_data))

        atomic_text(pdir/'project.json', json.dumps(meta, ensure_ascii=False, indent=2))

        # Update SQLite index
        with Session(engine) as session:
            rec = session.get(ProjectRecord, state.id)
            if not rec:
                rec = ProjectRecord(
                    id=state.id,
                    name=state.name,
                    created_at=state.created_at,
                    updated_at=state.updated_at,
                    source_media_path=state.source_media_path,
                    proxy_media_path=state.proxy_media_path,
                    duration_seconds=state.duration_seconds,
                    aspect_ratio=state.settings.aspect_ratio,
                    caption_count=len(state.captions),
                    graphic_count=len(state.graphics),
                    davinci_project_name=state.settings.davinci_project_name,
                    davinci_timeline_name=state.settings.davinci_timeline_name
                )
                session.add(rec)
            else:
                rec.name = state.name
                rec.updated_at = state.updated_at
                rec.source_media_path = state.source_media_path
                rec.proxy_media_path = state.proxy_media_path
                rec.duration_seconds = state.duration_seconds
                rec.aspect_ratio = state.settings.aspect_ratio
                rec.caption_count = len(state.captions)
                rec.graphic_count = len(state.graphics)
                rec.davinci_project_name = state.settings.davinci_project_name
                rec.davinci_timeline_name = state.settings.davinci_timeline_name
            session.commit()

    @project_locked
    def get_project(self, project_id: str) -> Optional[ProjectState]:
        pdir = self.projects_dir / project_id
        if not (pdir / 'project.json').exists():
            return None

        try:
            meta = json.loads((pdir / 'project.json').read_text())
            if 'snapshot' in meta:
                return ProjectState.model_validate(meta['snapshot'])
            settings_data = json.loads((pdir / 'settings.json').read_text()) if (pdir / 'settings.json').exists() else {}
            captions_data = json.loads((pdir / 'captions.json').read_text()) if (pdir / 'captions.json').exists() else []
            graphics_data = json.loads((pdir / 'graphics.json').read_text()) if (pdir / 'graphics.json').exists() else []
            waveform = []
            if (pdir / 'thumbnails' / 'waveform.json').exists():
                waveform = json.loads((pdir / 'thumbnails' / 'waveform.json').read_text())

            source_path = meta.get('source_media_path')
            if source_path and not os.path.isabs(source_path):
                if (pdir / source_path).exists():
                    source_path = str(pdir / source_path)
            elif not source_path and (pdir / 'sub.mov').exists():
                source_path = str(pdir / 'sub.mov')

            return ProjectState(
                id=meta['id'],
                name=meta.get('name', 'Untitled'),
                created_at=meta.get('created_at', ''),
                updated_at=meta.get('updated_at', ''),
                source_media_path=source_path,
                proxy_media_path=meta.get('proxy_media_path'),
                waveform_data=waveform,
                duration_seconds=meta.get('duration_seconds', 0.0),
                fps=meta.get('fps', 30.0),
                settings=ProjectSettings(**settings_data),
                captions=[CaptionItem(**c) for c in captions_data],
                graphics=[MotionGraphicItem(**g) for g in graphics_data],
                detected_language=meta.get('detected_language', 'en'),
                ai_ingestion=meta.get('ai_ingestion', {})
            )
        except Exception as e:
            print(f'Error reading project {project_id}:', e)
            return None

    def list_projects(self) -> List[Dict[str, Any]]:
        results = []
        with Session(engine) as session:
            records = session.exec(select(ProjectRecord).order_by(ProjectRecord.updated_at.desc())).all()
            for r in records:
                pdir = self.projects_dir / r.id
                if not (pdir / 'project.json').exists():
                    continue
                media_exists = bool(
                    (r.source_media_path and os.path.exists(r.source_media_path)) or
                    (r.source_media_path and (pdir / r.source_media_path).exists()) or
                    (pdir / "sub.mov").exists()
                )
                results.append({
                    'id': r.id,
                    'name': r.name,
                    'created_at': r.created_at,
                    'updated_at': r.updated_at,
                    'duration_seconds': r.duration_seconds,
                    'aspect_ratio': r.aspect_ratio,
                    'caption_count': r.caption_count,
                    'graphic_count': r.graphic_count,
                    'source_media_path': r.source_media_path,
                    'source_media_exists': media_exists,
                    'davinci_project_name': r.davinci_project_name,
                    'davinci_timeline_name': r.davinci_timeline_name
                })
        return results


    def rename_project(self, project_id: str, new_name: str) -> Optional[ProjectState]:
        state = self.get_project(project_id)
        if not state:
            return None
        state.name = new_name
        self.save_project(state)
        return state

    def relink_media(self, project_id: str, new_source_path: str) -> Optional[ProjectState]:
        state = self.get_project(project_id)
        if not state:
            return None
        state.source_media_path = new_source_path
        self.save_project(state)
        return state

    @project_locked
    def delete_project(self, project_id: str) -> bool:
        """
        Deletes a project completely:
        1. Removes from SQLite database record.
        2. Safely removes the entire project directory from disk.
        """
        import shutil
        import stat

        # 1. Delete SQLite record
        try:
            with Session(engine) as session:
                rec = session.get(ProjectRecord, project_id)
                if rec:
                    session.delete(rec)
                    session.commit()
        except Exception as e:
            print(f"[ProjectManager] Warning deleting SQLite record for {project_id}: {e}")

        # 2. Remove directory from disk
        pdir = self.projects_dir / project_id
        if pdir.exists():
            def _remove_readonly(func, path, excinfo):
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass

            try:
                shutil.rmtree(pdir, onerror=_remove_readonly)
            except Exception as e:
                print(f"[ProjectManager] Error in shutil.rmtree for {pdir}: {e}")
                try:
                    shutil.rmtree(pdir, ignore_errors=True)
                except Exception:
                    pass

            return not pdir.exists()

        return True

    def bulk_delete_projects(self, project_ids: list[str]) -> dict:
        results = {}
        for pid in project_ids:
            results[pid] = self.delete_project(pid)
        return {
            "success": True,
            "deleted_count": sum(1 for v in results.values() if v),
            "results": results
        }

project_manager = ProjectManager()
