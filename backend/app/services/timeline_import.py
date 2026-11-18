"""Offline FCPXML and Resolve timeline import.

This module turns a historical timeline into placement records and feedback
rows for the scorecard and a training export. It is a batch job.

Do not import it from auto-produce, the editorial planner, or an API route.
An exported timeline has no avoid boxes and no planner proposal, and its
layout belongs to whatever era the editor was working in.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Sequence

from app.services.editorial_placement import (
    TEMPLATE_FAMILY,
    family_of,
    interval_avoid_rects,
    sample_hard_negatives,
    score_placement,
)

# Longer phrases first so "lower third" is not also matched as a generic title.
_NAME_FAMILIES = (
    ("lower third", "text_title"),
    ("basic title", "text_title"),
    ("custom title", "text_title"),
    ("split screen", "split_broll"),
    ("b-roll", "split_broll"),
    ("broll", "split_broll"),
    ("article", "article_card"),
    ("counter", "callout"),
    ("callout", "callout"),
    ("stat", "callout"),
    ("title", "text_title"),
)

# Normalized size at FCP scale 100, used when the generator has no pixel bounds.
_FAMILY_SIZE = {
    "text_title": (0.72, 0.16),
    "callout": (0.36, 0.18),
    "split_broll": (0.50, 0.56),
    "article_card": (0.70, 0.40),
}

_OVERLAY_TAGS = {"title", "generator"}
_CONNECTED_TAGS = {"video", "ref-clip", "asset-clip", "clip"}


def fcp_transform_to_center_rect(fcp_x: float, fcp_y: float, scale_x: float, scale_y: float, frame_w: float, frame_h: float, natural_w: float, natural_h: float) -> tuple[float, float, float, float]:
    """FCP position is a percent of frame height, origin at center, +Y up."""
    center_x = 0.5 + (fcp_x / 100.0) * (frame_h / frame_w)
    center_y = 0.5 - (fcp_y / 100.0)
    width = min(1.0, (natural_w * (scale_x / 100.0)) / frame_w)
    height = min(1.0, (natural_h * (scale_y / 100.0)) / frame_h)
    return (center_x, center_y, width, height)


def map_template_family(name: str) -> tuple[Optional[str], bool]:
    """Return (family, unmapped). Unmapped names stay in the export for review."""
    token = (name or "").strip()
    if token in TEMPLATE_FAMILY:
        return family_of(token), False
    lowered = token.lower()
    for phrase, family in _NAME_FAMILIES:
        if phrase in lowered:
            return family, False
    return None, True


def import_fcpxml(xml_text: str, *, project_id: str = "import", features: Optional[dict] = None, shadow_suggestions: Optional[Sequence[dict]] = None, domain: str = "general") -> dict:
    """Parse one timeline and attach features the caller already measured.

    `features` may hold `shot_cuts`, `detection_frames`, and Whisper `words`.
    This function does not run the live planner. Pass `shadow_suggestions`
    from a separate planner run when a baseline score is needed.
    """
    root = ET.fromstring(xml_text)
    frame_w, frame_h, fps = _sequence_format(root)
    timeline_hash = hashlib.sha1(xml_text.encode("utf-8")).hexdigest()[:8]
    effects = {node.attrib.get("id"): node.attrib.get("name") or "" for node in root.iter("effect")}
    placements = []
    feedback = []
    index = 0
    for node in root.iter():
        if not _is_overlay(node):
            continue
        duration = _seconds(node.attrib.get("duration") or "0s", fps)
        if duration <= 0:
            continue
        start = _seconds(node.attrib.get("offset") or node.attrib.get("start") or "0s", fps)
        name = node.attrib.get("name") or effects.get(node.attrib.get("ref"), "") or node.tag
        family, unmapped = map_template_family(name)
        template_id = node.attrib.get("ref") or name
        fcp_x, fcp_y, scale_x, scale_y = _transform(node)
        natural_w, natural_h = _natural_pixels(family, frame_w, frame_h)
        rect = fcp_transform_to_center_rect(fcp_x, fcp_y, scale_x, scale_y, frame_w, frame_h, natural_w, natural_h)
        segment_id = f"imp_{timeline_hash}_{index}"
        text = _text(node)
        placement = {
            "segment_id": segment_id,
            "raw_start_sec": round(start, 4),
            "raw_end_sec": round(start + duration, 4),
            "start_sec": round(start, 4),
            "end_sec": round(start + duration, 4),
            "start_snap": "none",
            "end_snap": "none",
            "crosses_cut": False,
            "intervene": True,
            "template_id": template_id,
            "template_family": family,
            "unmapped": unmapped,
            "name": name,
            "text": text,
            "screen_rect": [round(value, 4) for value in rect],
            "pos_x": round(rect[0], 4),
            "pos_y": round(rect[1], 4),
            "user_scale": round(scale_x / 100.0, 4),
            "effective_scale": round(min(scale_x / 100.0, 1.0), 4),
            "avoid_rects": [],
        }
        placements.append(placement)
        feedback.append({
            "cue_id": segment_id,
            "project_id": project_id,
            "source": "fcpxml_import",
            "final_decision": "keep",
            "edits": [],
            "editor_notes": "",
            "transcript_context": text,
        })
        index += 1
    _attach_features(placements, features or {}, domain)
    human = [_score_row(row) for row in placements if row.get("template_family")]
    scorecard = score_placement(list(shadow_suggestions or []), human) if shadow_suggestions is not None else None
    training = _training_rows(placements, (features or {}).get("words") or [])
    return {
        "source": "fcpxml_import",
        "project_id": project_id,
        "fps": round(fps, 6),
        "frame": {"width": frame_w, "height": frame_h},
        "placements": placements,
        "feedback": feedback,
        "unmapped": [row["name"] for row in placements if row["unmapped"]],
        "scorecard": scorecard,
        "training_rows": training,
    }


def fcpxml_to_eval_records(xml_text: str, fps: float = 30.0) -> list[dict]:
    """Scorecard-shaped rows. `fps` is kept for callers that already know it.

    The sequence `frameDuration` in the XML wins when it is present.
    """
    del fps
    imported = import_fcpxml(xml_text)
    return [_score_row(row) for row in imported["placements"]]


def write_offline_bundle(imported: dict, directory: Path) -> dict:
    """Write the two offline destinations. This does not touch editorial_feedback.json."""
    directory.mkdir(parents=True, exist_ok=True)
    placements = directory / "fcpxml_placements.json"
    feedback = directory / "fcpxml_feedback.json"
    training = directory / "training_export.json"
    placements.write_text(json.dumps(imported["placements"], indent=2), encoding="utf-8")
    feedback.write_text(json.dumps(imported["feedback"], indent=2), encoding="utf-8")
    training.write_text(json.dumps(imported["training_rows"], indent=2), encoding="utf-8")
    written = {"placements": str(placements), "feedback": str(feedback), "training_export": str(training)}
    if imported.get("scorecard") is not None:
        score_path = directory / "scorecard_baseline.json"
        score_path.write_text(json.dumps(imported["scorecard"], indent=2), encoding="utf-8")
        written["scorecard"] = str(score_path)
    return written


def _attach_features(placements: list[dict], features: dict, domain: str) -> None:
    cuts = [float(cut) for cut in features.get("shot_cuts") or []]
    frames = features.get("detection_frames") or []
    for row in placements:
        row["crosses_cut"] = any(row["raw_start_sec"] < cut < row["raw_end_sec"] for cut in cuts)
        avoid = interval_avoid_rects(frames, row["start_sec"], row["end_sec"], domain)
        row["avoid_rects"] = [[round(value, 4) for value in rect] for rect in avoid]


def _training_rows(placements: Sequence[dict], words: Sequence[dict]) -> list[dict]:
    positives = []
    for row in placements:
        if row.get("unmapped"):
            continue
        positives.append({
            "intervene": True,
            "human": "keep",
            "source": "fcpxml_import",
            "segment_id": row["segment_id"],
            "start_sec": row["start_sec"],
            "end_sec": row["end_sec"],
            "template_id": row["template_id"],
            "template_family": row["template_family"],
            "screen_rect": row["screen_rect"],
        })
    hard = []
    for word in words:
        if word.get("emphasis") != "high":
            continue
        start, end = float(word["start_sec"]), float(word["end_sec"])
        if any(row["start_sec"] < end and start < row["end_sec"] for row in placements):
            continue
        hard.append({
            "intervene": False,
            "human": "left_clear",
            "hard": True,
            "source": "fcpxml_import",
            "start_sec": start,
            "end_sec": end,
            "reason": "emphasis_without_overlay",
        })
    return sample_hard_negatives(positives + hard, ratio=2.5)


def _score_row(row: dict) -> dict:
    return {
        "template_id": row["template_id"],
        "template_family": row.get("template_family"),
        "start_sec": row["start_sec"],
        "end_sec": row["end_sec"],
        "screen_rect": row["screen_rect"],
        "name": row.get("name"),
    }


def _is_overlay(node: ET.Element) -> bool:
    if node.tag in _OVERLAY_TAGS:
        return True
    return node.tag in _CONNECTED_TAGS and bool(node.attrib.get("lane"))


def _sequence_format(root: ET.Element) -> tuple[float, float, float]:
    formats = {node.attrib.get("id"): node for node in root.iter("format")}
    sequence = next(root.iter("sequence"), None)
    chosen = None
    if sequence is not None:
        chosen = formats.get(sequence.attrib.get("format"))
    if chosen is None and formats:
        chosen = next(iter(formats.values()))
    if chosen is None:
        return 1920.0, 1080.0, 30.0
    width = float(chosen.attrib.get("width") or 1920)
    height = float(chosen.attrib.get("height") or 1080)
    fps = _fps(chosen.attrib.get("frameDuration") or "1/30s")
    return width, height, fps


def _fps(frame_duration: str) -> float:
    token = frame_duration.strip().rstrip("s")
    if "/" not in token:
        seconds = float(token or 0)
        return (1.0 / seconds) if seconds else 30.0
    numerator, denominator = token.split("/", 1)
    num = float(numerator or 0)
    den = float(denominator or 0)
    if num <= 0 or den <= 0:
        return 30.0
    return den / num


def _seconds(value: str, fps: float) -> float:
    token = value.strip().rstrip("s")
    if "/" in token:
        numerator, denominator = token.split("/", 1)
        denom = float(denominator or fps or 1)
        return float(numerator) / denom if denom else 0.0
    return float(token or 0)


def _transform(node: ET.Element) -> tuple[float, float, float, float]:
    position = ""
    scale = ""
    adjust = node.find("adjust-transform")
    if adjust is not None:
        position = adjust.attrib.get("position") or ""
        scale = adjust.attrib.get("scale") or ""
        for param in adjust.findall("param"):
            key = (param.attrib.get("name") or "").lower()
            if key == "position":
                position = param.attrib.get("value") or position
            if key == "scale":
                scale = param.attrib.get("value") or scale
    if not position:
        position = node.attrib.get("position") or "0 0"
    if not scale:
        scale = node.attrib.get("scale") or "100 100"
    px, py = _pair(position, 0.0)
    sx, sy = _pair(scale, 100.0)
    return px, py, sx, sy


def _pair(value: str, default: float) -> tuple[float, float]:
    parts = [part for part in value.replace(",", " ").split() if part]
    if not parts:
        return default, default
    first = float(parts[0])
    second = float(parts[1]) if len(parts) > 1 else first
    return first, second


def _natural_pixels(family: Optional[str], frame_w: float, frame_h: float) -> tuple[float, float]:
    width, height = _FAMILY_SIZE.get(family or "", (0.40, 0.20))
    return width * frame_w, height * frame_h


def _text(node: ET.Element) -> str:
    chunks = [item.text.strip() for item in node.iter("text-style") if item.text and item.text.strip()]
    return " ".join(chunks)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import an FCPXML timeline into offline placement JSON.")
    parser.add_argument("fcpxml")
    parser.add_argument("--out", required=True)
    parser.add_argument("--project-id", default="import")
    parser.add_argument("--features", help="JSON with shot_cuts, detection_frames, and words. Measured outside the live planner.")
    parser.add_argument("--shadow", help="Planner suggestions JSON from a separate shadow run.")
    parser.add_argument("--media", help="Source video. Shot cuts are probed here and are not sent to auto-produce.")
    args = parser.parse_args(argv)
    features = json.loads(Path(args.features).read_text(encoding="utf-8")) if args.features else {}
    if args.media:
        from app.services.editorial_features import detect_shot_cuts
        features.setdefault("shot_cuts", detect_shot_cuts(args.media))
    shadow = json.loads(Path(args.shadow).read_text(encoding="utf-8")) if args.shadow else None
    imported = import_fcpxml(Path(args.fcpxml).read_text(encoding="utf-8"), project_id=args.project_id, features=features, shadow_suggestions=shadow)
    written = write_offline_bundle(imported, Path(args.out))
    print(json.dumps({"unmapped": imported["unmapped"], "files": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
