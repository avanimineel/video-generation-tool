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
OPENING_SECONDS = 7.0
INTERRUPT_SECONDS = 6.0
SPEECH_LOOKS = ("camera", "paper", "film", "streaming", "flat_vector", "scrapbook", "flat_infographic", "paper_craft")
PAPER_SUBJECTS = (
    ("pill", re.compile(r"\b(pills?|medicines?|tablets?|doses?|capsules?)\b", re.I)),
    ("bill", re.compile(r"\b(bills?|money|rupees?|dollars?|prices?|costs?|fees?)\b", re.I)),
    ("book", re.compile(r"\b(books?|pages?|novels?)\b", re.I)),
    ("phone", re.compile(r"\b(phones?|mobiles?|apps?|screens?)\b", re.I)),
    ("house", re.compile(r"\b(houses?|homes?|rooms?|doors?)\b", re.I)),
    ("heart", re.compile(r"\b(hearts?)\b", re.I)),
    ("calendar", re.compile(r"\b(calendars?|dates?|appointments?|weeks?|months?)\b", re.I)),
    ("cup", re.compile(r"\b(cups?|tea|coffee|water|glasses?)\b", re.I)),
)


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


def build_story(captions, beats=None) -> dict:
    """Arrange the spoken lines into a hook, claim, proof, story, and CTA. Copy stays verbatim.

    `beats` groups neighboring row indexes into one claim. The joined text is the
    spoken lines in order. Nothing is rewritten.
    """
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
    first = min(rows, key=lambda row: row["start"])
    if not first["viral"]:
        inferences.append({
            "start": first["start"],
            "text": first["text"],
            "patterns": [],
            "why": "Opening line has no number, question, contrast, or direct address. The picture uses the strongest spoken line inside the first 7 seconds.",
        })
    from app.services.local_story_models import beat_source, caption_beat_groups, normalize_groups
    groups = normalize_groups(len(rows), beats) if beats is not None else caption_beat_groups(rows)
    story_beats = []
    for group in groups:
        members = [rows[index] for index in group]
        story_beats.append({
            "start": members[0]["start"],
            "end": members[-1]["end"],
            "text": " ".join(member["text"] for member in members),
            "lines": [member["text"] for member in members],
            "caption_indexes": [member["index"] for member in members],
        })
        for member in members:
            member["beat"] = members[0]["index"]
    return {
        "spine": spine,
        "lines": rows,
        "beats": story_beats,
        "beat_source": "given" if beats is not None else beat_source(),
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
    glitches = [graphic for graphic in kept if (getattr(graphic, "parameters", None) or {}).get("effect") == "glitch"]
    extra_glitch = set()
    for graphic in glitches:
        window = [item for item in glitches if graphic.start <= item.start < graphic.start + 15]
        if len(window) > 2:
            extra_glitch.update(item.id for item in sorted(window, key=lambda item: item.start)[2:])
    if extra_glitch:
        dropped.extend({"id": item_id, "reason": "glitch cap"} for item_id in extra_glitch)
        kept = [graphic for graphic in kept if graphic.id not in extra_glitch]
    return kept, dropped


def _allowed(chosen, choice_made, key: str) -> bool:
    return bool(choice_made) and key in (chosen or [])


def _graphic(item_id, start, end, template, title, parameters):
    from app.core.models import MotionGraphicItem
    return MotionGraphicItem(id=item_id, start=round(start, 2), end=round(end, 2), template_id=template, title=title, parameters=parameters)


def caption_agent(state, chosen, choice_made):
    """Highlight the spoken word inside the existing clause. Do not recut the line into short boxes."""
    if not _allowed(chosen, choice_made, "kinetic_captions") and not _allowed(chosen, choice_made, "paper_purple"):
        return {"status": "waiting" if not choice_made else "off", "sync_ms": 80}
    changed = 0
    if _allowed(chosen, choice_made, "kinetic_captions"):
        for caption in getattr(state, "captions", None) or []:
            style = getattr(caption, "style", None)
            if style is None:
                continue
            style.has_highlight = True
            style.highlight_bounce = True
            color = str(getattr(getattr(state, "settings", None), "caption_highlight_color", "") or "#F5E642")
            style.highlight_active_color = color if color.startswith("#") and len(color) in (4, 7) else "#F5E642"
            style.highlight_scale = 1.08
            style.font_weight = "900"
            style.animation_type = "pop"
            changed += 1
    if _allowed(chosen, choice_made, "paper_purple"):
        from app.services.overlay_styles import apply_paper_purple_captions
        changed = apply_paper_purple_captions(state, chosen, choice_made)
        return {"status": "paper_purple", "captions": changed, "sync_ms": 80, "chunking": "spoken_clause"}
    return {"status": "highlight", "captions": changed, "sync_ms": 80, "chunking": "spoken_clause"}


def opening_target(story) -> dict:
    """The spoken line inside the first 7 seconds that should carry the opening picture."""
    lines = story.get("lines") or []
    if not lines:
        return {"weak": False, "text": "", "start": None}
    first = min(lines, key=lambda row: row["start"])
    window = [row for row in lines if row["start"] < OPENING_SECONDS] or [first]
    best = max(window, key=lambda row: (len(row["viral"]), row["score"], -row["start"]))
    return {
        "weak": not first["viral"],
        "text": best["text"],
        "start": best["start"],
        "index": best["index"],
        "first": first["text"],
        "first_index": first["index"],
    }


def _speaker_focus(state, moment: float) -> float:
    """Vertical centre of the speaker's head, or the upper-third default when no face is measured."""
    try:
        from app.services.subject_layers import speaker_head_band
        band = speaker_head_band(state, moment)
    except Exception:
        band = None
    if not band:
        return 0.35
    centre = (band[0] + band[1]) / 2
    if 0.15 <= centre <= 0.55:
        return round(centre, 3)
    return 0.35


def _zoom(state) -> float:
    try:
        scale = float(getattr(getattr(state, "settings", None), "punch_scale", 1.15) or 1.15)
    except (TypeError, ValueError):
        scale = 1.15
    return min(1.15, max(1.05, scale))


def emphasis_agent(state, graphics, story, chosen, choice_made):
    """Punch in on an emphasized spoken line, at least 3 seconds apart, at most 8 per 30 seconds."""
    graphics = [graphic for graphic in graphics if not ((getattr(graphic, "parameters", None) or {}).get("retention_camera"))]
    opening = opening_target(story)
    if _allowed(chosen, choice_made, "paper_purple"):
        return graphics, {"status": "locked", "added": 0, "opening": opening}
    if not _allowed(chosen, choice_made, "punch_in"):
        return graphics, {"status": "waiting" if not choice_made else "off", "added": 0, "opening": opening}
    added = []
    last = -10.0
    last_jump = -10.0
    focus_y = _speaker_focus(state, opening["start"] or 0)
    zoom = _zoom(state)
    for row in story.get("lines") or []:
        emphasized = row["intent"] in ("hook", "claim") or "specific_number" in row["viral"] or "contrast" in row["viral"]
        if opening["weak"] and row["index"] == opening["first_index"] and opening["index"] != row["index"]:
            emphasized = False
        if opening["weak"] and row["index"] == opening["index"] and row["score"] > 0:
            emphasized = True
        if not emphasized or row["start"] - last < 3:
            continue
        if sum(1 for item in added if row["start"] < item.start + 30) >= MAX_PUNCH_PER_30S:
            break
        jump = row["intent"] == "hook" and last > 0 and row["start"] - last_jump >= 8
        if jump:
            last_jump = row["start"]
        end = min(row["end"], row["start"] + 1.6)
        if end - row["start"] < 0.6:
            end = row["start"] + 1.2
        added.append(_graphic(
            f"emphasis_{len(added)}_{int(row['start'] * 100)}",
            row["start"],
            end,
            "source_reframe",
            "Jump cut" if jump else "Punch-in",
            {
                "editorial_generated": True,
                "retention_camera": True,
                "emphasis": True,
                "start_scale": 1.0,
                "end_scale": zoom,
                "motion_curve": "hold" if jump else "smoothstep",
                "easing": "easing.spring" if jump else "easing.bezier",
                "focus_x": 0.5,
                "focus_y": focus_y,
                "opening": bool(opening["weak"] and row["index"] == opening["index"]),
            },
        ))
        last = row["start"]
    return graphics + added, {"status": "placed", "added": len(added), "opening": opening, "focus_y": focus_y, "zoom": zoom}


def entity_agent(graphics, story, chosen, choice_made, product_note=""):
    """Call out a spoken number, place, or product. The on-screen text is copied from the line."""
    if not choice_made:
        return graphics, {"status": "waiting", "numbers": 0, "places": 0, "products": 0}
    number_pattern = re.compile(r"\d[\d,]*(?:\.\d+)?%?")
    place_pattern = re.compile(r"\bin\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b")
    counts = {"numbers": 0, "places": 0, "products": 0}

    def covered(start, end, entity):
        return any(
            (getattr(graphic, "parameters", None) or {}).get("entity") == entity
            and graphic.start < end and graphic.end > start
            for graphic in graphics
        )

    for row in story.get("lines") or []:
        cursor = row["start"]
        if any(getattr(graphic, "template_id", "") == "source_reframe" and abs(float(graphic.start) - cursor) < GAP_SECONDS for graphic in graphics):
            cursor += GAP_SECONDS
        if _allowed(chosen, choice_made, "data_callouts"):
            match = number_pattern.search(row["text"])
            if match and cursor + 0.8 <= row["end"] + 0.4 and not covered(row["start"], row["end"], "number"):
                token = match.group(0)
                graphics.append(_graphic(
                    f"entity_num_{counts['numbers']}_{int(cursor * 100)}",
                    cursor,
                    min(row["end"], cursor + 1.4),
                    "kinetic_typography",
                    token,
                    {"editorial_generated": True, "headline": token, "entity": "number", "title_style": "bold_pop"},
                ))
                counts["numbers"] += 1
                cursor += 0.7
        if _allowed(chosen, choice_made, "location_maps"):
            place = place_pattern.search(row["text"])
            if place and not covered(row["start"], row["end"], "place"):
                name = place.group(1)
                graphics.append(_graphic(
                    f"entity_place_{counts['places']}_{int(cursor * 100)}",
                    cursor,
                    min(row["end"], cursor + 1.4),
                    "kinetic_typography",
                    name,
                    {"editorial_generated": True, "headline": name, "entity": "place", "retrieval_query": f"aerial map of {name}"},
                ))
                counts["places"] += 1
                cursor += 0.7
        if _allowed(chosen, choice_made, "product_swap") and product_note and product_note.casefold() in row["text"].casefold():
            if not covered(row["start"], row["end"], ("youtube_insert", "split_screen_vertical", "kinetic_typography")):
                graphics.append(_graphic(
                    f"entity_product_{counts['products']}",
                    row["start"],
                    min(row["end"], row["start"] + 2.0),
                    "kinetic_typography",
                    product_note,
                    {"editorial_generated": True, "headline": product_note, "entity": "product", "retrieval_query": f"hand holding {product_note}"},
                ))
                counts["products"] += 1
    counts["status"] = "placed"
    return graphics, counts


def paper_subject(text: str) -> str:
    for name, pattern in PAPER_SUBJECTS:
        if pattern.search(text or ""):
            return name
    return ""


def paper_purple_agent(state, graphics, story, chosen, choice_made):
    """Draw a cream paper scene for a concrete spoken thing. The speaker stays for the other lines."""
    if not _allowed(chosen, choice_made, "paper_purple"):
        return graphics, {"status": "off", "scenes": 0, "badges": 0}
    base = [
        graphic for graphic in graphics
        if not (
            getattr(graphic, "template_id", "") == "look_effect"
            and (getattr(graphic, "parameters", None) or {}).get("effect") == "paper_purple"
        )
    ]
    lines = story.get("lines") or []
    duration = float(getattr(state, "duration_seconds", 0) or 0)
    if duration < 1 and lines:
        duration = max(float(row["end"]) for row in lines)
    duration = max(duration, 4.0)
    budget = duration * 0.75
    used = 0.0
    placed = []
    badge = False
    seen_scene = False
    last_end = -1.0
    for index, row in enumerate(lines):
        named = paper_subject(row["text"])
        opening = (not seen_scene) and (float(row["start"]) < 3.0 or index == 0)
        if opening or named:
            start = float(row["start"])
            if start < last_end:
                start = last_end
            end = min(float(row["end"]), start + 3.2)
            if end - start < 0.8:
                end = start + 1.2
            length = end - start
            if start >= float(row["end"]) - 0.3:
                continue
            if seen_scene and used + length > budget:
                continue
            placed.append(_graphic(
                f"paper_purple_{len(placed)}_{int(start * 100)}",
                start,
                end,
                "look_effect",
                "Paper purple",
                {
                    "editorial_generated": True,
                    "effect": "paper_purple",
                    "look_overlay": True,
                    "subject": named or "object",
                    "badge": False,
                    "scene_start": round(start, 2),
                    "scene_end": round(end, 2),
                    "transition": "cut",
                },
            ))
            used += length
            seen_scene = True
            last_end = end
            continue
        if seen_scene and not badge:
            start = float(row["start"])
            end = min(float(row["end"]), start + 1.2)
            if end - start < 0.6:
                end = start + 0.9
            placed.append(_graphic(
                f"paper_purple_badge_{int(start * 100)}",
                start,
                end,
                "look_effect",
                "Paper purple",
                {
                    "editorial_generated": True,
                    "effect": "paper_purple",
                    "look_overlay": True,
                    "subject": "badge",
                    "badge": True,
                    "scene_start": round(start, 2),
                    "scene_end": round(end, 2),
                    "transition": "cut",
                },
            ))
            badge = True
    full = [item for item in placed if not item.parameters.get("badge")]

    def _hits(graphic):
        return getattr(graphic, "template_id", "") == "look_effect" and any(_overlaps(graphic, item) for item in full)

    cleaned = [graphic for graphic in base if not _hits(graphic)]
    return cleaned + placed, {"status": "placed", "scenes": len(full), "badges": 1 if badge else 0}


def motion_agent(graphics):
    """Stamp easing, blend, and frame step. Paper craft steps at 12 fps. Scale stays 1.0 to 1.15."""
    blends = {"confetti": "screen", "fog": "screen", "light_leak": "screen", "storm": "screen", "glitch": "screen", "paper": "multiply", "film": "multiply", "paper_craft": "multiply", "scrapbook": "multiply"}
    stepped = 0
    for graphic in graphics:
        params = getattr(graphic, "parameters", None)
        if not isinstance(params, dict):
            continue
        effect = params.get("effect")
        if graphic.template_id == "source_reframe":
            params["start_scale"] = 1.0
            params["end_scale"] = min(1.15, max(1.0, float(params.get("end_scale") or 1.15)))
            params["easing"] = params.get("easing") or "easing.bezier"
        if effect in blends:
            params["blend"] = blends[effect]
        if effect in ("paper_craft", "scrapbook"):
            params["fps_step"] = 12
            stepped += 1
        if effect == "glitch":
            graphic.end = min(graphic.end, graphic.start + 0.12)
    return {"stepped": stepped}


def _overlaps(item, other) -> bool:
    return float(item.start) < float(other.end) and float(item.end) > float(other.start)


def interrupt_agent(graphics, story, chosen, choice_made):
    """Keep a picture change on the speech. A look that sits only in a pause is removed."""
    captions = story.get("lines") or []
    dropped = []
    kept = []
    for graphic in graphics:
        effect = (getattr(graphic, "parameters", None) or {}).get("effect")
        spoken = any(_overlaps(graphic, SimpleLine(row["start"], row["end"])) for row in captions)
        if getattr(graphic, "template_id", "") == "look_effect" and captions and not spoken:
            dropped.append({"id": graphic.id, "effect": effect, "reason": "pause"})
            continue
        kept.append(graphic)
    if not choice_made:
        return kept, {"status": "waiting", "dropped": dropped, "added": 0}
    allowed = [key for key in SPEECH_LOOKS if key in (chosen or [])]
    added = 0
    last_visual = -INTERRUPT_SECONDS
    cursor = 0
    for row in captions:
        covering = [graphic for graphic in kept if graphic.start <= row["end"] and graphic.end >= row["start"]]
        if covering:
            last_visual = max(last_visual, max(float(graphic.start) for graphic in covering))
            continue
        if not allowed or row["start"] - last_visual < INTERRUPT_SECONDS:
            continue
        effect = allowed[cursor % len(allowed)]
        cursor += 1
        end = min(row["end"], row["start"] + 2.2)
        if end - row["start"] < 0.8:
            end = row["start"] + 1.2
        kept.append(_graphic(
            f"interrupt_{effect}_{int(row['start'] * 100)}",
            row["start"],
            end,
            "look_effect",
            effect,
            {"editorial_generated": True, "effect": effect, "look_overlay": True, "interrupt": True},
        ))
        last_visual = row["start"]
        added += 1
    return kept, {"status": "placed", "dropped": dropped, "added": added}


class SimpleLine:
    def __init__(self, start, end):
        self.start = start
        self.end = end


def silence_spans(captions, threshold: float = 0.6):
    """Gaps between spoken lines. The words themselves are not part of the gap."""
    ordered = sorted((caption for caption in captions or [] if float(getattr(caption, "end", 0)) > float(getattr(caption, "start", 0))), key=lambda caption: float(caption.start))
    spans = []
    for left, right in zip(ordered, ordered[1:]):
        gap = float(right.start) - float(left.end)
        if gap > threshold:
            spans.append({"start": round(float(left.end), 3), "end": round(float(right.start), 3), "gap": round(gap, 3)})
    return spans


def _map_time(moment: float, spans, keep: float) -> float:
    removed = 0.0
    for span in spans:
        cut = max(0.0, span["gap"] - keep)
        if moment >= span["end"]:
            removed += cut
            continue
        if moment > span["start"]:
            return round(span["start"] + min(moment - span["start"], keep) - removed, 3)
        break
    return round(moment - removed, 3)


def apply_pause_tighten(captions, graphics, threshold: float = 0.6, keep: float = 0.12):
    """Close pauses longer than the threshold. Spoken words keep their order and their text."""
    spans = silence_spans(captions, threshold)
    if not spans:
        return spans
    for caption in captions or []:
        caption.start = _map_time(float(caption.start), spans, keep)
        caption.end = max(caption.start + 0.2, _map_time(float(caption.end), spans, keep))
        for word in getattr(caption, "words", None) or []:
            if hasattr(word, "start"):
                word.start = _map_time(float(word.start), spans, keep)
                word.end = max(word.start + 0.05, _map_time(float(word.end), spans, keep))
    survivors = []
    for graphic in graphics or []:
        start = _map_time(float(graphic.start), spans, keep)
        end = _map_time(float(graphic.end), spans, keep)
        if end - start < 0.2:
            continue
        graphic.start = start
        graphic.end = end
        survivors.append(graphic)
    if isinstance(graphics, list):
        graphics[:] = survivors
    return spans


def stock_vfx_agent(graphics):
    """Prefer an alpha clip for atmosphere. The procedural draw remains the fallback."""
    prefer = {"fog", "storm", "confetti", "light_leak"}
    marked = 0
    for graphic in graphics:
        params = getattr(graphic, "parameters", None)
        if not isinstance(params, dict):
            continue
        if params.get("effect") in prefer:
            params["vfx_prefer"] = "alpha"
            params["vfx_source"] = "procedural"
            marked += 1
    return {"marked": marked, "fallback": "procedural"}


def sound_agent(state, graphics, chosen, choice_made):
    """Map a hit to a visible entrance. Skip the mix when sound design is off."""
    from app.services.overlay_styles import mark_sound_hits
    if choice_made and "sfx" not in (chosen or []):
        return {"status": "off"}
    mark_sound_hits(graphics, list(chosen or []) or ["sfx"], True)
    project_id = getattr(state, "id", None)
    if not project_id:
        return {"status": "marked", "rendered": False}
    from app.services.automatic_sfx import prepare_sfx
    duration = float(getattr(state, "duration_seconds", 0) or 0)
    if duration < 1 and graphics:
        duration = max(float(graphic.end) for graphic in graphics)
    prepare_sfx(project_id, graphics, max(duration, 1.0))
    return {"status": "mixed", "lead_ms": 40, "voice_lufs": -14, "under_db": [6, 12]}


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
                "easing": (getattr(graphic, "parameters", None) or {}).get("easing", ""),
                "blend": (getattr(graphic, "parameters", None) or {}).get("blend", ""),
                "vfx": (getattr(graphic, "parameters", None) or {}).get("vfx_prefer", ""),
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
    """Run every short-form agent in order. A later agent may drop a beat. It may not invent words."""
    graphics = list(graphics if graphics is not None else getattr(state, "graphics", []) or [])
    chosen = list(chosen or [])
    domain = getattr(getattr(state, "settings", None), "domain_profile", None)
    pack = style_pack(domain)
    story = build_story(getattr(state, "captions", None) or [])
    captions = caption_agent(state, chosen, choice_made)
    graphics, emphasis = emphasis_agent(state, graphics, story, chosen, choice_made)
    product_note = str(getattr(getattr(state, "settings", None), "overlay_product_note", "") or "")
    graphics, entities = entity_agent(graphics, story, chosen, choice_made, product_note)
    relevance_drops = []
    density_drops = []
    interrupts = {"status": "waiting", "dropped": [], "added": 0}
    if choice_made:
        graphics, relevance_drops = relevance_agent(graphics, getattr(state, "captions", None) or [], story)
        graphics, interrupts = interrupt_agent(graphics, story, chosen, choice_made)
        graphics, density_drops = density_agent(graphics)
    else:
        graphics, interrupts = interrupt_agent(graphics, story, chosen, False)
    graphics, paper = paper_purple_agent(state, graphics, story, chosen, choice_made)
    motion = motion_agent(graphics)
    stock = stock_vfx_agent(graphics)
    sound = sound_agent(state, graphics, chosen, choice_made)
    platform = platform_agent(state)
    settings = getattr(state, "settings", None)
    try:
        threshold = float(getattr(settings, "pause_threshold", 0.6) or 0.6)
    except (TypeError, ValueError):
        threshold = 0.6
    pauses = silence_spans(getattr(state, "captions", None) or [], threshold)
    if getattr(settings, "tighten_pauses", False) and pauses:
        apply_pause_tighten(getattr(state, "captions", None) or [], graphics, threshold)
        pauses = {"tightened": True, "spans": pauses}
    else:
        pauses = {"tightened": False, "spans": pauses}
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
            "caption",
            "emphasis",
            "entity",
            "relevance",
            "interrupt",
            "density",
            "paper_purple",
            "motion",
            "stock_vfx",
            "sound",
            "platform",
            "remotion",
            "measure",
        ],
        "style_pack": pack,
        "story": story,
        "caption": captions,
        "emphasis": emphasis,
        "entity": entities,
        "relevance_dropped": relevance_drops,
        "interrupt": interrupts,
        "density_dropped": density_drops,
        "paper_purple": paper,
        "pauses": pauses,
        "motion": motion,
        "stock_vfx": stock,
        "sound": sound,
        "platform": platform,
        "remotion": {"fps": composition["fps"], "tracks": len(composition["tracks"])},
        "acceptance": checks,
        "chosen": chosen,
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
