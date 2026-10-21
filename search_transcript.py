import json, os

transcript_path = r"C:\Users\BTSRIHARI\.gemini\antigravity\brain\6b61b4ad-3921-4f9d-ab5e-298825c0289f\.system_generated\logs\transcript.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        if data.get("type") == "USER_INPUT":
            content = data.get("content", "")
            media = data.get("media", [])
            step = data.get("step_index")
            if any(k in content.lower() for k in ["teammate", "two pages", "guide", "pdf", "organ"]):
                print(f"=== STEP {step} ===")
                print(content[:300])
                if media:
                    print("MEDIA:", media)
