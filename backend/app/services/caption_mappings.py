"""Editor examples that tie a spoken line to a range on the video timeline.

These examples are prompt context for the next transcription and editorial pass.
They do not change model weights.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from app.core.config import settings

_GLOBAL_NAME = "caption_timeline_examples.json"
_MAX_PROJECT = 200
_MAX_GLOBAL = 40


def _project_path(project_id: str):
    return settings.projects_dir / project_id / "transcription" / "caption_mappings.json"


def _global_path():
    return settings.projects_dir / _GLOBAL_NAME


def _read(path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _write(path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def list_mappings(project_id: str) -> List[Dict[str, Any]]:
    return _read(_project_path(project_id))


def save_mapping(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Replace the example for this caption, or append one when the caption is new."""
    project_id = str(entry.get("project_id") or "").strip()
    spoken = str(entry.get("spoken_text") or "").strip()
    if not project_id:
        raise ValueError("A caption mapping needs a project.")
    if not spoken:
        raise ValueError("A caption mapping needs the spoken line.")
    start = float(entry.get("start_sec") or 0)
    end = float(entry.get("end_sec") or 0)
    if end <= start:
        raise ValueError("The caption end time has to be after the start time.")
    example = {
        "project_id": project_id,
        "caption_id": str(entry.get("caption_id") or ""),
        "start_sec": round(start, 3),
        "end_sec": round(end, 3),
        "source_text": str(entry.get("source_text") or "").strip()[:500],
        "spoken_text": spoken[:500],
        "note": str(entry.get("note") or "").strip()[:240],
        "at": datetime.utcnow().isoformat(),
    }
    rows = _read(_project_path(project_id))
    caption_id = example["caption_id"]
    replaced = False
    if caption_id:
        for index, row in enumerate(rows):
            if row.get("caption_id") == caption_id:
                rows[index] = example
                replaced = True
                break
    if not replaced:
        rows.insert(0, example)
    _write(_project_path(project_id), rows[:_MAX_PROJECT])

    source = example["source_text"]
    from app.services.translation_service import translation_service
    if (
        translation_service.is_devanagari(source)
        and not translation_service.is_devanagari(example["spoken_text"])
        and not translation_service.medical_english_is_unusable(source, example["spoken_text"])
    ):
        from app.services.accepted_pairs import record_accepted_pair
        record_accepted_pair(
            source,
            example["spoken_text"],
            project_id=project_id,
            start_sec=example["start_sec"],
            end_sec=example["end_sec"],
            origin="editor",
        )

    shared = _read(_global_path())
    shared.insert(0, example)
    _write(_global_path(), shared[:_MAX_GLOBAL])
    return example


def save_section_note(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Keep an editor note for the next similar section. This does not teach the English on the line."""
    project_id = str(entry.get("project_id") or "").strip()
    note = " ".join(str(entry.get("note") or "").split())[:240]
    if not project_id:
        raise ValueError("A section note needs a project.")
    if not note:
        raise ValueError("A section note needs some text.")
    start = float(entry.get("start_sec") or 0)
    end = float(entry.get("end_sec") or 0)
    example = {
        "project_id": project_id,
        "caption_id": str(entry.get("caption_id") or ""),
        "start_sec": round(start, 3),
        "end_sec": round(end, 3),
        "source_text": str(entry.get("source_text") or "").strip()[:500],
        "spoken_text": str(entry.get("spoken_text") or "").strip()[:500],
        "note": note,
        "at": datetime.utcnow().isoformat(),
    }
    rows = _read(_project_path(project_id))
    caption_id = example["caption_id"]
    replaced = False
    if caption_id:
        for index, row in enumerate(rows):
            if row.get("caption_id") == caption_id:
                row = dict(row)
                row["note"] = note
                row["at"] = example["at"]
                if example["source_text"]:
                    row["source_text"] = example["source_text"]
                rows[index] = row
                example = row
                replaced = True
                break
    if not replaced:
        rows.insert(0, example)
    _write(_project_path(project_id), rows[:_MAX_PROJECT])
    shared = [row for row in _read(_global_path()) if row.get("note") != note or row.get("caption_id") != caption_id]
    shared.insert(0, example)
    _write(_global_path(), shared[:_MAX_GLOBAL])
    return example


def recent_section_notes(limit: int = 3) -> List[str]:
    notes: List[str] = []
    for row in _read(_global_path()):
        note = " ".join(str(row.get("note") or "").split())
        if note and note not in notes:
            notes.append(note)
        if len(notes) >= limit:
            break
    return notes


def section_note_guidance(limit: int = 3) -> str:
    notes = recent_section_notes(limit)
    if not notes:
        return ""
    return (
        "Editor notes for a similar section: "
        + " | ".join(notes)
        + ". Follow a note when the spoken line is the same kind of claim. "
    )


def transcription_prompt(base: str) -> str:
    """Append a few corrected lines so the next speech pass can prefer them."""
    rows = _read(_global_path())[:3]
    if not rows:
        return base
    pieces = []
    for row in rows:
        spoken = " ".join(str(row.get("spoken_text") or "").split())
        if not spoken:
            continue
        pieces.append(f"{row.get('start_sec')}-{row.get('end_sec')}s: {spoken[:80]}")
    if not pieces:
        return base
    return base + " Editor-corrected lines to prefer when the audio matches: " + " | ".join(pieces)
