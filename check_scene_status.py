import os, json, re
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, '06_Images')
approved_dir = os.path.join(img_dir, 'Approved')
chk_path = os.path.join(proj_dir, '04_Scenes', 'Image_Checkpoints.json')

scenes = youtube_agent.parse_scenes_from_file()
valid_scenes = [s for s in scenes if not youtube_agent.is_title_card_scene(s)]
total_scenes = len(valid_scenes)

checkpoints = {}
if os.path.exists(chk_path):
    try:
        with open(chk_path, 'r', encoding='utf-8') as f:
            checkpoints = json.load(f)
    except Exception:
        pass

approved_scenes = []
remaining_scenes = []

for s in valid_scenes:
    num = f"{s['number']:02d}"
    chk_status = checkpoints.get(num, {}).get('status')
    app_exists = os.path.exists(os.path.join(approved_dir, f"Scene_{num}.png"))
    
    if chk_status == 'approved' or app_exists:
        approved_scenes.append(num)
    else:
        remaining_scenes.append(num)

print(f"TOTAL SCENES: {total_scenes}")
print(f"APPROVED ({len(approved_scenes)}): {approved_scenes}")
print(f"REMAINING ({len(remaining_scenes)}): {remaining_scenes}")
