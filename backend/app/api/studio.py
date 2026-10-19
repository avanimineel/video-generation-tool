from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.services.sound_library import catalogue
from app.services.studio import agents, films

router = APIRouter(prefix="/api/studio", tags=["studio"])


class NewFilm(BaseModel):
    url: str = ''
    prompt: str = ''
    aspect: str = '16:9'
    engine: str = 'claude'
    duration: Optional[float] = None


class Remix(BaseModel):
    instruction: str
    engine: Optional[str] = None


class SaveVersion(BaseModel):
    note: str = ''


def _guard(fn, *args):
    try:
        return fn(*args)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:1500])
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Film not found')


@router.get("/engines")
def engines():
    return {'engines': agents.available(), 'sounds': catalogue()}


@router.post("")
def new_film(req: NewFilm):
    return _guard(films.create, req.url, req.prompt, req.aspect, req.engine, req.duration)


@router.get("")
def list_films():
    return {'films': films.list_films()}


@router.get("/{film_id}")
def film_status(film_id: str):
    state = _guard(films.status, film_id)
    if not state: raise HTTPException(status_code=404, detail='Film not found')
    return state


@router.get("/{film_id}/film")
def get_film(film_id: str):
    film = _guard(films.get_film, film_id)
    if film is None: raise HTTPException(status_code=404, detail='This film has not been made yet')
    return film


@router.put("/{film_id}/film")
def put_film(film_id: str, film: dict[str, Any]):
    try:
        return films.put_film(film_id, film)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Film not found')
    except Exception as exc:  # Validation errors explain which field is wrong.
        raise HTTPException(status_code=400, detail=str(exc)[:1500])


@router.post("/{film_id}/remix")
def remix(film_id: str, req: Remix):
    return _guard(films.remix, film_id, req.instruction, req.engine)


@router.post("/{film_id}/versions")
def save_version(film_id: str, req: SaveVersion):
    return {'version': _guard(films.save_version, film_id, req.note)}


@router.get("/{film_id}/versions/{n}")
def get_version(film_id: str, n: int):
    data = _guard(films.get_version, film_id, n)
    if data is None: raise HTTPException(status_code=404, detail='Version not found')
    return data


@router.post("/{film_id}/versions/{n}/restore")
def restore(film_id: str, n: int):
    return _guard(films.restore, film_id, n)


@router.get("/{film_id}/player", response_class=HTMLResponse)
def player(film_id: str, version: Optional[int] = None):
    try:
        return HTMLResponse(films.player(film_id, version), headers={'Cache-Control': 'no-store'})
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail='Film not found')


@router.get("/{film_id}/assets")
def list_assets(film_id: str):
    return {'assets': _guard(films.assets, film_id)}


@router.get("/{film_id}/assets/{name:path}")
def asset(film_id: str, name: str):
    path = _guard(films.asset, film_id, 'assets/' + name)
    if not path: raise HTTPException(status_code=404, detail='Asset not found')
    return FileResponse(path)


@router.post("/{film_id}/render")
def render(film_id: str):
    return _guard(films.render, film_id)


@router.get("/{film_id}/video")
def video(film_id: str):
    path = _guard(films.video_path, film_id)
    if not path: raise HTTPException(status_code=404, detail='Not rendered yet')
    return FileResponse(path, media_type='video/mp4', filename=f'{film_id}.mp4')
