"""
gen_dynamic_short_breakdown.py
"""
import os, sys, json

proj_dir = r"D:\youtube_automation_agent\channels\history\How_Did_Ancient_People_Stay_Cool_Without_Electrici_2026-08-11_084945"
sys.path.insert(0, r"D:\youtube_automation_agent")

active_json = r"D:\youtube_automation_agent\active_project.json"
with open(active_json, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": proj_dir}, f, indent=4)

from creative_assistant import generate_short_breakdown

script_p = os.path.join(proj_dir, "03_Script", "Final_Script.md")
with open(script_p, "r", encoding="utf-8") as f:
    script_txt = f.read()

print("Generating dynamic Short breakdown based on script length...")
short_json_str = generate_short_breakdown(script_txt)

# Clean json wrappers
if short_json_str.startswith("```"):
    import re
    short_json_str = re.sub(r"^```(?:json)?\n|```$", "", short_json_str, flags=re.MULTILINE).strip()

short_breakdown = json.loads(short_json_str)

shorts_dir = os.path.join(proj_dir, "18_Short_Video")
os.makedirs(shorts_dir, exist_ok=True)
breakdown_path = os.path.join(shorts_dir, "Short_Breakdown.json")

with open(breakdown_path, "w", encoding="utf-8") as f:
    json.dump(short_breakdown, f, indent=4)

print(f"\nSUCCESS! Generated {len(short_breakdown)} dynamic scenes for YouTube Short!")
for i, sc in enumerate(short_breakdown):
    narr = sc.get("narration", "")
    prompt = sc.get("image_prompt", "")[:60]
    print(f"  Scene {i+1}: Narration=\"{narr}\"\n           Prompt=\"{prompt}...\"")
