"""Deterministic placement for editorial cues.

The planner may suggest approximate times and a center point. This module
snaps those times, builds a preview-space avoid envelope, and picks a 3x3
slot that stays inside platform dead zones. It does not train a model and it
does not read timeline files.
"""

from __future__ import annotations

import math
import random
from typing import Optional, Sequence

CenterRect = tuple[float, float, float, float]  # center_x, center_y, w, h
Box = tuple[float, float, float, float]  # x1, y1, x2, y2

DOMAIN_CLASSES = {
    "general": frozenset({"face", "hand"}),
    "medical": frozenset({"face", "hand", "instrument"}),
    "sports": frozenset({"face", "hand", "ball"}),
}

TEMPLATE_FAMILY = {
    "kinetic_typography": "text_title",
    "mixed_typography_title": "text_title",
    "authored_title": "text_title",
    "stat_counter": "callout",
    "dimension_callout": "callout",
    "jargon_translation": "callout",
    "split_screen_vertical": "split_broll",
    "youtube_insert": "split_broll",
    "article_reconstruction": "article_card",
}

STRATEGY_TEMPLATE = {
    "BROLL_VIDEO": "youtube_insert",
    "STOCK_IMAGE": "split_screen_vertical",
    "CHECKLIST": "kinetic_typography",
    "MIXED_TYPOGRAPHY_TITLE": "kinetic_typography",
    "ICONOGRAPHY": "split_screen_vertical",
    "MOTION_GRAPHIC": "split_screen_vertical",
}

# Center rects for chrome that sits on the export regardless of the picture.
DEAD_ZONE_PRESETS = {
    "reels": [
        (0.50, 0.06, 1.00, 0.12),
        (0.50, 0.91, 1.00, 0.18),
        (0.93, 0.50, 0.14, 1.00),
    ],
    "youtube": [
        (0.50, 0.05, 1.00, 0.10),
        (0.50, 0.94, 1.00, 0.12),
    ],
    "none": [],
}


def family_of(template_id: str) -> str:
    return TEMPLATE_FAMILY.get(template_id, "callout")


def same_family(left: str, right: str) -> bool:
    return family_of(left) == family_of(right)


def preset_for_aspect(aspect_ratio: str) -> str:
    if aspect_ratio == "9:16":
        return "reels"
    if aspect_ratio == "16:9":
        return "youtube"
    return "none"


def dead_zones(preset: str) -> list[CenterRect]:
    return list(DEAD_ZONE_PRESETS.get(preset, ()))


def safe_bounds(preset: str) -> tuple[float, float, float, float]:
    """Largest axis-aligned playable rect inside the preset's bands."""
    if preset == "reels":
        return (0.04, 0.12, 0.86, 0.82)
    if preset == "youtube":
        return (0.04, 0.10, 0.96, 0.88)
    return (0.0, 0.0, 1.0, 1.0)


def to_box(rect: CenterRect) -> Box:
    cx, cy, w, h = rect
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def from_box(box: Box) -> CenterRect:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1)


def intersects(a: Box, b: Box, pad: float = 0.0) -> bool:
    return a[0] - pad < b[2] and a[2] + pad > b[0] and a[1] - pad < b[3] and a[3] + pad > b[1]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def rect_hits(rect: CenterRect, others: Sequence[CenterRect]) -> bool:
    box = to_box(rect)
    return any(intersects(box, to_box(other)) for other in others)


def visible_preview_rect(source_rect: CenterRect, *, crop: Optional[CenterRect] = None, zoom: float = 1.0, pan: tuple[float, float] = (0.0, 0.0)) -> Optional[CenterRect]:
    """Map a source-frame box into preview space.

    Order: reframe crop, zoom about the frame center, pan, then discard a box
    whose area still inside [0, 1] is under 10% of its post-transform area.
    """
    x1, y1, x2, y2 = to_box(source_rect)
    if crop:
        left, top, right, bottom = to_box(crop)
        width = max(1e-6, right - left)
        height = max(1e-6, bottom - top)
        x1, x2 = (x1 - left) / width, (x2 - left) / width
        y1, y2 = (y1 - top) / height, (y2 - top) / height

    def zoom_about_center(value: float) -> float:
        return 0.5 + (value - 0.5) * zoom

    x1, x2 = zoom_about_center(x1), zoom_about_center(x2)
    y1, y2 = zoom_about_center(y1), zoom_about_center(y2)
    x1 += pan[0]
    x2 += pan[0]
    y1 += pan[1]
    y2 += pan[1]
    full = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    vx1, vy1, vx2, vy2 = max(0.0, x1), max(0.0, y1), min(1.0, x2), min(1.0, y2)
    visible = max(0.0, vx2 - vx1) * max(0.0, vy2 - vy1)
    if full <= 0 or visible / full < 0.10:
        return None
    return from_box((vx1, vy1, vx2, vy2))


