"""
Spatial Framing & Auto-Centering Service powered by Google Gemini (Argon / 3.5 Flash).
Analyzes visual media (images & video frames) to locate primary subjects
(faces, dental/medical regions, monuments, text) and calculates optimal
9:16 vertical crop coordinates (pos_x, pos_y, scale).
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from PIL import Image

logger = logging.getLogger(__name__)

PRIMARY_MODEL = os.getenv("ARGON_MODEL", "gemini-4-argon")
FALLBACK_MODEL = os.getenv("EDITORIAL_MODEL", "gemini-3.5-flash")

def analyze_spatial_framing(
    image_path: str,
    context_hint: str = "primary subject or speaker",
    preferred_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes an image and returns optimal 9:16 vertical crop anchors (pos_x, pos_y, scale).
    pos_x: 0.0 (left) to 1.0 (right), 0.5 is center.
    pos_y: 0.0 (top) to 1.0 (bottom), 0.5 is center.
    """
    if not os.path.exists(image_path):
        return {"pos_x": 0.5, "pos_y": 0.5, "scale": 1.0, "reason": "file_not_found"}

    from app.core.config import get_provider_key
    api_key = get_provider_key("GEMINI_API_KEY")
    if not api_key:
        return {"pos_x": 0.5, "pos_y": 0.5, "scale": 1.0, "reason": "no_api_key"}

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        pil_img = Image.open(image_path)
        w, h = pil_img.size

        prompt = f"""
You are an expert video editor reframing landscape (16:9) or arbitrary media into a vertical (9:16) crop.
Analyze the image with special attention to: {context_hint}.
Identify the primary visual focal point (e.g. face, teeth, body, monument, action).
Return ONLY a valid JSON object with:
{{
  "pos_x": <float between 0.0 and 1.0, horizontal focal centroid, 0.5 is center>,
  "pos_y": <float between 0.0 and 1.0, vertical focal centroid, 0.5 is center>,
  "scale": <float between 1.0 and 1.5, recommended zoom>,
  "subject_detected": "<short description of focal subject>",
  "rationale": "<why this framing centers the key subject in 9:16>"
}}
"""
        models_to_try = [preferred_model] if preferred_model else [PRIMARY_MODEL, FALLBACK_MODEL, "gemini-3.5-flash-lite"]
        models_to_try = [m for m in models_to_try if m]

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[pil_img, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                if response and response.text:
                    data = json.loads(response.text)
                    data["model_used"] = model_name
                    # Clamp values
                    data["pos_x"] = max(0.0, min(1.0, float(data.get("pos_x", 0.5))))
                    data["pos_y"] = max(0.0, min(1.0, float(data.get("pos_y", 0.5))))
                    data["scale"] = max(1.0, min(2.0, float(data.get("scale", 1.0))))
                    return data
            except Exception as e:
                logger.warning(f"Spatial framing failed with model {model_name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in spatial framing analysis: {e}")

    return {"pos_x": 0.5, "pos_y": 0.5, "scale": 1.0, "reason": "fallback_default"}
