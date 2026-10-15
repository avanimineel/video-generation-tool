import json

with open("backend/projects/proj_sub_black_1789484112699/captions.json") as f:
    caps = json.load(f)

for i in range(18, 28):
    c = caps[i]
    st = c['start']
    en = c['end']
    txt = c['text']
    print(f"[{i}] [{st:.2f} - {en:.2f}] '{txt}'")
