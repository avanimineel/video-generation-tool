"""Overlay choices asked after captions, matched to the project domain."""
from __future__ import annotations

from typing import Dict, Iterable, List

from app.services.project_manager import project_domain

OVERLAYS: List[Dict[str, object]] = [
    {
        "id": "kinetic_captions",
        "label": "Hormozi-style kinetic captions",
        "detail": "Spoken words pop in one at a time. The active word is highlighted in yellow and bounces.",
        "recommended": ("general", "finance", "business", "fitness", "sports", "education", "real_estate"),
    },
    {
        "id": "punch_in",
        "label": "Punch-in zooms",
        "detail": "The frame eases from 1.0x to 1.15x on a pitch, a number, or an emotional line.",
        "recommended": ("general", "finance", "business", "fitness", "sports", "real_estate", "medical", "education"),
    },
    {
        "id": "data_callouts",
        "label": "Charts and price callouts",
        "detail": "A spoken number, percent, price, or discount becomes a counter or a simple chart.",
        "recommended": ("finance", "business", "real_estate", "medical", "education", "sports", "legal"),
    },
    {
        "id": "location_maps",
        "label": "Location fly-ins",
        "detail": "A named city, store, or origin is shown as a map or an aerial view.",
        "recommended": ("real_estate", "sports", "business"),
    },
    {
        "id": "sfx",
        "label": "Sound design",
        "detail": "A short pop or whoosh plays when a title, zoom, or callout appears.",
        "recommended": ("general", "finance", "business", "fitness", "sports", "real_estate"),
    },
    {
        "id": "product_swap",
        "label": "Product-in-hand",
        "detail": "When a product is named, the picture looks for a hand or person holding that product.",
        "recommended": ("business", "fitness"),
    },
    {
        "id": "camera",
        "label": "Camera effect",
        "detail": "A viewfinder frame and focus marks sit on the picture, like a second camera.",
        "recommended": ("general", "business", "fitness", "sports", "real_estate", "education"),
    },
    {
        "id": "confetti",
        "label": "Confetti and glitter",
        "detail": "Short bursts of confetti and glitter on a win, a launch, or a result.",
        "recommended": ("general", "business", "fitness", "sports"),
    },
    {
        "id": "paper",
        "label": "Crumpled paper",
        "detail": "A paper texture and crease lines, for a document, report, or letter.",
        "recommended": ("general", "finance", "education", "legal", "business"),
    },
    {
        "id": "fog",
        "label": "Fog and smoke",
        "detail": "A soft fog bank rises through the lower half of the frame.",
        "recommended": ("general", "fitness", "sports"),
    },
    {
        "id": "film",
        "label": "Film",
        "detail": "Letterbox bars and light grain, like a filmed reel.",
        "recommended": ("general", "education", "business", "real_estate", "legal", "medical"),
    },
    {
        "id": "streaming",
        "label": "Streaming",
        "detail": "A live frame and a lower bar, like a stream or a webinar.",
        "recommended": ("general", "business", "education", "fitness", "sports"),
    },
    {
        "id": "glitch",
        "label": "Glitch",
        "detail": "Short horizontal tears and color shifts on a digital or high-energy line.",
        "recommended": ("general", "business", "fitness", "sports"),
    },
    {
        "id": "storm",
        "label": "Lightning and rain",
        "detail": "Rain streaks and a brief lightning flash for a dramatic line.",
        "recommended": ("general", "fitness", "sports"),
    },
    {
        "id": "light_leak",
        "label": "Light leak",
        "detail": "A warm flare leaks in from the corner of the frame.",
        "recommended": ("general", "business", "real_estate", "education", "fitness"),
    },
    {
        "id": "space",
        "label": "Space",
        "detail": "A dark sky and stars, for a big idea, a future, or a science line.",
        "recommended": ("general", "education", "business"),
    },
]

LOOK_ORDER = (
    "camera",
    "confetti",
    "paper",
    "fog",
    "film",
    "streaming",
    "glitch",
    "storm",
    "light_leak",
    "space",
)

_BY_ID = {str(item["id"]): item for item in OVERLAYS}

GATED_STRATEGIES = {
    "kinetic_captions": {"KINETIC_TYPOGRAPHY", "MIXED_TYPOGRAPHY_TITLE"},
    "data_callouts": {"STAT_COUNTER", "CHART", "DATA_VISUALIZATION"},
    "location_maps": {"MAP"},
    "punch_in": {"SOURCE_VIDEO_REFRAME"},
    "product_swap": {"GENERATED_VISUAL"},
}


