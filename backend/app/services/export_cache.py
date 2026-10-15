import hashlib
import json
from pathlib import Path
from app.core.config import settings
from app.services.editorial_planner import write_json

def fingerprint(state, subtitles_only):
    payload=state.model_dump(exclude={'updated_at','ai_ingestion','waveform_data'})
    paths=[Path(state.source_media_path)] if state.source_media_path else []
    root=settings.projects_dir/state.id
    for folder in (root/'assets',root/'media'):
        if folder.exists():paths.extend(p for p in folder.rglob('*') if p.is_file())
    inputs=[]
    for path in paths:
        if path.exists():
            stat=path.stat();inputs.append((str(path),stat.st_size,stat.st_mtime_ns))
    return hashlib.sha256(json.dumps({'renderer':2,'state':payload,'subtitles_only':subtitles_only,'inputs':sorted(inputs)},sort_keys=True).encode()).hexdigest()

def cache_matches(path, signature):
    try:
        meta=json.loads(path.with_suffix('.render.json').read_text())
        return path.is_file() and path.stat().st_size>0 and meta.get('signature')==signature and meta.get('size')==path.stat().st_size
    except (ValueError,OSError):return False

def remember(path, signature):
    path=Path(path)
    if path.is_file():write_json(path.with_suffix('.render.json'),{'signature':signature,'size':path.stat().st_size})
