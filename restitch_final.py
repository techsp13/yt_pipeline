import os
import sys

proj_dir = r"D:\youtube_automation_agent\channels\science\NASAs_Twin_Study_2026-07-25_230010"

# Set step to 10 in Project_Config.json
cfg_path = os.path.join(proj_dir, "Project_Config.json")
if os.path.exists(cfg_path):
    import json
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["step"] = 10
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
    print("[SUCCESS] Set project step to 10!")

# Delete old compiled Scene_228 video clip if it exists in output_temp
temp_dir = os.path.join(proj_dir, "output_temp")
if os.path.exists(temp_dir):
    for f in os.listdir(temp_dir):
        if "228" in f:
            try:
                os.remove(os.path.join(temp_dir, f))
                print(f"[CLEARED] Removed old temp clip: {f}")
            except Exception:
                pass

print("[READY] Step 10 ready for clean video compilation!")