def known_ids() -> List[str]:
    return [str(item["id"]) for item in OVERLAYS]


def normalize_styles(values: Iterable[str] | None) -> List[str]:
    chosen = []
    for value in values or []:
        key = str(value or "").strip().casefold().replace(" ", "_").replace("-", "_")
        if key in _BY_ID and key not in chosen:
            chosen.append(key)
    return chosen


def styles_for_domain(domain: str | None) -> List[dict]:
    name = project_domain(domain)
    rows = []
    for item in OVERLAYS:
        recommended = name in item["recommended"]
        rows.append({
            "id": item["id"],
            "label": item["label"],
            "detail": item["detail"],
            "recommended": recommended,
        })
    return rows


def recommended_ids(domain: str | None) -> List[str]:
    return [row["id"] for row in styles_for_domain(domain) if row["recommended"]]


def selection_from_state(state) -> tuple:
    settings = getattr(state, "settings", None)
    made = bool(getattr(settings, "overlay_choice_made", False))
    chosen = normalize_styles(getattr(settings, "overlay_styles", None))
    note = str(getattr(settings, "overlay_product_note", "") or "").strip()
    return made, chosen, note


def instruction(chosen: List[str], note: str = "") -> str:
    if not chosen:
        return (
            "The editor turned off the optional overlays. Keep the speaker, and use stock only for a concrete visible action. "
            "Do not add kinetic titles, punch-in zooms, charts, maps, or product-in-hand shots."
        )
    lines = ["The editor chose these overlays. Use a chosen overlay when the spoken line calls for it:"]
    for key in chosen:
        item = _BY_ID[key]
        lines.append(f"- {item['label']}: {item['detail']}")
    if "location_maps" in chosen:
        lines.append("For a named place, request STOCK_IMAGE with a retrieval query such as 'aerial map of <place>'.")
    if "data_callouts" in chosen:
        lines.append("For a spoken number, price, percent, or discount, use STAT_COUNTER or CHART with the exact spoken figure.")
    if "kinetic_captions" not in chosen:
        lines.append("Do not add KINETIC_TYPOGRAPHY titles. The caption track already carries the words.")
    if "product_swap" in chosen:
        product = note or "the named product"
        lines.append(f"When a product is named, search stock for a hand holding {product}. Do not invent a brand screen.")
    looks = [key for key in LOOK_ORDER if key in chosen]
    if looks:
        names = ", ".join(str(_BY_ID[key]["label"]) for key in looks)
        lines.append(f"Picture looks already placed on the timeline: {names}. Do not search stock for those textures.")
    lines.append("Leave out any overlay type that was not chosen.")
    return "\n".join(lines)


def constrain_decisions(decisions, chosen: List[str], choice_made: bool):
    """Drop overlay treatments the editor did not choose. Stock illustration stays."""
    if not choice_made:
        return decisions
    allowed = set()
    for key in chosen:
        allowed.update(GATED_STRATEGIES.get(key, set()))
    gated = set().union(*GATED_STRATEGIES.values())
    for decision in decisions:
        strategy = getattr(decision, "strategy", "")
        if strategy == "MAP" and "location_maps" in chosen:
            place = (getattr(decision, "anchor_phrase", "") or getattr(decision, "display_text", "") or "the named place").strip()
            decision.strategy = "STOCK_IMAGE"
            decision.intent = "LOCATE"
            asset = decision.asset
            asset.retrieval_query = asset.retrieval_query or f"aerial map of {place}"
            if not asset.alternate_queries:
                asset.alternate_queries = [f"{place} city map", "street map close up"]
            asset.desired_visual_description = asset.desired_visual_description or f"A clear map or aerial view of {place}."
            continue
        if strategy == "GENERATED_VISUAL" and "product_swap" in chosen:
            decision.strategy = "STOCK_IMAGE"
            asset = decision.asset
            asset.retrieval_query = asset.retrieval_query or "hand holding product close up"
            continue
        if strategy in gated and strategy not in allowed:
            decision.intervene = False
            decision.strategy = "NO_INTERVENTION"
            decision.rationale = "This overlay was not selected for this video."
    return decisions


