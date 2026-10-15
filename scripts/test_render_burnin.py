import urllib.request
import json
import time

url = "http://localhost:8002/api/media/proj_sub_black_1789484112699/render-burnin"
data = {"subtitles_only": True, "force_rerender": True}
req = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
print("Triggering burn-in render...")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print("Burn-in response:", res)

for i in range(25):
    time.sleep(2)
    p_url = "http://localhost:8002/api/media/proj_sub_black_1789484112699/render-progress"
    with urllib.request.urlopen(p_url) as p_resp:
        p_data = json.loads(p_resp.read().decode())
        pct = p_data.get("percent")
        status = p_data.get("status")
        print(f"Poll {i+1}: {pct}% | status={status}")
        if status == "completed":
            print("Render completed successfully!")
            break
