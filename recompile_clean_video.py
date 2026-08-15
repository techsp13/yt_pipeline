import os
import sys
import json
import subprocess
import shutil

proj_dir = r"D:\youtube_automation_agent\channels\history\why_ancient_human_do_drug_2026-07-24_210849"

# Set active project directory
active_pointer = r"D:\youtube_automation_agent\active_project.json"
with open(active_pointer, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": proj_dir}, f, indent=4)

# Set state step to 10 in Project_Config.json
cfg_file = os.path.join(proj_dir, "Project_Config.json")
with open(cfg_file, "r", encoding="utf-8") as f:
    state = json.load(f)

state["step"] = 10
with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4)

# Remove old invalid checkpoints/metadata for the 12 cleared scenes so they re-render cleanly
cleared_scenes = [158, 161, 163, 165, 166, 169, 170, 172, 174, 175, 177, 180]
for num in cleared_scenes:
    scene_num = f"{num:02d}"
    meta_path = os.path.join(proj_dir, "14_Checkpoints", f"Scene_{scene_num}_Metadata.json")
    voice_path = os.path.join(proj_dir, "07_Voice", f"Scene_{scene_num}_Voice.mp3")
    if os.path.exists(meta_path):
        os.remove(meta_path)
    if os.path.exists(voice_path):
        os.remove(voice_path)

print("Active project pointer set to why_ancient_human_do_drug and step set to 10.")
print("Cleared metadata for duplicated audio scenes. Ready to run video compilation.")
