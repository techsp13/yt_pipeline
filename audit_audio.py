import os
import re
import json

proj_dir = r"D:\youtube_automation_agent\channels\history\why_ancient_human_do_drug_2026-07-24_210849"
breakdown_file = os.path.join(proj_dir, "04_Scenes", "Scene_Breakdown.md")

with open(breakdown_file, "r", encoding="utf-8") as f:
    content = f.read()

scene_blocks = re.split(r"\*\*V\d+\*\*", content)
headers = re.findall(r"\*\*V(\d+)\*\*", content)

scenes = []
for idx, header in enumerate(headers):
    block = scene_blocks[idx + 1] if idx + 1 < len(scene_blocks) else ""
    num = int(header)
    m = re.search(r"\*\*Narration:\*\*\s*\"?(.*?)\"?\n", block, re.IGNORECASE)
    narr = m.group(1).strip() if m else ""
    scenes.append((num, narr))

print(f"Total scenes parsed: {len(scenes)}")

seen = {}
duplicates = []
for num, narr in scenes:
    if not narr:
        continue
    clean_narr = narr.strip('"').strip()
    if clean_narr in seen:
        duplicates.append((num, seen[clean_narr], clean_narr))
    else:
        seen[clean_narr] = num

print(f"Duplicate narration sentences found in Scene_Breakdown.md: {len(duplicates)}")
for curr_num, orig_num, text in duplicates:
    print(f"  - Scene V{curr_num:02d} duplicates Scene V{orig_num:02d}: \"{text}\"")

# Check if script itself has duplicated Acts or sections
script_file = os.path.join(proj_dir, "03_Script", "Final_Script.md")
if os.path.exists(script_file):
    with open(script_file, "r", encoding="utf-8") as f:
        script_text = f.read()
    print(f"\nFinal_Script.md length: {len(script_text)} characters")
    acts = re.findall(r"### ACT \d+:.*", script_text)
    print("Acts found in Final_Script.md:")
    for a in acts:
        print("  -", a)
