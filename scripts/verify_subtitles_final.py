import json

path = "backend/projects/proj_sub_black_1789484112699/captions.json"
with open(path) as f:
    caps = json.load(f)

print("=== VERIFYING SUBTITLES 20.0s - 35.0s ===")
for i, c in enumerate(caps):
    st = c.get("start", 0)
    en = c.get("end", 0)
    if 20.0 <= st <= 35.0 or 20.0 <= en <= 35.0:
        words_str = " ".join(f"{w['word']}({w['start']:.2f}-{w['end']:.2f})" for w in c.get("words", []))
        print(f"[{i:02d}] [{st:05.2f} - {en:05.2f}] \"{c.get('text')}\"")
        print(f"     Words: {words_str}")