def apply_kinetic_captions(state, chosen: List[str], choice_made: bool) -> None:
    if not choice_made or "kinetic_captions" not in chosen:
        return
    for caption in getattr(state, "captions", []) or []:
        style = caption.style
        style.has_highlight = True
        style.highlight_bounce = True
        style.highlight_active_color = "#F5E642"
        style.highlight_scale = 1.08
        style.font_weight = "900"
        style.animation_type = "pop"


def add_punch_ins(state, graphics, chosen: List[str], choice_made: bool):
    if not choice_made or "punch_in" not in chosen:
        return graphics
    from app.core.models import MotionGraphicItem
    added = 0
    for caption in getattr(state, "captions", []) or []:
        if added >= 3:
            break
        text = f"{caption.translated_text or ''} {caption.text or ''}"
        if not any(character.isdigit() for character in text) and float(caption.start or 0) > 12:
            continue
        start = float(caption.start or 0)
        end = min(float(caption.end or start), start + 1.6)
        if end - start < 0.6:
            continue
        if any(g.template_id == "source_reframe" and g.start < end and g.end > start for g in graphics):
            continue
        graphics.append(MotionGraphicItem(
            id=f"punch_{added}_{int(start * 100)}",
            start=start,
            end=round(end, 2),
            template_id="source_reframe",
            title="Punch-in",
            parameters={
                "editorial_generated": True,
                "retention_camera": True,
                "start_scale": 1.0,
                "end_scale": 1.15,
                "motion_curve": "smoothstep",
                "focus_x": 0.5,
                "focus_y": 0.35,
            },
        ))
        added += 1
    return graphics


def mark_sound_hits(graphics, chosen: List[str], choice_made: bool) -> None:
    if not choice_made or "sfx" not in chosen:
        return
    for graphic in graphics:
        if graphic.template_id == "kinetic_typography" and not graphic.parameters.get("title_style"):
            graphic.parameters["title_style"] = "bold_pop"
        if graphic.template_id == "source_reframe":
            graphic.parameters["motion_curve"] = "hold"


def add_look_overlays(state, graphics, chosen: List[str], choice_made: bool):
    """Place each selected picture look on its own short span. Unselected looks stay off."""
    graphics = [g for g in graphics if getattr(g, "template_id", "") != "look_effect"]
    selected = [key for key in LOOK_ORDER if key in chosen]
    if not choice_made or not selected:
        return graphics
    from app.core.models import MotionGraphicItem
    duration = float(getattr(state, "duration_seconds", 0) or 0)
    captions = getattr(state, "captions", None) or []
    if duration < 1 and captions:
        duration = max(float(getattr(caption, "end", 0) or 0) for caption in captions)
    duration = max(duration, 4.0)
    beat = 2.2
    gap = 1.4
    cursor = 0.6
    plan = selected + selected
    placed = 0
    for effect in plan:
        end = min(duration - 0.15, cursor + beat)
        if end - cursor < 1.0 or cursor >= duration - 1.1:
            break
        label = str(_BY_ID[effect]["label"])
        graphics.append(MotionGraphicItem(
            id=f"look_{effect}_{placed}",
            start=round(cursor, 2),
            end=round(end, 2),
            template_id="look_effect",
            title=label,
            parameters={"editorial_generated": True, "effect": effect, "look_overlay": True},
        ))
        placed += 1
        cursor = end + gap
        if placed >= len(selected) and cursor > duration * 0.72:
            break
    return graphics


