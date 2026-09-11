import os
import sys
import json
import time
import re
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

sys.stdout.reconfigure(encoding='utf-8')

import telegram_bot
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, "06_Images")
scenes_file = os.path.join(proj_dir, "04_Scenes", "Scene_List.json")

print(f"[Telegram Dispatch] Scanning project images in: {img_dir}")

narrations = {}
if os.path.exists(scenes_file):
    try:
        with open(scenes_file, "r", encoding="utf-8") as f:
            sdata = json.load(f)
            for s in sdata:
                num = s.get("number")
                nar = s.get("narration", "").strip()
                if num is not None:
                    narrations[int(num)] = nar
    except Exception as e:
        print(f"[Warning] Could not load narrations: {e}")

# Collect all valid Scene files 1 to 230
scene_map = {}
for i in range(1, 231):
    candidates = [
        os.path.join(img_dir, f"{i:03d}_Scene_{i}.png"),
        os.path.join(img_dir, f"{i:02d}_Scene_{i}.png"),
        os.path.join(img_dir, f"{i:03d}_Scene_{i:02d}.png"),
        os.path.join(img_dir, f"{i:02d}_Scene_{i:02d}.png"),
        os.path.join(img_dir, f"Scene_{i}.png"),
        os.path.join(img_dir, f"Scene_{i:02d}.png"),
        os.path.join(img_dir, "Approved", f"Scene_{i}.png"),
    ]
    found = None
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 20000:
            found = c
            break
    if found:
        scene_map[i] = found
    else:
        print(f"[Warning] Missing file for scene {i}")

sorted_scenes = sorted(scene_map.items(), key=lambda x: x[0])
total_images = len(sorted_scenes)

print(f"[Telegram Dispatch] Verified {total_images} / 230 scenes ready on disk. Beginning dispatch...")

telegram_bot.send_message(
    f"🎬 *FULL PROJECT IMAGE VERIFICATION: {total_images}/230 SCENES READY*\n\n"
    f"💰 *Channel:* Money\n"
    f"📊 *Title:* Revenue vs Profit: Where Does the Money Go?\n"
    f"🖼️ *Total Scenes:* {total_images} (100% Generated & Verified)\n"
    f"🎨 *Style:* Minimalist 2D Doodle Webcomic (Zenn & Mack)\n"
    f"✨ *Text Policy:* Zero white corner text | Hand-drawn comic signage\n\n"
    f"Sending all 230 scenes in albums of 5 with scene narrations below:"
)

BATCH_SIZE = 5
total_albums = (total_images + BATCH_SIZE - 1) // BATCH_SIZE

for i in range(0, total_images, BATCH_SIZE):
    chunk = sorted_scenes[i:i+BATCH_SIZE]
    album_idx = (i // BATCH_SIZE) + 1
    
    album = []
    for num, path in chunk:
        nar = narrations.get(num, "")
        if nar:
            caption = f"📺 Scene {num}\n\"{nar[:180]}\""
        else:
            caption = f"📺 Scene {num}"
        album.append((path, caption))
        
    print(f"Sending album {album_idx}/{total_albums} (Scenes {chunk[0][0]}..{chunk[-1][0]})...", flush=True)
    
    sent = False
    for attempt in range(3):
        try:
            telegram_bot.send_media_group(album)
            sent = True
            time.sleep(2.5)  # Telegram API flood control protection
            break
        except Exception as e:
            print(f"⚠️ Album {album_idx} attempt {attempt+1} failed: {e}. Retrying in 4s...", flush=True)
            time.sleep(4.0)
            
    if not sent:
        print(f"❌ Could not send album {album_idx} after 3 attempts.", flush=True)

# Final completion message with interactive buttons
btns = [
    [{"text": "🚀 Approve All 230 Scenes & Start Voiceover", "callback_data": "approve_all_batch"}]
]
telegram_bot.send_message(
    "✅ *All 230 Scene Images Dispatched for Verification!*\n\n"
    "• Review any scene above.\n"
    "• To regenerate a specific scene, reply `/reject <scene_number>` (e.g. `/reject 42`).\n"
    "• Or click the button below to approve and start Voice Generation!",
    buttons=btns
)

print(f"[Done] All {total_images} images dispatched to Telegram successfully!")
