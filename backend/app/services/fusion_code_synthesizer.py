"""
Generative DaVinci Fusion Composition Synthesizer powered by Google Gemini (Argon / 3.5 Flash).
Synthesizes professional Lua/Fusion .comp node trees tailored to specific spoken dialogue beats,
kinetic titles, stats, or anatomical graphics.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PRIMARY_MODEL = os.getenv("ARGON_MODEL", "gemini-4-argon")
FALLBACK_MODEL = os.getenv("EDITORIAL_MODEL", "gemini-3.5-flash")

def synthesize_fusion_composition(
    dialogue_context: str,
    graphic_type: str = "kinetic_title",
    aspect_ratio: str = "9:16",
    fps: float = 30.0,
    duration_frames: int = 90
) -> Dict[str, Any]:
    """
    Synthesizes a production-grade DaVinci Resolve Fusion composition (.comp format)
    for high-retention vertical short-form editing.
    """
    from app.core.config import get_provider_key
    api_key = get_provider_key("GEMINI_API_KEY")
    if not api_key:
        return {"success": False, "error": "missing_api_key"}

    prompt = f"""
You are an expert Blackmagic DaVinci Resolve Fusion VFX and Motion Graphics compositor.
Generate a high-retention, clean, professional Fusion composition node tree for a {aspect_ratio} video at {fps} fps ({duration_frames} frames duration).

Dialogue Beat / Visual Goal:
"{dialogue_context}"

Graphic Type: {graphic_type}

Design Requirements:
1. Target resolution: 1080x1920 (vertical 9:16).
2. Clean typography with subtle drop shadow, background card/pill if appropriate, and smooth easing keyframes (In/Out cubic bezier).
3. Connect outputs through a Merge node to MediaOut1.
4. Return ONLY a valid JSON object with:
{{
  "title": "<Short descriptive name>",
  "fusion_lua_comp": "<Valid Fusion composition Lua string starting with Composition {{ ... }}>",
  "summary_nodes": ["<List of key nodes used, e.g. TextPlus, Background, Transform, Merge>"],
  "design_rationale": "<Explanation of motion design>"
}}
"""

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL, "gemini-3.5-flash-lite"]

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                if response and response.text:
                    data = json.loads(response.text)
                    data["model_used"] = model_name
                    data["success"] = True
                    return data
            except Exception as e:
                logger.warning(f"Fusion synthesis failed on {model_name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in Fusion code synthesis: {e}")

    return {
        "success": False,
        "error": "Failed to synthesize composition with available models"
    }
