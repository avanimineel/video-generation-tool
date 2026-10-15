from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.services.fusion_templates import fusion_generator
from app.services.project_manager import project_manager
from app.services.dynamic_graphics_service import dynamic_graphics_service
from app.core.models import CaptionStyle

router = APIRouter(prefix="/api/graphics", tags=["graphics"])

class SuggestGraphicRequest(BaseModel):
    selected_text: str

class GenerateCompRequest(BaseModel):
    template_id: str
    params: Dict[str, Any]
    duration_frames: int = 90

class AnalyzeBeatsRequest(BaseModel):
    max_pct: Optional[float] = 25.0
    category: Optional[str] = None
    min_support: Optional[int] = 2

@router.get("/templates")
async def list_templates():
    return {'templates': fusion_generator.get_template_catalog()}

@router.get("/dynamic-samples/{project_id}")
async def get_dynamic_samples(project_id: str, max_pct: float = 25.0, category: Optional[str] = None):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = dynamic_graphics_service.generate_dynamic_samples_for_project(
        captions=project.captions,
        fps=project.fps or 30.0,
        category_override=category,
        max_pct=max_pct
    )
    return result

@router.post("/analyze-beats/{project_id}")
async def analyze_project_beats(project_id: str, req: AnalyzeBeatsRequest):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = dynamic_graphics_service.generate_dynamic_samples_for_project(
        captions=project.captions,
        fps=project.fps or 30.0,
        category_override=req.category,
        max_pct=req.max_pct or 25.0,
        min_support=req.min_support or 2
    )
    return result

@router.get("/category-patterns")
async def get_category_patterns(category: str = "healthcare", min_support: int = 2):
    return dynamic_graphics_service.pattern_extractor.extract_patterns(
        category=category,
        min_support=min_support
    )

@router.post("/suggest")
async def suggest_graphics(req: SuggestGraphicRequest):
    text_lower = req.selected_text.lower()
    suggestions = []

    # 1. Number / Metric detection
    if any(k in text_lower for k in ['million', 'crore', '$', 'percent', '%', 'grow', 'revenue', 'scale']):
        suggestions.append({
            'template_id': 'stat_counter',
            'title': 'Animated Metric Count-Up',
            'preview_text': 'M → M (+500%)',
            'params': {
                'start_value': 'M',
                'end_value': 'M',
                'sub_badge': '+500% Revenue',
                'badge_color': '#CCFF00',
                'duration_sec': 2.5
            }
        })

    # 2. Emotional / Metaphor detection
    if any(k in text_lower for k in ['felt like', 'world', 'shift', 'ground', 'feet', 'falling', 'running']):
        suggestions.append({
            'template_id': 'silhouette_curve',
            'title': '2.5D Silhouette & Curved Arc Text',
            'preview_text': 'It felt like / under my feet',
            'params': {
                'arc_text_top': 'It felt like',
                'arc_text_bottom': 'under my feet',
                'bg_color': '#B4F000',
                'silhouette_color': '#000000',
                'curve_angle': 25
            }
        })

    # 3. Always provide High-Impact Kinetic Typography (as seen in screenshots)
    words = req.selected_text.split()
    headline = " ".join(words[:2]) if len(words) >= 2 else req.selected_text
    punchline = " ".join(words[2:]) if len(words) > 2 else ""

    suggestions.append({
        'template_id': 'kinetic_typography',
        'title': 'Kinetic Serif + Sans Typography',
        'preview_text': f'{headline} {punchline}',
        'params': {
            'headline': headline or 'Back then',
            'accent_word': 'I had',
            'punchline': punchline or 'no idea.',
            'primary_color': '#FFFFFF',
            'accent_color': '#CCFF00',
            'font_serif': 'Playfair Display',
            'font_sans': 'Montserrat'
        }
    })

    return {'suggestions': suggestions}

@router.post("/generate-comp")
async def generate_fusion_comp(req: GenerateCompRequest):
    comp_code = fusion_generator.generate_motion_graphic_comp(
        template_id=req.template_id,
        params=req.params,
        duration_frames=req.duration_frames
    )
    return {'fusion_comp_code': comp_code}

