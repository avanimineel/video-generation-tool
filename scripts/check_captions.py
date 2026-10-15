import json

proj = "backend/projects/proj_sub_black_1789484112699"
with open(f"{proj}/translation.json") as f:
    tr = json.load(f)

for seg in tr.get("segments", []):
    s = seg.get("start", 0)
    e = seg.get("end", 0)
    if 20.0 <= s <= 33.0 or 20.0 <= e <= 33.0:
        print(f"[{s:.2f} - {e:.2f}] {seg.get('translated_text', '')} (original: {seg.get('original_text', '')})")
