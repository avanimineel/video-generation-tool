"""Accepted Hindi-to-English pairs for a later training job.

The same video keeps using its saved captions. This file is only the input a
separate training run may read. It does not change Whisper or NLLB weights.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings


def pairs_path():
    return settings.projects_dir / "accepted_translation_pairs.jsonl"


def record_accepted_pair(
    source_text: str,
    english: str,
    *,
    domain: Optional[str] = None,
    project_id: str = "",
    start_sec: Optional[float] = None,
    end_sec: Optional[float] = None,
    origin: str = "repair",
) -> bool:
    """Append one accepted pair. A repeat of the same Hindi and English is skipped."""
    if os.getenv("COMPANION_TEST_MODE") == "1":
        return False
    source = " ".join((source_text or "").split())
    rendered = " ".join((english or "").split())
    if not source or not rendered:
        return False
    path = pairs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            seen.add((row.get("source_text"), row.get("english")))
    key = (source, rendered)
    if key in seen:
        return False
    row: Dict[str, Any] = {
        "source_text": source,
        "english": rendered,
        "domain": (domain or "general").strip().lower(),
        "project_id": project_id,
        "origin": origin,
        "at": datetime.utcnow().isoformat(),
    }
    if start_sec is not None:
        row["start_sec"] = round(float(start_sec), 3)
    if end_sec is not None:
        row["end_sec"] = round(float(end_sec), 3)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return True
