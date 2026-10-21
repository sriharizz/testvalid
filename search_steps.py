import json

transcript_path = r"C:\Users\BTSRIHARI\.gemini\antigravity\brain\6b61b4ad-3921-4f9d-ab5e-298825c0289f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        step = data.get("step_index")
        if step in [2848, 2850, 2852, 2854, 2858, 2860, 2862, 2868]:
            print(f"*** STEP {step} ***")
            print(data.get("content"))
            if data.get("media"):
                print("MEDIA:", data.get("media"))
