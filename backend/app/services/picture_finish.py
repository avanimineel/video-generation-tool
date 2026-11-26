"""Picture grade, voice cleanup, and the vertical export size.

The short-form agents decide what appears. This module finishes the picture and the voice
at export, where the frames and the audio actually meet.
"""
from __future__ import annotations

VOICE_CLEANUP = "highpass=f=80,afftdn=nr=6:nf=-25,loudnorm=I=-14:TP=-1.5:LRA=11"


def export_preset(portrait: bool) -> dict:
    """One delivery size for Reels, TikTok, and Shorts. Landscape stays 720p."""
    if portrait:
        return {"platform": "reels", "width": 1080, "height": 1920, "fps": 30, "bitrate": "8000k", "paint_width": 720, "paint_height": 1280}
    return {"platform": "landscape", "width": 1280, "height": 720, "fps": 30, "bitrate": "5000k", "paint_width": 1280, "paint_height": 720}


def grade_frame(image, pack: str):
    """A light correction. Documentary stays neutral. Direct response warms slightly. Skin is not crushed."""
    from PIL import Image, ImageEnhance
    image = image.convert("RGB")
    if pack == "direct_response":
        image = ImageEnhance.Contrast(image).enhance(1.04)
        image = ImageEnhance.Color(image).enhance(1.04)
        warm = Image.new("RGB", image.size, (255, 220, 190))
        return Image.blend(image, warm, 0.05)
    if pack == "documentary":
        image = ImageEnhance.Contrast(image).enhance(1.03)
        return ImageEnhance.Color(image).enhance(0.98)
    return ImageEnhance.Contrast(image).enhance(1.02)
