from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.translation_service import translation_service
from app.services.translation_training import load_accepted_pairs, promote_chosen_line, run_training, training_status

router = APIRouter(prefix="/api/training", tags=["training"])


class ChoiceRequest(BaseModel):
    source_text: str = ""
    english: str = ""
    domain: str = "general"
    earlier_lines: list[str] = []


class ChooseRequest(BaseModel):
    source_text: str
    english: str
    domain: str = "general"
    project_id: str = ""
    start_sec: float = 0
    end_sec: float = 0


class SectionNoteRequest(BaseModel):
    source_text: str = ""
    english: str = ""
    domain: str = "general"
    earlier_lines: list[str] = []


class KeepSectionNoteRequest(BaseModel):
    project_id: str
    caption_id: str = ""
    source_text: str = ""
    spoken_text: str = ""
    note: str
    start_sec: float = 0
    end_sec: float = 0


@router.get("")
def get_training_status():
    return training_status()


@router.post("/choices")
def caption_choices(req: ChoiceRequest):
    return {"options": translation_service.caption_choices(req.source_text, req.english, req.domain, req.earlier_lines)}


@router.post("/section-note")
def suggest_section_note(req: SectionNoteRequest):
    try:
        note = translation_service.suggest_section_note(
            req.source_text,
            req.english,
            domain=req.domain,
            earlier_lines=req.earlier_lines,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"note": note}


@router.post("/section-note/keep")
def keep_section_note(req: KeepSectionNoteRequest):
    from app.services.caption_mappings import save_section_note
    try:
        example = save_section_note(req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "note": example.get("note") or ""}


@router.post("/choose")
def choose_line(req: ChooseRequest):
    taught = promote_chosen_line(
        req.source_text,
        req.english,
        domain=req.domain,
        project_id=req.project_id,
        start_sec=req.start_sec,
        end_sec=req.end_sec,
    )
    return {
        "taught": taught,
        "detail": "This section was saved for new videos." if taught else "This wording stays on the video only. It was not taught because it misses the medical meaning.",
    }


@router.post("/run")
def run_training_job():
    report = run_training(load_accepted_pairs())
    return {
        "promoted": report.promoted,
        "reason": report.reason,
        "accepted_pairs": report.accepted_pairs,
        "train_count": report.train_count,
        "holdout_count": report.holdout_count,
        "baseline_errors": report.baseline_errors,
        "candidate_errors": report.candidate_errors,
        "promoted_pairs": report.promoted_pairs,
    }
