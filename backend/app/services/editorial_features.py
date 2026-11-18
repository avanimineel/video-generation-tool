"""Shot cuts and speech-energy samples for placement.

These run before the planner snap. A missing binary or a failed probe returns
empty features. The live planner still places the cue.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Optional

from app.services.editorial_placement import annotate_emphasis


def scene_cuts_from_showinfo(log_text: str) -> list[float]:
    times = []
    for match in re.finditer(r"pts_time:([0-9.]+)", log_text):
        times.append(round(float(match.group(1)), 4))
    return times


def detect_shot_cuts(path: str, threshold: float = 0.4) -> list[float]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path:
        return []
    try:
        completed = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path, "-filter:v", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return scene_cuts_from_showinfo(completed.stderr)


def rms_samples_from_astats(log_text: str, hop: float = 0.1) -> list[tuple[float, float]]:
    values = [float(match) for match in re.findall(r"RMS level dB: (-?[0-9.]+|inf|-inf)", log_text)]
    samples = []
    for index, decibel in enumerate(values):
        if decibel < -90:
            linear = 0.0
        else:
            linear = 10 ** (decibel / 20)
        samples.append((round(index * hop, 4), linear))
    return samples


def sample_speech_rms(path: str) -> list[tuple[float, float]]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path:
        return []
    try:
        completed = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", path, "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"],
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return rms_samples_from_astats(completed.stderr + completed.stdout)


def attach_placement_features(state, words: Optional[list[dict]] = None) -> dict:
    """Cache shot cuts on the project. Emphasis is computed for the supplied words."""
    ingestion = dict(getattr(state, "ai_ingestion", None) or {})
    path = getattr(state, "source_media_path", None) or ""
    if "shot_cuts" not in ingestion:
        ingestion["shot_cuts"] = detect_shot_cuts(path)
    if words:
        samples = sample_speech_rms(path) if path else []
        ingestion["word_features"] = annotate_emphasis(words, samples)
    ingestion["placement_features_ready"] = True
    state.ai_ingestion = ingestion
    return ingestion
