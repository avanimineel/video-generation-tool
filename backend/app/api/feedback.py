"""
Feedback & Training Data Endpoints
Allows editors to log Keep, Cut, or Swap decisions on AI suggestions,
query stats, and export few-shot training examples.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.services.feedback_service import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["Editor Feedback & AI Training"])

class DecisionLogRequest(BaseModel):
    project_id: str
    cue_id: str
    decision: str = Field(..., description="'keep' | 'cut' | 'swap'")
    reasoning: str = ""
    strength: float = 0.75
    graphic_type: str = "split_screen_vertical"
    start_sec: float = 0.0
    end_sec: float = 1.0
    search_query: str = ""
    transcript_context: str = ""
    selected_asset: Optional[Dict[str, Any]] = None
    swap_details: Optional[Dict[str, Any]] = None
    final_decision: Optional[Dict[str, Any]] = None
    editor_notes: str = ""

@router.post("/decisions")
async def log_editor_decision(req: DecisionLogRequest):
    if req.decision.lower() not in ["keep", "cut", "swap"]:
        raise HTTPException(status_code=400, detail="Decision must be 'keep', 'cut', or 'swap'")

    entry = feedback_service.record_decision(
        project_id=req.project_id,
        cue_id=req.cue_id,
        decision=req.decision,
        reasoning=req.reasoning,
        strength=req.strength,
        graphic_type=req.graphic_type,
        start_sec=req.start_sec,
        end_sec=req.end_sec,
        search_query=req.search_query,
        transcript_context=req.transcript_context,
        selected_asset=req.selected_asset,
        swap_details=req.swap_details,
        final_decision=req.final_decision,
        editor_notes=req.editor_notes
    )
    return {"success": True, "decision": entry}

@router.get("/decisions")
async def get_editor_decisions(
    decision: Optional[str] = Query(None, description="'keep' | 'cut' | 'swap' | 'all'"),
    graphic_type: Optional[str] = Query(None, description="Filter by graphic type"),
    min_strength: Optional[float] = Query(None, description="Minimum confidence strength"),
    max_strength: Optional[float] = Query(None, description="Maximum confidence strength"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    return feedback_service.query_decisions(
        decision_filter=decision,
        graphic_type=graphic_type,
        min_strength=min_strength,
        max_strength=max_strength,
        project_id=project_id,
        limit=limit,
        offset=offset
    )

@router.get("/stats")
async def get_feedback_statistics(
    project_id: Optional[str] = Query(None, description="Project ID or 'all'")
):
    return feedback_service.get_statistics(project_id=project_id)

@router.get("/few-shot-export")
async def export_few_shot_prompt_examples(
    decision_ids: Optional[str] = Query(None, description="Comma-separated decision IDs, or omit for all")
):
    ids_list = [i.strip() for i in decision_ids.split(",") if i.strip()] if decision_ids else None
    return feedback_service.generate_few_shot_export(decision_ids=ids_list)

class GuidanceRequest(BaseModel):
    project_id: str = "global"
    guidance: str = ""

@router.post("/guidance")
async def save_editorial_guidance(req: GuidanceRequest):
    return {"success": True, "data": feedback_service.save_guidance(req.project_id, req.guidance)}

@router.get("/guidance")
async def get_editorial_guidance(project_id: str = Query("global")):
    return {"success": True, "guidance": feedback_service.get_guidance(project_id)}

