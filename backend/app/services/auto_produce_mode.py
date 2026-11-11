"""Auto-produce mode + cloud feature flags for local-first EC2.

Env:
  AUTO_PRODUCE_MODE=full|captions_only   (default full; request body can override)
  ENABLE_TWELVE_LABS=1|0                (default 1)
  ENABLE_GEMINI_EDITORIAL=1|0           (default 1)
  ENABLE_STOCK_SEARCH=1|0               (default 1)

Captions-only runs Whisper + translation + layout and stops before Twelve Labs /
Gemini editorial / stock. Full mode requires the enabled cloud features to have
usable keys; otherwise the pipeline finishes captions and returns a clear
opt-in message instead of an opaque planner failure.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

CAPTIONS_ONLY_MESSAGE = (
    "Captions-only complete; enable Twelve Labs/Gemini/stock for full editorial"
)


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def resolve_auto_produce_mode(request_mode: Optional[str] = None) -> str:
    """Request body wins over AUTO_PRODUCE_MODE env; invalid values → full."""
    candidate = (request_mode or os.getenv("AUTO_PRODUCE_MODE") or "full").strip().lower()
    if candidate in ("captions_only", "captions-only", "offline_captions"):
        return "captions_only"
    if candidate in ("full", "auto_edit", "auto-edit"):
        return "full"
    return "full"


def feature_flags() -> Dict[str, bool]:
    return {
        "twelve_labs": _env_flag("ENABLE_TWELVE_LABS", True),
        "gemini_editorial": _env_flag("ENABLE_GEMINI_EDITORIAL", True),
        "stock_search": _env_flag("ENABLE_STOCK_SEARCH", True),
    }


def cloud_readiness() -> Tuple[bool, List[str]]:
    """Whether full editorial can run. Returns (ok, human-readable blockers)."""
    from app.services.editorial_planner import configured_key

    flags = feature_flags()
    blockers: List[str] = []
    if not flags["twelve_labs"]:
        blockers.append("ENABLE_TWELVE_LABS is off")
    elif not configured_key("TWELVE_LABS_API_KEY"):
        blockers.append("TWELVE_LABS_API_KEY is missing or a test placeholder")

    if not flags["gemini_editorial"]:
        blockers.append("ENABLE_GEMINI_EDITORIAL is off")
    elif not configured_key("GEMINI_API_KEY"):
        blockers.append("GEMINI_API_KEY is missing or a test placeholder")

    if not flags["stock_search"]:
        blockers.append("ENABLE_STOCK_SEARCH is off (full editorial B-roll disabled)")

    # Stock off alone still blocks "full" visual pipeline by policy.
    return (len(blockers) == 0, blockers)


def describe_mode(mode: str) -> Dict[str, Any]:
    flags = feature_flags()
    ready, blockers = cloud_readiness() if mode == "full" else (False, [])
    return {
        "auto_produce_mode": mode,
        "feature_flags": flags,
        "cloud_ready": ready if mode == "full" else False,
        "cloud_blockers": blockers if mode == "full" else [],
    }
