import json
for p in ["backend/projects/proj_sub_black_1789478878370", "backend/projects/proj_sub_1789475711388"]:
    try:
        with open(f"{p}/captions.json") as f:
            caps = json.load(f)
        print(p, "captions around 23s:")
        for i, c in enumerate(caps):
            st = c.get("start", 0)
            en = c.get("end", 0)
            txt = c.get("text", "")
            if 21.0 <= st <= 26.0:
                print(f"  [{i}] {st}-{en}: {txt}")
    except Exception as e:
        print(p, "error:", e)
