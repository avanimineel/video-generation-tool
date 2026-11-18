"""Local editorial path used when Gemini or Twelve Labs reject a key.

Order is Gemini, then in-process Qwen, then LOCAL_PLANNER_URL,
then a deterministic planner that needs no GPU. Shot cuts come from ffmpeg.
YOLO11n, Florence-2, and SigLIP live in local_models and stay empty when a weight fails to load.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import requests

from app.core.config import settings
from app.services.editorial_planner import Decision, Scores, verbatim_text, weak_title

_AUTH = {401, 403}


def note_provider_failure(provider: str, status: int) -> None:
    if status not in _AUTH:
        return
    health = _load()
    health[provider] = {"status": status, "degraded": True}
    _save(health)


def provider_degraded(provider: str) -> bool:
    return bool(_load().get(provider, {}).get("degraded"))


def clear_provider(provider: str) -> None:
    health = _load()
    health.pop(provider, None)
    _save(health)


def local_planner_configured() -> bool:
    return bool(os.getenv("LOCAL_PLANNER_URL", "").strip())


def local_llm_json(prompt: str, schema: Optional[dict] = None) -> Optional[dict]:
    """OpenAI-compatible JSON call. A missing server returns None."""
    url = os.getenv("LOCAL_PLANNER_URL", "").strip()
    if not url:
        return None
    body = {
        "model": os.getenv("LOCAL_PLANNER_MODEL", "qwen2.5"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "editorial_plan", "schema": schema}}
    try:
        response = requests.post(url, json=body, timeout=(5, 90))
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or payload.get("content")
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return None
    return None


def deterministic_decisions(segments) -> list:
    """One spoken title on a number or a substantive phrase. No stock search."""
    decisions = []
    for segment in segments:
        choices = _cues(segment)
        if not choices:
            decisions.append(_quiet(segment, "No number or substantive spoken phrase in this stretch."))
            continue
        for cue in choices:
            decisions.append(_title(segment, cue))
    return decisions


def auth_failure(message: str) -> bool:
    text = message or ""
    return "401" in text or "403" in text or "degraded" in text.lower() or "API key not valid" in text or "api_key_invalid" in text


def _cues(segment) -> list[dict]:
    beats = list(getattr(segment, "dialogue_beats", None) or [])
    if not beats and getattr(segment, "transcript", ""):
        beats = [{"start_sec": segment.start_sec, "end_sec": segment.end_sec, "text": segment.transcript}]
    spoken = getattr(segment, "transcript", "") or ""
    chosen = []
    last_end = segment.start_sec
    for beat in beats:
        text = str(beat.get("text") or "").strip()
        if not text or weak_title(text) or not verbatim_text(text, spoken):
            continue
        start = max(float(beat.get("start_sec") or segment.start_sec), last_end)
        end = min(float(beat.get("end_sec") or start + 1.6), segment.end_sec)
        if end < start + 1.0:
            end = min(segment.end_sec, start + 1.2)
        if end <= start or start >= segment.end_sec:
            continue
        if chosen and start < last_end:
            continue
        number = bool(re.search(r"\d", text))
        emphasized = str(beat.get("emphasis") or "") == "high"
        if not number and not emphasized and len(text.split()) < 3:
            continue
        if chosen and start - chosen[-1]["start_sec"] < 4.0 and not number:
            continue
        anchor_id, anchor_word = _anchor(segment, start)
        chosen.append({
            "text": text,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "strategy": "STAT_COUNTER" if number else "KINETIC_TYPOGRAPHY",
            "cue_kind": "number" if number else "phrase",
            "intent": "QUANTIFY" if number else "EMPHASIZE",
            "audio_anchor_id": anchor_id,
            "audio_anchor_word": anchor_word,
        })
        last_end = end
        if len(chosen) >= 2:
            break
    return chosen


def _anchor(segment, start: float):
    cues = [word for word in (getattr(segment, "audio_cues", None) or []) if word.get("usable") and word.get("word")]
    if not cues:
        return None, ""
    nearest = min(cues, key=lambda word: abs(float(word.get("start") or 0) - start))
    return nearest.get("id"), str(nearest.get("word") or "")


def _scores() -> Scores:
    return Scores(**{name: (0.2 if name in ("redundancy", "visual_fatigue") else 0.55) for name in Scores.model_fields})


def _quiet(segment, reason: str) -> Decision:
    return Decision(
        segment_id=segment.id,
        intervene=False,
        rationale=reason,
        strategy="NO_INTERVENTION",
        start_sec=segment.start_sec,
        end_sec=segment.end_sec,
        scores=_scores(),
    )


def _title(segment, cue: dict) -> Decision:
    return Decision(
        segment_id=segment.id,
        intervene=True,
        rationale="Local planner. Spoken text placed because the cloud planner is unavailable.",
        intent=cue["intent"],
        strategy=cue["strategy"],
        anchor_phrase=cue["text"],
        audio_anchor_id=cue.get("audio_anchor_id"),
        audio_anchor_word=cue.get("audio_anchor_word") or "",
        cue_kind=cue["cue_kind"],
        start_sec=cue["start_sec"],
        end_sec=cue["end_sec"],
        display_text=cue["text"],
        visual_role="emphasis",
        scores=_scores(),
        composition={"layout": "text_overlay", "position": [0.5, 0.32]},
    )


def _path():
    return settings.projects_dir / "provider_health.json"


def _load() -> dict:
    path = _path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(health: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(health, indent=2), encoding="utf-8")
    temporary.replace(path)
