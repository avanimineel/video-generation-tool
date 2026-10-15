import json

path = "backend/projects/proj_sub_black_1789484112699/captions.json"
with open(path) as f:
    caps = json.load(f)

style_template = caps[20]["style"]
pos_y = caps[20]["pos_y"]
pos_x = caps[20]["pos_x"]

print("Style template:", style_template)
print("pos_x:", pos_x, "pos_y:", pos_y)
