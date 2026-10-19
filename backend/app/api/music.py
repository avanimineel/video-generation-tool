from typing import Optional

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.models import AudioTrackItem
from app.services import music_service
from app.services.project_manager import project_manager

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("/search")
def search_music(q: Optional[str] = None, mood: Optional[str] = None, min_seconds: float = 0):
    try:
        return {'tracks': music_service.search(q, mood, min_seconds), 'moods': list(music_service.MOODS)}
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except requests.RequestException:
        raise HTTPException(status_code=502, detail='Music search is unavailable right now.')


class AddMusicRequest(BaseModel):
    music_id: str
    volume: float = 0.35
    duck_under_speech: bool = True
    start: float = 0.0


@router.post("/{project_id}/add")
def add_music(project_id: str, req: AddMusicRequest):
    state = project_manager.get_project(project_id)
    if not state: raise HTTPException(status_code=404, detail='Project not found')
    try:
        track = music_service.lookup(req.music_id)
        music_service.download(track)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (requests.RequestException, RuntimeError):
        raise HTTPException(status_code=502, detail='The track could not be downloaded. Try another one.')
    length = max(1.0, (state.duration_seconds or track['duration']) - req.start)
    # One music bed per project: a new choice replaces the old one.
    state.audio_tracks = [t for t in state.audio_tracks if t.type != 'music'] + [AudioTrackItem(
        id=f"music_{track['id'][:8]}", title=track['title'], type='music', url=f"/api/music/file/{track['id']}",
        duration=min(length, track['duration'] or length), start=max(0.0, req.start), volume=min(1.0, max(0.0, req.volume)),
        duck_under_speech=req.duck_under_speech, music_id=track['id'], license=f"{track['license']} {track.get('license_version') or ''}".strip(),
        attribution=track['attribution'], credit_required=track['credit_required'])]
    project_manager.save_project(state)
    return state


@router.get("/file/{music_id}")
def music_file(music_id: str):
    path = music_service.local_file(music_id)
    if not path: raise HTTPException(status_code=404, detail='Track not downloaded')
    return FileResponse(path, media_type='audio/mpeg' if path.suffix == '.mp3' else 'audio/' + path.suffix.lstrip('.'))
