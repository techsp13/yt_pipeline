import os
import json
import sys
import re

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def prepare_colab_payload():
    pointer_file = r"D:\youtube_automation_agent\Current"
    proj_dir = None
    if os.path.exists(pointer_file):
        try:
            with open(pointer_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                proj_dir = data.get("active_project_dir")
        except Exception:
            pass

    if not proj_dir or not os.path.exists(proj_dir):
        proj_dir = r"D:\youtube_automation_agent\channels\money\the_cola_wars_2026-07-25_131744"

    breakdown_path = os.path.join(proj_dir, "04_Scenes", "Scene_Breakdown.md")
    with open(breakdown_path, "r", encoding="utf-8") as f:
        content = f.read()

    scene_blocks = re.split(r"\*\*V\d+\*\*", content)
    headers = re.findall(r"\*\*V(\d+)\*\*", content)

    colab_scenes = []
    for idx, header in enumerate(headers):
        block = scene_blocks[idx + 1] if idx + 1 < len(scene_blocks) else ""
        num = int(header)
        
        narration_match = re.search(r"\*\*Narration:\*\*\s*\"?(.*?)\"?\n", block, re.DOTALL | re.IGNORECASE)
        if not narration_match:
            narration_match = re.search(r"\*\*Narration:\*\*\s*\"?(.*)", block, re.DOTALL | re.IGNORECASE)
            
        raw_narration = narration_match.group(1).strip() if narration_match else ""
        
        # Clean quotes, newlines, and parenthetical instructions
        clean_text = raw_narration.split("\n")[0].strip().strip('"')
        clean_text = re.sub(r"\([^\)]*\)", "", clean_text).strip()
        
        if clean_text:
            colab_scenes.append({
                "scene": f"Scene_{num:02d}",
                "narration": clean_text
            })

    out_json = os.path.join(proj_dir, "scenes_payload.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(colab_scenes, f, indent=2)

    root_json = r"D:\youtube_automation_agent\scenes_payload.json"
    with open(root_json, "w", encoding="utf-8") as f:
        json.dump(colab_scenes, f, indent=2)

    print(f"✅ Exported {len(colab_scenes)} 100% PURE spoken narrations to scenes_payload.json!")
    return out_json

if __name__ == "__main__":
    prepare_colab_payload()
