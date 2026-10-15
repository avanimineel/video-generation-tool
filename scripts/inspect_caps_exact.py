import json

with open("backend/projects/proj_sub_black_1789484112699/captions.json") as f:
    caps = json.load(f)

for i in range(18, 29):
    c = caps[i]
    print(f"--- Index {i} ---")
    print("id:", c.get("id"))
    print("start:", c.get("start"), "end:", c.get("end"))
    print("text:", c.get("text"))
    print("words:", [(w["word"], w["start"], w["end"]) for w in c.get("words", [])])