def envelope(boxes: Sequence[Box], pad: float = 0.01) -> list[CenterRect]:
    """Bounding envelopes of overlapping boxes. Gaps between boxes are kept."""
    pending = list(boxes)
    merged: list[Box] = []
    while pending:
        current = pending.pop()
        grew = True
        while grew:
            grew = False
            rest: list[Box] = []
            for other in pending:
                if intersects(current, other, pad):
                    current = (min(current[0], other[0]), min(current[1], other[1]), max(current[2], other[2]), max(current[3], other[3]))
                    grew = True
                else:
                    rest.append(other)
            pending = rest
        merged.append(current)
    return [from_box(box) for box in merged]


def interval_avoid_rects(frames: Sequence[dict], start_sec: float, end_sec: float, domain: str) -> list[CenterRect]:
    classes = DOMAIN_CLASSES.get(domain, DOMAIN_CLASSES["general"])
    boxes: list[Box] = []
    for frame in frames:
        time_sec = float(frame.get("time_sec", 0))
        if time_sec < start_sec - 0.5 or time_sec > end_sec + 0.5:
            continue
        for det in frame.get("detections") or []:
            if det.get("label") not in classes:
                continue
            preview = det.get("preview_rect")
            if preview is None and det.get("source_rect"):
                preview = visible_preview_rect(tuple(det["source_rect"]))  # type: ignore[arg-type]
            if not preview:
                continue
            boxes.append(to_box(tuple(preview)))  # type: ignore[arg-type]
    return envelope(boxes)


def quantize_incoming_frame(cut_sec: float, fps: float) -> float:
    """First frame of the incoming shot. cut_sec is that shot's presentation time."""
    if fps <= 0:
        return cut_sec
    return round(cut_sec * fps) / fps


def snap_interval(start: float, end: float, *, cuts: Sequence[float], gaps: Sequence[float], word_start: Optional[float], fps: float, tolerance: float = 0.25) -> dict:
    """Snap planner times onto a cut, a pause, or the anchor word.

    A raw interval that contains a cut stays marked crosses_cut even after the
    snap repairs it, so batch-accept can still hold it back.
    """
    raw_crosses = any(start < cut < end for cut in cuts)

    def pick(target: float, word: Optional[float]) -> tuple[float, str]:
        options: list[tuple[float, float, str]] = []
        for cut in cuts:
            if abs(target - cut) <= tolerance:
                snapped = quantize_incoming_frame(cut, fps)
                options.append((abs(target - cut), snapped, "shot_cut_next_frame"))
        for gap in gaps:
            if abs(target - gap) <= tolerance:
                options.append((abs(target - gap), gap, "whisper_gap"))
        if word is not None and abs(target - word) <= tolerance:
            shot = _shot_containing(word, cuts)
            cue_shot = _shot_containing(target, cuts)
            if shot == cue_shot:
                options.append((abs(target - word) - 1e-6, word, "word_start"))
        if not options:
            return target, "none"
        options.sort()
        # Word onset inside the shot beats a cut. A cut beats a pause.
        rank = {"word_start": 0, "shot_cut_next_frame": 1, "whisper_gap": 2}
        best = min(options, key=lambda item: (rank[item[2]], item[0]))
        return best[1], best[2]

    new_start, start_snap = pick(start, word_start)
    new_end, end_snap = pick(end, None)
    if new_end <= new_start:
        new_end = new_start + 0.4
        end_snap = "none"
    return {
        "start_sec": round(new_start, 4),
        "end_sec": round(new_end, 4),
        "start_snap": start_snap,
        "end_snap": end_snap,
        "crosses_cut": raw_crosses,
    }


def _shot_containing(time_sec: float, cuts: Sequence[float]) -> int:
    index = 0
    for cut in sorted(cuts):
        if time_sec < cut:
            break
        index += 1
    return index


