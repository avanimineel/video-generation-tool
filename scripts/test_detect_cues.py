import json
import sys
sys.path.insert(0, "backend")
from app.services.transcription_service import transcription_service
from app.core.models import CaptionItem

with open("backend/projects/proj_sub_black_1789484112699/captions.json") as f:
    raw_caps = json.load(f)

captions = [CaptionItem(**c) for c in raw_caps]
cues, graphics, rlog = transcription_service.detect_dimensions_and_cues(captions)
print(f"Detected {len(cues)} cues, {len(graphics)} graphics, {len(rlog)} reasoning logs.")
for i, r in enumerate(rlog[:5]):
    t_name = r.get("template_name")
    t_fmt = r.get("timestamp_formatted")
    dur = r.get("duration_sec")
    phrase = r.get("spoken_trigger_phrase")
    term = r.get("trigger_term")
    cat = r.get("cue_category")
    print(f"\n--- Cue {i+1}: {t_name} @ {t_fmt} ({dur}s) ---")
    print(f"Trigger Phrase: \"{phrase}\" [Term: {term}]")
    print(f"Category: {cat}")
    print(f"Timestamp Logic: {r.get('timestamp_logic')}")
    print(f"Image Logic: {r.get('image_logic')}")
    print(f"Layout Logic: {r.get('layout_logic')}")
    print(f"Pacing Logic: {r.get('pacing_logic')}")
