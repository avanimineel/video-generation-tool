"""Ordered production stages and where a run is allowed to start.

Captions and translation stay in place until the editor starts at that stage
or earlier. Starting at a stage reruns it and every stage after it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

STAGE_ORDER = ("captions", "translation", "understanding", "plan", "pictures", "timeline")

STAGE_LABELS = {
    "captions": "Captions",
    "translation": "Translation",
    "understanding": "Video understanding",
    "plan": "Visual plan",
    "pictures": "Pictures",
    "timeline": "Timeline",
}

STAGE_DETAILS = {
    "captions": "Spoken lines and word timings from the audio.",
    "translation": "English lines on the same timings.",
    "understanding": "What is on screen. Skipped when Twelve Labs is not set, and the spoken lines are used instead.",
    "plan": "One visual brief for each spoken beat.",
    "pictures": "Stock that matched the brief, or the reason a picture was not used.",
    "timeline": "Titles and pictures placed on the spoken word.",
}

CONTINUE_LABELS = {
    "captions": "Start from captions",
    "translation": "Continue from translation",
    "understanding": "Continue from video understanding",
    "plan": "Continue from the visual plan",
    "pictures": "Continue from pictures",
    "timeline": "Continue from the timeline",
}

_ALIASES = {
    "transcription": "captions",
    "caption": "captions",
    "translate": "translation",
    "video_understanding": "understanding",
    "editorial": "plan",
    "editorial_planning": "plan",
    "asset_review": "pictures",
    "assets": "pictures",
    "placement": "timeline",
}


def normalize_from_stage(value: Optional[str]) -> Optional[str]:
    if value is None or not str(value).strip():
        return None
    key = str(value).strip().lower().replace("-", "_")
    key = _ALIASES.get(key, key)
    return key if key in STAGE_ORDER else None


def _devanagari(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097f" for ch in text or "")


def _line_ready(caption) -> bool:
    english = (getattr(caption, "translated_text", "") or "").strip()
    source = (getattr(caption, "text", "") or "").strip()
    if _devanagari(source):
        return bool(english) and not _devanagari(english)
    return bool(english or source)


def _fingerprint(rows: List[Dict[str, Any]]) -> str:
    brief = [
        (round(float(row.get("start_sec", row.get("start", 0))), 2),
         round(float(row.get("end_sec", row.get("end", 0))), 2),
         (row.get("text") or row.get("translated_text") or "").strip())
        for row in rows
    ]
    return json.dumps(brief, ensure_ascii=False)


def _caption_rows(captions) -> List[Dict[str, Any]]:
    return [
        {"start_sec": c.start, "end_sec": c.end, "text": (c.translated_text or c.text or "").strip()}
        for c in captions
    ]


def _latest_file(editorial: Path, name: str) -> Optional[Path]:
    if not editorial.is_dir():
        return None
    found = sorted(editorial.glob("*/" + name))
    return found[-1] if found else None


def _read_json(path: Optional[Path]):
    if path is None or not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def pipeline_status(state, projects_dir: Path) -> Dict[str, Any]:
    """Describe each stage from the files and captions already saved."""
    captions = list(getattr(state, "captions", []) or [])
    editorial = Path(projects_dir) / state.id / "editorial"
    latest = _read_json(editorial / "latest.json") or {}
    decisions = latest.get("decisions") or []
    score = latest.get("scorecard") or {}
    saved_transcript = _read_json(_latest_file(editorial, "00_transcript.json"))
    current = _fingerprint(_caption_rows(captions))
    if isinstance(saved_transcript, list):
        visuals_fresh = _fingerprint(saved_transcript) == current
    else:
        visuals_fresh = True

    captions_done = bool(captions)
    translation_done = captions_done and all(_line_ready(c) for c in captions)
    has_understanding = bool(_latest_file(editorial, "01_semantic_timeline.json") or _latest_file(editorial, "01_understanding_raw.json"))
    has_plan = bool(decisions) or bool(_latest_file(editorial, "03_schedule.json") or _latest_file(editorial, "02_editorial_decisions.json"))
    has_pictures = bool(_latest_file(editorial, "04_asset_review.json")) or any(
        isinstance(row, dict) and row.get("status") in ("inserted", "rejected_assets") for row in decisions
    )
    has_timeline = bool(_latest_file(editorial, "06_timeline.json")) or any(
        isinstance(getattr(g, "parameters", None), dict) and g.parameters.get("editorial_generated")
        for g in (getattr(state, "graphics", []) or [])
    )
    if latest.get("outcome") == "captions_only" and not decisions and not has_plan:
        has_understanding = has_plan = has_pictures = has_timeline = False

    def visual(present: bool) -> str:
        if not captions_done or not translation_done:
            return "not_run"
        if not present:
            return "not_run"
        return "done" if visuals_fresh else "out_of_date"

    states = {
        "captions": "done" if captions_done else "not_run",
        "translation": "done" if translation_done else ("not_run" if captions_done else "not_run"),
        "understanding": visual(has_understanding),
        "plan": visual(has_plan),
        "pictures": visual(has_pictures),
        "timeline": visual(has_timeline),
    }
    if captions_done and not translation_done:
        states["translation"] = "not_run"

    english_count = sum(1 for c in captions if _line_ready(c) and not _devanagari(c.translated_text or c.text or ""))
    summaries = {
        "captions": f"{len(captions)} spoken lines" if captions_done else "Not created yet",
        "translation": f"{english_count} English lines" if translation_done else "Not written yet",
        "understanding": "Saved from this video" if states["understanding"] == "done" else "Not done for these captions",
        "plan": f"{len(decisions)} beats in the last plan" if states["plan"] == "done" else "Not planned for these captions",
        "pictures": (
            f"{score.get('rejected_assets', 0)} pictures not used"
            if states["pictures"] == "done" and score.get("rejected_assets")
            else ("Pictures reviewed" if states["pictures"] == "done" else "Not searched for these captions")
        ),
        "timeline": (
            f"{score.get('inserted', latest.get('inserted', 0))} visuals on the timeline"
            if states["timeline"] == "done" else "Not placed for these captions"
        ),
    }
    if states["understanding"] == "out_of_date":
        summaries["understanding"] = "Out of date because the captions changed"

    next_stage = next((stage for stage in STAGE_ORDER if states[stage] in ("not_run", "out_of_date")), None)
    stages = [
        {
            "id": stage,
            "label": STAGE_LABELS[stage],
            "detail": STAGE_DETAILS[stage],
            "state": "next" if stage == next_stage else states[stage],
            "summary": summaries[stage],
            "replace_note": _replace_note(stage, len(captions), english_count, score.get("inserted", latest.get("inserted", 0))),
        }
        for stage in STAGE_ORDER
    ]
    return {
        "stages": stages,
        "next_stage": next_stage,
        "continue_label": CONTINUE_LABELS.get(next_stage, "Timeline is ready"),
        "continue_note": _continue_note(next_stage, len(captions), english_count),
    }


def _continue_note(stage: Optional[str], captions: int, english: int) -> str:
    if stage in (None,):
        return "The visual timeline is ready. Run again from a stage when you want that step replaced."
    if stage == "captions":
        return "Captions are created from the audio, then translation and the visual timeline."
    if stage == "translation":
        return "Spoken timings stay. English lines are written again, then the visual timeline."
    if stage == "pictures":
        return f"{captions} captions and {english} English lines stay. Pictures and the timeline are searched again."
    if stage == "timeline":
        return f"{captions} captions, {english} English lines, and the visual plan stay. The timeline is placed again."
    return f"{captions} captions and {english} English lines stay. Planning and pictures run again."


def _replace_note(stage: str, captions: int, english: int, inserted: int) -> str:
    if stage == "captions":
        return f"The current {english} English lines, visual plan, and {inserted} timeline visuals will be replaced. Spoken timings are created again from the audio."
    if stage == "translation":
        return f"The {captions} spoken timings stay. English lines, the visual plan, and timeline visuals are written again."
    if stage == "understanding":
        return f"The {captions} captions and {english} English lines stay. Video understanding, the plan, pictures, and timeline are created again."
    if stage == "plan":
        return f"The {captions} captions and {english} English lines stay. The visual plan, pictures, and timeline are created again."
    if stage == "pictures":
        return "The visual plan stays. Pictures are searched again and the timeline is placed again."
    return "The plan and the chosen pictures stay. The timeline overlays are placed again."