def find_next_free_slot(current: CenterRect, avoid: Sequence[CenterRect], preset: str) -> Optional[CenterRect]:
    x_min, y_min, x_max, y_max = safe_bounds(preset)
    _, _, width, height = current
    if width > (x_max - x_min) or height > (y_max - y_min):
        return None
    blocked = [to_box(rect) for rect in list(avoid) + dead_zones(preset)]
    cell_w = (x_max - x_min) / 3
    cell_h = (y_max - y_min) / 3
    seen: set[tuple[float, float]] = set()
    candidates: list[tuple[float, CenterRect]] = []
    for row in range(3):
        for col in range(3):
            raw_x = x_min + cell_w * (col + 0.5)
            raw_y = y_min + cell_h * (row + 0.5)
            center_x = clamp(raw_x, x_min + width / 2, x_max - width / 2)
            center_y = clamp(raw_y, y_min + height / 2, y_max - height / 2)
            key = (round(center_x, 4), round(center_y, 4))
            if key in seen:
                continue
            seen.add(key)
            rect: CenterRect = (center_x, center_y, width, height)
            if any(intersects(to_box(rect), box) for box in blocked):
                continue
            dist = (center_x - current[0]) ** 2 + (center_y - current[1]) ** 2
            candidates.append((dist, rect))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def default_size(layout: str) -> tuple[float, float]:
    if layout == "fullscreen":
        return (0.86, 0.70)
    if layout == "split_screen":
        return (0.42, 0.55)
    return (0.78, 0.18)


def effective_scale(user_scale: float, rect: CenterRect, frame: tuple[float, float], natural: tuple[float, float]) -> float:
    """Scale painted inside screen_rect. user_scale cannot grow past the box."""
    width, height = rect[2], rect[3]
    frame_w, frame_h = frame
    natural_w, natural_h = natural
    if natural_w <= 0 or natural_h <= 0:
        return min(user_scale, 1.0)
    auto_fit = min((width * frame_w) / natural_w, (height * frame_h) / natural_h)
    return min(user_scale, auto_fit)


def annotate_emphasis(words: Sequence[dict], samples: Sequence[tuple[float, float]], window: float = 2.0, ratio: float = 1.5) -> list[dict]:
    """Mark a word high when its in-span RMS is 1.5x the speech around it.

    samples are (time_sec, rms). Energy outside a word span is ignored, so a
    music hit between words does not become emphasis.
    """
    annotated = []
    for word in words:
        start, end = float(word["start_sec"]), float(word["end_sec"])
        inside = [rms for time_sec, rms in samples if start <= time_sec <= end]
        local = [rms for time_sec, rms in samples if abs(time_sec - (start + end) / 2) <= window / 2 and _inside_any_word(time_sec, words)]
        speech = (sum(inside) / len(inside)) if inside else 0.0
        baseline = (sum(local) / len(local)) if local else 0.0
        speech_ratio = (speech / baseline) if baseline > 0 else 0.0
        annotated.append({
            **word,
            "speech_rms_ratio": round(speech_ratio, 4),
            "emphasis": "high" if speech_ratio >= ratio else "normal",
        })
    return annotated


def _inside_any_word(time_sec: float, words: Sequence[dict]) -> bool:
    return any(float(word["start_sec"]) <= time_sec <= float(word["end_sec"]) for word in words)


def word_gaps(words: Sequence[dict], minimum: float = 0.18) -> list[float]:
    ordered = sorted(words, key=lambda word: float(word["start_sec"]))
    gaps = []
    for prev, nxt in zip(ordered, ordered[1:]):
        gap = float(nxt["start_sec"]) - float(prev["end_sec"])
        if gap >= minimum:
            gaps.append(float(nxt["start_sec"]))
    return gaps


