import json

with open(r"D:\youtube_automation_agent\channels\history\The_Man_Who_Hid_Inside_a_Giant_Jar_During_an_Ancie_2026-09-08_154017\04_Scenes\Scene_List.json", "r", encoding="utf-8") as f:
    scenes = json.load(f)

for num in [20, 81, 218]:
    for s in scenes:
        if s["number"] == num:
            print(f"=== Scene {num} ===")
            print("Prompt:", s.get("image_prompt", "")[:100])
            print("Narration:", repr(s.get("narration")))
