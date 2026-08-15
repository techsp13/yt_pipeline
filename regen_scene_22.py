import os, sys, random
import youtube_agent
import gflow_assistant
import telegram_bot

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, '06_Images')
rejected_dir = os.path.join(img_dir, 'Rejected')
os.makedirs(rejected_dir, exist_ok=True)

# 1. Move existing Scene 22 images to Rejected
for f in os.listdir(img_dir):
    if f.startswith('Scene_22_') or f.startswith('Scene_022_'):
        src = os.path.join(img_dir, f)
        if os.path.isfile(src):
            try:
                os.rename(src, os.path.join(rejected_dir, f))
                print(f"Moved {f} to Rejected.")
            except Exception as e:
                print(f"Error moving {f}: {e}")

# 2. Get next version number
version = youtube_agent.get_next_image_version('22')
new_filename = f"Scene_22_v{version}.png"
new_path = os.path.join(img_dir, new_filename)

# 3. Get prompt
scenes = youtube_agent.parse_scenes_from_file()
scene_22 = next((s for s in scenes if s['number'] == 22), None)
if not scene_22:
    print("Error: Scene 22 not found in breakdown!")
    sys.exit(1)

prompt = scene_22['image_prompt'] + f" (Variation seed: {random.randint(1000, 999999)})"

print(f"Regenerating Scene 22 (v{version}) via Google Flow Imagen 4...")
success = gflow_assistant.generate_imagen_image(prompt, new_path)

if success and os.path.exists(new_path):
    print(f"SUCCESS! New Scene 22 image saved to {new_path}")
    telegram_bot.send_photo(photo_path=new_path, caption=f"🔄 *Regenerated Scene V22 (v{version})*\n\"{scene_22.get('narration')}\"")
    print("Sent photo to Telegram!")
else:
    print("Failed to generate image via gflow!")