def temporal_iou(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    inter = max(0.0, min(end_a, end_b) - max(start_a, start_b))
    union = max(end_a, end_b) - min(start_a, start_b)
    if union <= 0:
        return 0.0
    return inter / union


def score_placement(suggestions: Sequence[dict], human: Sequence[dict]) -> dict:
    """Four readings. Recall under 0.4 means the plan is not saving edit time."""
    matched = []
    used = set()
    for index, suggestion in enumerate(suggestions):
        best = None
        for human_index, graphic in enumerate(human):
            if human_index in used:
                continue
            overlap = temporal_iou(suggestion["start_sec"], suggestion["end_sec"], graphic["start_sec"], graphic["end_sec"])
            if overlap > 0 and (best is None or overlap > best[0]):
                best = (overlap, human_index)
        if best:
            used.add(best[1])
            matched.append((index, best[1], best[0]))
    exact = 0
    family = 0
    collisions = 0
    for suggestion in suggestions:
        rect = suggestion.get("screen_rect")
        avoid = suggestion.get("avoid_rects") or []
        if rect and rect_hits(tuple(rect), [tuple(item) for item in avoid]):
            collisions += 1
    for suggestion_index, human_index, _overlap in matched:
        left = suggestions[suggestion_index].get("template_id", "")
        right = human[human_index].get("template_id", "")
        if left == right:
            exact += 1
        if same_family(left, right):
            family += 1
    suggestion_count = len(suggestions)
    human_count = len(human)
    return {
        "temporal_iou_mean": round(sum(item[2] for item in matched) / len(matched), 4) if matched else 0.0,
        "exact_template_match": round(exact / len(matched), 4) if matched else 0.0,
        "family_template_match": round(family / len(matched), 4) if matched else 0.0,
        "avoid_collision_rate": round(collisions / suggestion_count, 4) if suggestion_count else 0.0,
        "intervention_precision": round(len(matched) / suggestion_count, 4) if suggestion_count else 0.0,
        "intervention_recall": round(len(matched) / human_count, 4) if human_count else 0.0,
    }


def sample_hard_negatives(rows: Sequence[dict], ratio: float = 2.5, seed: int = 0) -> list[dict]:
    """Training export only. Project review still keeps every left-clear cue."""
    positives = [row for row in rows if row.get("intervene") and row.get("human") == "keep"]
    hard = [row for row in rows if not row.get("intervene") and row.get("human") == "left_clear" and row.get("hard")]
    limit = int(math.floor(ratio * len(positives)))
    picker = random.Random(seed)
    chosen = hard if len(hard) <= limit else picker.sample(list(hard), limit)
    return list(positives) + list(chosen)


def place_decision(row: dict, graphic, state) -> dict:
    """Stamp snap, screen_rect, and a free slot onto one planned graphic."""
    settings = getattr(state, "settings", None)
    aspect = getattr(settings, "aspect_ratio", "9:16")
    preset = preset_for_aspect(aspect)
    domain = getattr(settings, "domain_profile", None) or ("medical" if getattr(settings, "brand_preset", "") == "medical_evidence" else "general")
    fps = float(getattr(state, "fps", 30) or 30)
    layout = (row.get("composition") or {}).get("layout") or "overlay"
    position = (row.get("composition") or {}).get("position") or [0.5, 0.5]
    width, height = default_size(layout)
    current: CenterRect = (float(position[0]), float(position[1]), width, height)
    words = _words(state)
    gaps = word_gaps(words)
    cuts = list((getattr(state, "ai_ingestion", None) or {}).get("shot_cuts") or [])
    anchor = row.get("audio_anchor_word_start")
    if anchor is None:
        anchor = _anchor_time(words, row.get("audio_anchor_word") or row.get("anchor_phrase") or "")
    snapped = snap_interval(float(row["start_sec"]), float(row["end_sec"]), cuts=cuts, gaps=gaps, word_start=anchor, fps=fps)
    frames = (getattr(state, "ai_ingestion", None) or {}).get("detection_frames") or []
    avoid = interval_avoid_rects(frames, snapped["start_sec"], snapped["end_sec"], domain)
    chosen = current
    if rect_hits(current, avoid) or rect_hits(current, dead_zones(preset)):
        slot = find_next_free_slot(current, avoid, preset)
        if slot is not None:
            chosen = slot
    hits = rect_hits(chosen, avoid) or rect_hits(chosen, dead_zones(preset))
    placement = {
        **snapped,
        "screen_rect": [round(value, 4) for value in chosen],
        "pos_x": round(chosen[0], 4),
        "pos_y": round(chosen[1], 4),
        "avoid_rects": [[round(value, 4) for value in rect] for rect in avoid],
        "preset": preset,
        "domain": domain,
        "template_family": family_of(getattr(graphic, "template_id", "") or ""),
        "hits_avoid": hits,
        "clear": (not hits) and (not snapped["crosses_cut"]),
    }
    row["start_sec"] = snapped["start_sec"]
    row["end_sec"] = snapped["end_sec"]
    row["placement"] = placement
    graphic.start = snapped["start_sec"]
    graphic.end = snapped["end_sec"]
    graphic.pos_x = placement["pos_x"]
    graphic.pos_y = placement["pos_y"]
    params = dict(getattr(graphic, "parameters", None) or {})
    params["screen_rect"] = placement["screen_rect"]
    params["avoid_rects"] = placement["avoid_rects"]
    params["max_scale"] = 1.0
    graphic.parameters = params
    return placement


def _words(state) -> list[dict]:
    found = []
    for caption in getattr(state, "captions", []) or []:
        for word in getattr(caption, "words", []) or []:
            found.append({"word": word.word, "start_sec": float(word.start), "end_sec": float(word.end)})
    return found


def _anchor_time(words: Sequence[dict], phrase: str) -> Optional[float]:
    token = (phrase or "").split()
    if not token:
        return None
    target = token[0].strip(".,!?").lower()
    for word in words:
        if str(word["word"]).strip(".,!?").lower() == target:
            return float(word["start_sec"])
    return None
