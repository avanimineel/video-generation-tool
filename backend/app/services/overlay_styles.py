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
]

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
