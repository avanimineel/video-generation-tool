import json

with open("backend/projects/proj_sub_black_1789484112699/captions.json") as f:
    caps = json.load(f)

for i in range(24, min(33, len(caps))):
    c = caps[i]
    print(f"[{i}] [{c['start']:.2f} - {c['end']:.2f}] '{c['text']}'")
