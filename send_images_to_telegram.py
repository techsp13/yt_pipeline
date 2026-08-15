import os
import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

import telegram_bot
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, "06_Images")

print(f"Scanning images in: {img_dir}")

# Collect all valid Scene_XX_vY.png or .jpg files
files = [f for f in os.listdir(img_dir) if (f.startswith("Scene_") or f.endswith(".png") or f.endswith(".jpg")) and os.path.isfile(os.path.join(img_dir, f)) and os.path.getsize(os.path.join(img_dir, f)) > 1000]

# Group by scene number to get the latest image for each scene
scene_map = {}
for f in files:
    # Try to extract scene number e.g. Scene_05_v1.png -> 05
    import re
    m = re.search(r"Scene_(\d+)", f)
    if m:
        s_num = f"{int(m.group(1)):02d}"
        path = os.path.join(img_dir, f)
        if s_num not in scene_map or os.path.getmtime(path) > os.path.getmtime(scene_map[s_num]):
            scene_map[s_num] = path

sorted_scenes = sorted(scene_map.items(), key=lambda x: int(x[0]))
total_images = len(sorted_scenes)

print(f"Found {total_images} unique scene images. Sending to Telegram in albums of 5...")
telegram_bot.send_message(f"📸 *Sending {total_images} existing local images for verification...*")

for i in range(0, total_images, 5):
    chunk = sorted_scenes[i:i+5]
    album = [(path, f"📺 *Scene V{num}*") for num, path in chunk]
    print(f"Sending album {i//5 + 1} ({len(chunk)} images: Scenes {chunk[0][0]}..{chunk[-1][0]})...")
    try:
        telegram_bot.send_media_group(album)
        time.sleep(1.5)  # Telegram API rate limit protection
    except Exception as e:
        print(f"Error sending album: {e}")

telegram_bot.send_message("✅ *All local images sent to Telegram!* Reply `/reject N` to regenerate any scene, or `/approve` to continue.")
print("Done sending all images!")