def paint_look_effect(image, effect: str, t: float):
    """Draw one picture look onto an RGB frame. The speaker stays visible underneath."""
    import random
    from PIL import Image, ImageDraw
    effect = effect if effect in LOOK_ORDER else "film"
    width, height = image.size
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if effect == "camera":
        margin = max(8, int(min(width, height) * 0.045))
        arm = max(16, int(min(width, height) * 0.07))
        ink = (255, 255, 255, 210)
        for x, y, sx, sy in (
            (margin, margin, 1, 1),
            (width - margin, margin, -1, 1),
            (margin, height - margin, 1, -1),
            (width - margin, height - margin, -1, -1),
        ):
            draw.line((x, y, x + sx * arm, y), fill=ink, width=3)
            draw.line((x, y, x, y + sy * arm), fill=ink, width=3)
        cx, cy = width // 2, height // 2
        draw.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), outline=(255, 255, 255, 160))
        draw.ellipse((margin, margin + 8, margin + 14, margin + 22), fill=(230, 40, 40, 230))
    elif effect == "confetti":
        rng = random.Random(int(t * 4))
        colors = ((255, 214, 10, 210), (255, 64, 129, 200), (64, 196, 255, 200), (140, 255, 160, 200), (255, 255, 255, 230))
        for _ in range(34):
            x = rng.randrange(width)
            y = (rng.randrange(height) + int(t * 36)) % height
            draw.rectangle((x, y, x + rng.choice((4, 7, 10)), y + rng.choice((8, 12, 6))), fill=rng.choice(colors))
        for _ in range(16):
            x, y = rng.randrange(width), rng.randrange(height)
            draw.ellipse((x, y, x + 3, y + 3), fill=(255, 255, 255, 230))
    elif effect == "paper":
        draw.rectangle((0, 0, width, height), fill=(214, 196, 160, 56))
        for step in range(1, 8):
            y = int(height * step / 8)
            draw.line((0, y, width, y + (8 if step % 2 else -8)), fill=(120, 90, 50, 80), width=2)
        draw.line((0, int(height * 0.22), width, int(height * 0.48)), fill=(255, 255, 255, 50), width=3)
    elif effect == "fog":
        for band in range(8):
            top = int(height * (0.42 + band * 0.07))
            draw.rectangle((0, top, width, top + int(height * 0.1)), fill=(226, 232, 236, 16 + band * 12))
    elif effect == "film":
        bar = max(10, int(height * 0.07))
        draw.rectangle((0, 0, width, bar), fill=(0, 0, 0, 220))
        draw.rectangle((0, height - bar, width, height), fill=(0, 0, 0, 220))
        rng = random.Random(int(t * 12))
        for _ in range(70):
            draw.point((rng.randrange(width), rng.randrange(height)), fill=(255, 255, 255, rng.randint(50, 140)))
    elif effect == "streaming":
        draw.rectangle((6, 6, width - 6, height - 6), outline=(255, 255, 255, 180), width=max(3, width // 100))
        draw.rectangle((int(width * 0.06), int(height * 0.05), int(width * 0.24), int(height * 0.1)), fill=(210, 28, 36, 230))
        draw.rectangle((0, int(height * 0.84), int(width * 0.58), int(height * 0.92)), fill=(0, 0, 0, 150))
        draw.text((int(width * 0.08), int(height * 0.055)), "LIVE", fill=(255, 255, 255, 255))
    elif effect == "glitch":
        rng = random.Random(int(t * 8))
        for _ in range(6):
            y = rng.randrange(max(1, height - 8))
            band = rng.randint(3, 14)
            color = rng.choice(((255, 0, 90, 100), (0, 230, 255, 90), (255, 255, 255, 60)))
            draw.rectangle((0, y, width, min(height, y + band)), fill=color)
    elif effect == "storm":
        draw.rectangle((0, 0, width, int(height * 0.32)), fill=(8, 14, 32, 100))
        rng = random.Random(int(t * 10))
        for _ in range(36):
            x, y = rng.randrange(width), rng.randrange(height)
            draw.line((x, y, x - 10, y + 26), fill=(190, 210, 255, 120), width=1)
        if int(t * 3) % 5 == 0:
            x = int(width * 0.64)
            draw.line(
                (x, 0, x - int(width * 0.04), int(height * 0.22), x + int(width * 0.03), int(height * 0.4), x - int(width * 0.06), int(height * 0.62)),
                fill=(255, 255, 255, 220),
                width=3,
            )
    elif effect == "light_leak":
        draw.ellipse((-int(width * 0.15), -int(height * 0.1), int(width * 0.55), int(height * 0.42)), fill=(255, 140, 40, 78))
        draw.ellipse((int(width * 0.45), int(height * 0.58), int(width * 1.15), int(height * 1.1)), fill=(255, 50, 90, 48))
    else:
        draw.rectangle((0, 0, width, height), fill=(6, 8, 28, 70))
        rng = random.Random(11)
        for _ in range(60):
            x, y = rng.randrange(width), rng.randrange(height)
            twinkle = 200 if (int(t * 2) + x) % 5 else 70
            draw.ellipse((x, y, x + 2, y + 2), fill=(255, 255, 255, twinkle))
    composed = Image.alpha_composite(image.convert("RGBA"), layer)
    image.paste(composed.convert(image.mode))
    return image
