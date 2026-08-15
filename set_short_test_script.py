import os
import json

proj_dir = r"D:\youtube_automation_agent\channels\science\why_ocean_salty_2026-07-28_210115"
script_dir = os.path.join(proj_dir, "03_Script")
os.makedirs(script_dir, exist_ok=True)

short_script = """## Why Is The Ocean Salty?

**[0:00 - Scene 1]**
Have you ever wondered why the ocean is salty? Rain falls on rocks, dissolving minerals and washing salt into rivers.

**[0:05 - Scene 2]**
Over billions of years, rivers carried millions of tons of salt into the sea, turning our oceans salty today!
"""

with open(os.path.join(script_dir, "Script_Draft.txt"), "w", encoding="utf-8") as f:
    f.write(short_script)
with open(os.path.join(script_dir, "Final_Script.md"), "w", encoding="utf-8") as f:
    f.write(short_script)

print("Short 2-scene test script saved!")

# Update Project_Config.json to Step 5
cfg_path = os.path.join(proj_dir, "Project_Config.json")
if os.path.exists(cfg_path):
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["script"] = short_script
    cfg["step"] = 5
    cfg["active"] = True
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
    print("Project_Config.json updated to Step 5.")

state_path = r"D:\youtube_automation_agent\agent_state.json"
with open(state_path, "r", encoding="utf-8") as f:
    st = json.load(f)
st["script"] = short_script
st["step"] = 5
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(st, f, indent=4)
print("agent_state.json updated to Step 5.")
