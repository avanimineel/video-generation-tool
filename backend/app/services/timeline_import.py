"""Offline timeline import for the placement scorecard.

This parser turns an exported timeline into the same records the scorecard
compares. Auto-produce and the live planner must not import this module.
Legacy edit styles stay in the evaluation bucket.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def fcpxml_to_eval_records(xml_text: str, fps: float = 30.0) -> list[dict]:
    """Read clip start and duration from a small FCPXML fragment.

    Times use FCPXML rational seconds (`start="10/30s"`). Records are suitable
    for `score_placement` and are not editorial decisions.
    """
    root = ET.fromstring(xml_text)
    records = []
    for node in root.iter():
        if node.tag not in {"asset-clip", "video", "title", "ref-clip"}:
            continue
        start = _seconds(node.attrib.get("offset") or node.attrib.get("start") or "0s", fps)
        duration = _seconds(node.attrib.get("duration") or "0s", fps)
        if duration <= 0:
            continue
        records.append({
            "template_id": node.attrib.get("ref") or node.tag,
            "start_sec": round(start, 4),
            "end_sec": round(start + duration, 4),
            "name": node.attrib.get("name") or node.tag,
        })
    return records


def _seconds(value: str, fps: float) -> float:
    token = value.strip().rstrip("s")
    if "/" in token:
        numerator, denominator = token.split("/", 1)
        denom = float(denominator or fps or 1)
        return float(numerator) / denom if denom else 0.0
    return float(token or 0)
