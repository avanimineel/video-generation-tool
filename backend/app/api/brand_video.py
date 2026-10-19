from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.brand_video import jobs

router = APIRouter(prefix="/api/brand-video", tags=["brand-video"])


class BrandFilmRequest(BaseModel):
    url: str
    aspect: str = '16:9'


@router.post("")
def create_brand_film(req: BrandFilmRequest):
    try:
        return jobs.start(req.url, req.aspect)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
def list_brand_films():
    return {'films': jobs.list_films()}


@router.get("/{film_id}")
def brand_film_status(film_id: str):
    try:
        state = jobs.status(film_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not state: raise HTTPException(status_code=404, detail='Brand film not found')
    return state


@router.get("/{film_id}/film")
def brand_film_file(film_id: str):
    try:
        path = jobs.film_path(film_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not path: raise HTTPException(status_code=404, detail='Film not ready')
    return FileResponse(path, media_type='video/mp4', filename=f'{film_id}.mp4')
