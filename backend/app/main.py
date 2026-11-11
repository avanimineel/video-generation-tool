from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.api.projects import router as projects_router
from app.api.media import router as media_router
from app.api.subtitles import router as subtitles_router
from app.api.graphics import router as graphics_router
from app.api.davinci import router as davinci_router
from app.api.articles import router as articles_router
from app.api.feedback import router as feedback_router
from app.api.brand_video import router as brand_video_router
from app.api.studio import router as studio_router
from app.api.music import router as music_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.logging_setup import configure_logging
    configure_logging()
    init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI-assisted video editing companion for DaVinci Resolve",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.services.project_manager import ProjectConflict
from fastapi.responses import JSONResponse

@app.exception_handler(ProjectConflict)
async def project_conflict(request, exc):
    return JSONResponse(status_code=409, content={'detail': str(exc)})

# Mount Routers
app.include_router(projects_router)
app.include_router(media_router)
app.include_router(subtitles_router)
app.include_router(graphics_router)
app.include_router(davinci_router)
app.include_router(articles_router)
app.include_router(feedback_router)
app.include_router(brand_video_router)
app.include_router(studio_router)
app.include_router(music_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.version,
        "projects_dir": str(settings.projects_dir)
    }

@app.get("/")
async def root():
    return {
        "message": "Resolve AI Companion Backend is running",
        "endpoints": [
            "/api/projects",
            "/api/media",
            "/api/subtitles",
            "/api/graphics",
            "/api/davinci"
        ]
    }
