from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.services.article_scraper_service import article_scraper_service, ARTICLE_PRESETS

router = APIRouter(prefix="/api/article", tags=["article"])

class ParseArticleRequest(BaseModel):
    url: Optional[str] = None
    pasted_text: Optional[str] = None
    target_speech: Optional[str] = None
    preset_key: Optional[str] = None

@router.post("/parse")
async def parse_article_endpoint(req: ParseArticleRequest):
    try:
        data = article_scraper_service.parse_article(
            url=req.url,
            pasted_text=req.pasted_text,
            target_speech=req.target_speech,
            preset_key=req.preset_key
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/presets")
async def get_article_presets():
    return {
        "presets": [
            {
                "key": key,
                "publisher": val["publisher"],
                "headline": val["headline"],
                "highlight_quote": val["highlight_quote"],
                "marker_color": val["marker_color"]
            }
            for key, val in ARTICLE_PRESETS.items()
        ]
    }
