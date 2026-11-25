"""Short-form agents that run after captions and again after the visual plan.

The words stay the spoken captions. Viral inferences only name patterns already in those
lines. A later agent may drop an overlay. It may not invent a sentence, a number, or a place.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

VIRAL_PATTERNS = (
    ("specific_number", re.compile(r"\d")),
    ("open_question", re.compile(r"\?")),
    ("contrast", re.compile(r"\b(but|not|only|never|without|instead)\b", re.I)),
    ("direct_address", re.compile(r"\b(you|your)\b", re.I)),
    ("stakes", re.compile(r"\b(stop|avoid|save[ds]?|lose|win|risk|free|now|secret)\b", re.I)),
)

MOOD_WORDS = {
    "win": re.compile(r"\b(win|launch|result|saved|success|congrats)\b", re.I),
    "effort": re.compile(r"\b(train|workout|push|heavy|hard|sweat|effort)\b", re.I),
    "weather": re.compile(r"\b(rain|storm|thunder|lightning|weather)\b", re.I),
    "digital": re.compile(r"\b(app|software|glitch|bug|code|online|digital)\b", re.I),
    "future": re.compile(r"\b(future|space|science|universe|planet)\b", re.I),
    "document": re.compile(r"\b(report|letter|bill|contract|document)\b", re.I),
}

EFFECT_MOOD = {
    "confetti": {"win"},
    "fog": {"effort"},
    "storm": {"weather"},
    "glitch": {"digital"},
    "space": {"future"},
    "light_leak": {"story", "place"},
}

PACK_BY_DOMAIN = {
    "finance": "direct_response",
    "business": "direct_response",
    "fitness": "direct_response",
    "medical": "documentary",
    "legal": "documentary",
    "education": "documentary",
    "real_estate": "documentary",
    "sports": "direct_response",
    "general": "explainer",
}

GAP_SECONDS = 0.7
MAX_PUNCH_PER_30S = 8


def _text(caption) -> str:
    translated = str(getattr(caption, "translated_text", "") or "").strip()
    spoken = str(getattr(caption, "text", "") or "").strip()
    if translated and spoken and translated.casefold() != spoken.casefold():
        return translated
    return translated or spoken


def viral_hits(text: str) -> list:
    return [name for name, pattern in VIRAL_PATTERNS if pattern.search(text or "")]


def moods_in(text: str) -> set:
    return {name for name, pattern in MOOD_WORDS.items() if pattern.search(text or "")}


def tag_intent(text: str, index: int, total: int, start: float) -> str:
    hits = set(viral_hits(text))
    if index == 0 or start < 3.0:
        return "hook"
    if "specific_number" in hits or "contrast" in hits:
        return "claim"
    if re.search(r"\b(because|study|shown|data|proof|percent)\b", text or "", re.I):
        return "proof"
    if total > 1 and index >= total - 1:
        return "cta"
    if re.search(r"\b(start|follow|click|join|subscribe|download)\b", text or "", re.I):
        return "cta"
    return "story"


def style_pack(domain: str | None) -> str:
    key = (domain or "general").strip().lower().replace(" ", "_").replace("-", "_")
    return PACK_BY_DOMAIN.get(key, "explainer")


def build_story(captions) -> dict:
    """Arrange the spoken lines into a hook, claim, proof, story, and CTA. Copy stays verbatim."""
    rows = []
    total = len(captions or [])
    for index, caption in enumerate(captions or []):
        text = _text(caption)
        if not text:
            continue
        start = float(getattr(caption, "start", 0) or 0)
        hits = viral_hits(text)
        score = len(hits) * 2 + (2 if start < 3 else 0)
        rows.append({
            "index": index,
            "start": start,
            "end": float(getattr(caption, "end", start) or start),
            "text": text,
            "intent": tag_intent(text, index, total, start),
            "viral": hits,
            "moods": sorted(moods_in(text)),
            "score": score,
        })
    if not rows:
        return {"spine": {}, "lines": [], "inferences": [], "viral_score": 0}
    opening = [row for row in rows if row["start"] < 5] or rows[:1]
    hook = max(opening, key=lambda row: (row["score"], -row["start"]))
    later = [row for row in rows if row["index"] != hook["index"]]
    claim = next((row for row in later if row["intent"] == "claim"), None)
    proof = next((row for row in later if row["intent"] == "proof" and row is not claim), None)
    cta = next((row for row in reversed(rows) if row["intent"] == "cta" and row is not hook), None)
    used = {id(item) for item in (hook, claim, proof, cta) if item}
    story = next((row for row in rows if id(row) not in used and row["intent"] == "story"), None)
    spine = {
        "hook": hook["text"],
        "claim": claim["text"] if claim else "",
        "proof": proof["text"] if proof else "",
        "story": story["text"] if story else "",
        "cta": cta["text"] if cta else "",
    }
    inferences = []
    for row in rows:
        if row["viral"]:
            inferences.append({
                "start": row["start"],
                "text": row["text"],
                "patterns": row["viral"],
                "why": "Spoken line already contains " + ", ".join(row["viral"]) + ".",
            })
    if hook["score"] == 0:
        inferences.append({
            "start": hook["start"],
            "text": hook["text"],
            "patterns": [],
            "why": "Opening line has no number, question, contrast, or direct address. The hook stays this spoken line.",
        })
    return {
        "spine": spine,
        "lines": rows,
        "inferences": inferences,
        "viral_score": sum(row["score"] for row in rows),
    }


def _nearby_text(captions, start: float, end: float) -> str:
    parts = []
    for caption in captions or []:
        c_start = float(getattr(caption, "start", 0) or 0)
        c_end = float(getattr(caption, "end", c_start) or c_start)
        if c_start < end + 1 and c_end > start - 1:
            parts.append(_text(caption))
    return " ".join(parts)


def relevance_agent(graphics, captions, story):
    """Decorative effects stay only when the spoken mood supports them."""
    kept = []
    dropped = []
    lines = story.get("lines") or []
    for graphic in graphics:
        effect = (getattr(graphic, "parameters", None) or {}).get("effect")
        allowed = EFFECT_MOOD.get(effect)
        if getattr(graphic, "template_id", "") != "look_effect" or not allowed:
            kept.append(graphic)
            continue
        window = _nearby_text(captions, graphic.start, graphic.end)
        found = moods_in(window)
        nearby = [row for row in lines if row["start"] < graphic.end + 1 and row["end"] > graphic.start - 1]
        if "story" in allowed and any(row["intent"] == "story" for row in nearby):
            found.add("story")
        if "place" in allowed and re.search(r"\b(city|street|home|house|store|office)\b", window, re.I):
            found.add("place")
        if found & allowed:
            kept.append(graphic)
        else:
            dropped.append({"id": graphic.id, "effect": effect, "reason": "mood gate"})
    return kept, dropped


def _rank(graphic) -> int:
    template = getattr(graphic, "template_id", "")
    if template in ("kinetic_typography", "mixed_typography_title"):
        return 0
    if template in ("youtube_insert", "split_screen_vertical"):
        return 1
    if template == "source_reframe":
        return 2
    if template == "look_effect":
        return 4
    return 3


def density_agent(graphics):
    """Keep overlays at least 700 ms apart and punch-ins under 8 per 30 seconds."""
    ordered = sorted(graphics, key=lambda graphic: (float(graphic.start), _rank(graphic)))
    kept = []
    dropped = []
    for graphic in ordered:
        conflict = [other for other in kept if abs(float(graphic.start) - float(other.start)) < GAP_SECONDS]
        if not conflict:
            kept.append(graphic)
            continue
        worst = max(conflict, key=_rank)
        if _rank(graphic) < _rank(worst):
            kept.remove(worst)
            dropped.append({"id": worst.id, "reason": "700ms gap"})
            kept.append(graphic)
        else:
            dropped.append({"id": graphic.id, "reason": "700ms gap"})
    reframes = [graphic for graphic in kept if graphic.template_id == "source_reframe"]
    remove = set()
    for graphic in reframes:
        window = [item for item in reframes if graphic.start <= item.start < graphic.start + 30]
        if len(window) > MAX_PUNCH_PER_30S:
            extra = sorted(window, key=lambda item: item.start)[MAX_PUNCH_PER_30S:]
            remove.update(item.id for item in extra)
    if remove:
        dropped.extend({"id": item_id, "reason": "punch cap"} for item_id in remove)
        kept = [graphic for graphic in kept if graphic.id not in remove]
    return kept, dropped


def platform_agent(state):
    """Sit captions above the platform UI band. Do not print a live badge."""
    moved = 0
    for caption in getattr(state, "captions", None) or []:
        if float(getattr(caption, "pos_y", 0.82) or 0.82) >= 0.80:
            caption.pos_y = 0.76
            moved += 1
    return {"caption_band": 0.76, "captions_moved": moved, "live_badge": "omitted"}


def remotion_composition(state, graphics, story, pack: str) -> dict:
    duration = float(getattr(state, "duration_seconds", 0) or 0)
    if duration < 1 and graphics:
        duration = max(float(graphic.end) for graphic in graphics)
    if duration < 1 and state.captions:
        duration = max(float(getattr(caption, "end", 0) or 0) for caption in state.captions)
    duration = max(duration, 1.0)
    return {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "durationInFrames": int(round(duration * 30)),
        "stylePack": pack,
        "story": story.get("spine") or {},
        "tracks": [
            {
                "id": getattr(graphic, "id", ""),
                "template": getattr(graphic, "template_id", ""),
                "from": int(round(float(graphic.start) * 30)),
                "durationInFrames": max(1, int(round((float(graphic.end) - float(graphic.start)) * 30))),
                "effect": (getattr(graphic, "parameters", None) or {}).get("effect", ""),
                "title": getattr(graphic, "title", ""),
            }
            for graphic in graphics
        ],
    }


def acceptance(graphics, story) -> dict:
    starts = sorted(float(graphic.start) for graphic in graphics)
    gaps = [round(b - a, 3) for a, b in zip(starts, starts[1:])]
    punch = [graphic for graphic in graphics if getattr(graphic, "template_id", "") == "source_reframe"]
    return {
        "overlay_count": len(graphics),
        "min_gap_seconds": min(gaps) if gaps else None,
        "gap_ok": all(gap >= GAP_SECONDS - 0.001 for gap in gaps) if gaps else True,
        "punch_count": len(punch),
        "punch_ok": len(punch) <= MAX_PUNCH_PER_30S,
        "hook": (story.get("spine") or {}).get("hook", ""),
        "viral_score": story.get("viral_score", 0),
        "live_badge": "omitted",
    }


def run_shortform_agents(state, graphics=None, chosen=None, choice_made=False, run_dir=None):
    """Run brief, story, relevance, density, platform, remotion, and measure. Returns graphics, report."""
    graphics = list(graphics if graphics is not None else getattr(state, "graphics", []) or [])
    domain = getattr(getattr(state, "settings", None), "domain_profile", None)
    pack = style_pack(domain)
    story = build_story(getattr(state, "captions", None) or [])
    relevance_drops = []
    density_drops = []
    if choice_made:
        graphics, relevance_drops = relevance_agent(graphics, getattr(state, "captions", None) or [], story)
        graphics, density_drops = density_agent(graphics)
    platform = platform_agent(state)
    for graphic in graphics:
        params = getattr(graphic, "parameters", None)
        if isinstance(params, dict):
            params["style_pack"] = pack
            params["safe_top"] = 0.12
            params["safe_bottom"] = 0.18
    composition = remotion_composition(state, graphics, story, pack)
    checks = acceptance(graphics, story)
    report = {
        "agents": [
            "story",
            "brief",
            "relevance",
            "density",
            "platform",
            "remotion",
            "measure",
        ],
        "style_pack": pack,
        "story": story,
        "relevance_dropped": relevance_drops,
        "density_dropped": density_drops,
        "platform": platform,
        "remotion": {"fps": composition["fps"], "tracks": len(composition["tracks"])},
        "acceptance": checks,
        "chosen": list(chosen or []),
    }
    destination = None
    if run_dir is not None:
        destination = Path(run_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "08_shortform_agents.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        (destination / "remotion_composition.json").write_text(json.dumps(composition, ensure_ascii=False, indent=2))
        report["remotion"]["composition"] = str(destination / "remotion_composition.json")
    ingestion = dict(getattr(state, "ai_ingestion", None) or {})
    ingestion["shortform"] = {
        "style_pack": pack,
        "hook": (story.get("spine") or {}).get("hook", ""),
        "viral_score": story.get("viral_score", 0),
        "inferences": story.get("inferences") or [],
        "spine": story.get("spine") or {},
    }
    state.ai_ingestion = ingestion
    return graphics, report
