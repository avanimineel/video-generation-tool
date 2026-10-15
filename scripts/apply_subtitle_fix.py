import json
import os

projects_to_update = [
    "backend/projects/proj_sub_black_1789484112699",
    "backend/projects/proj_sub_black_1789478878370",
    "backend/projects/proj_sub_1789475711388"
]

for pdir in projects_to_update:
    cpath = os.path.join(pdir, "captions.json")
    if not os.path.exists(cpath):
        continue
    with open(cpath) as f:
        caps = json.load(f)

    # Find starting point around 23.0s - 24.0s where "Half" occurs
    start_idx = None
    end_idx = None
    for i, c in enumerate(caps):
        txt = c.get("text", "").lower()
        st = c.get("start", 0)
        en = c.get("end", 0)
        if start_idx is None and 22.8 <= st <= 24.5 and "half" in txt:
            start_idx = i
        if start_idx is not None and 33.0 <= en <= 35.5:
            end_idx = i + 1

    if start_idx is None or end_idx is None:
        print(f"Skipping {pdir}, start_idx={start_idx}, end_idx={end_idx}")
        continue

    print(f"Updating {pdir}: replacing captions {start_idx} to {end_idx} (count: {end_idx - start_idx})")
    style_template = caps[start_idx].get("style", {})
    pos_x = caps[start_idx].get("pos_x", 0.5)
    pos_y = caps[start_idx].get("pos_y", 0.56)

    def kw(word, start, end, is_k=False, cat=None, col=None):
        return {
            "word": word,
            "start": round(start, 2),
            "end": round(end, 2),
            "highlight": False,
            "is_keyword": is_k,
            "keyword_category": cat,
            "keyword_color": col,
            "keyword_font": "Playfair Display" if is_k else None
        }

    new_segments = [
        {
            "id": f"cap_wh_fix_2304_{pdir[-4:]}",
            "start": 23.04,
            "end": 24.84,
            "text": "Half the people mistake it for TB,",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("Half", 23.04, 23.60),
                kw("the", 23.60, 23.85),
                kw("people", 23.85, 24.20),
                kw("mistake", 24.20, 24.45),
                kw("it", 24.45, 24.55),
                kw("for", 24.55, 24.65),
                kw("TB,", 24.65, 24.84, True, "condition", "#FF4D4D")
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "Half the people mistake it for TB,"
        },
        {
            "id": f"cap_wh_fix_2484_{pdir[-4:]}",
            "start": 24.84,
            "end": 26.50,
            "text": "and start taking TB medication.",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("and", 24.84, 25.10),
                kw("start", 25.10, 25.45),
                kw("taking", 25.45, 25.80),
                kw("TB", 25.80, 26.15, True, "condition", "#FF4D4D"),
                kw("medication.", 26.15, 26.50, True, "treatment", "#00E5FF")
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "and start taking TB medication."
        },
        {
            "id": f"cap_wh_fix_2650_{pdir[-4:]}",
            "start": 26.50,
            "end": 28.40,
            "text": "Others treat it as a lung infection,",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("Others", 26.50, 26.85),
                kw("treat", 26.85, 27.20),
                kw("it", 27.20, 27.40),
                kw("as", 27.40, 27.55),
                kw("a", 27.55, 27.65),
                kw("lung", 27.65, 27.95, True, "organ", "#CCFF00"),
                kw("infection,", 27.95, 28.40, True, "condition", "#FF4D4D")
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "Others treat it as a lung infection,"
        },
        {
            "id": f"cap_wh_fix_2840_{pdir[-4:]}",
            "start": 28.40,
            "end": 30.16,
            "text": "and take no treatment at all.",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("and", 28.40, 28.70),
                kw("take", 28.70, 29.05),
                kw("no", 29.05, 29.35),
                kw("treatment", 29.35, 29.75, True, "treatment", "#00E5FF"),
                kw("at", 29.75, 29.95),
                kw("all.", 29.95, 30.16)
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "and take no treatment at all."
        },
        {
            "id": f"cap_wh_fix_3034_{pdir[-4:]}",
            "start": 30.34,
            "end": 32.02,
            "text": "And many patients, without",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("And", 30.34, 30.64),
                kw("many", 30.64, 31.02),
                kw("patients,", 31.02, 31.76),
                kw("without", 31.76, 32.02)
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "And many patients, without"
        },
        {
            "id": f"cap_wh_fix_3202_{pdir[-4:]}",
            "start": 32.02,
            "end": 33.38,
            "text": "ever being diagnosed,",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("ever", 32.02, 32.35),
                kw("being", 32.35, 32.70),
                kw("diagnosed,", 32.70, 33.38)
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "ever being diagnosed,"
        },
        {
            "id": f"cap_wh_fix_3338_{pdir[-4:]}",
            "start": 33.38,
            "end": 34.80,
            "text": "pass away from lung cancer.",
            "pos_x": pos_x,
            "pos_y": pos_y,
            "words": [
                kw("pass", 33.38, 33.68),
                kw("away", 33.68, 33.98),
                kw("from", 33.98, 34.18),
                kw("lung", 34.18, 34.45, True, "organ", "#CCFF00"),
                kw("cancer.", 34.45, 34.80, True, "condition", "#FF4D4D")
            ],
            "style": style_template,
            "source_language": "en",
            "translated_text": "pass away from lung cancer."
        }
    ]

    updated_caps = caps[:start_idx] + new_segments + caps[end_idx:]
    with open(cpath, "w") as f:
        json.dump(updated_caps, f, indent=2)
    print(f"Successfully updated {cpath}! Old count: {len(caps)}, New count: {len(updated_caps)}")
