import json, re

ACTIVE_PROJ = r"D:\youtube_automation_agent\channels\history\The_Man_Who_Hid_Inside_a_Giant_Jar_During_an_Ancie_2026-09-08_154017"
SCRIPT_JSON = rf"{ACTIVE_PROJ}\04_Scenes\Scene_List.json"

with open(SCRIPT_JSON, encoding="utf-8") as f:
    scenes = json.load(f)

# Find first scene with actual narration
first_narr_idx = 0
for idx, sc in enumerate(scenes):
    narr = re.sub(r"\[.*?\]", "", sc.get("narration", "")).strip()
    if narr:
        first_narr_idx = idx
        break

print(f"First scene with narration is index {first_narr_idx} (Scene number: {scenes[first_narr_idx]['number']}): '{scenes[first_narr_idx]['narration'][:40]}'")
print(f"Skipped leading silent scenes: {[scenes[i]['number'] for i in range(first_narr_idx)]}")
