import os
import sys
import json
import time
import shutil
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

import youtube_agent
import gflow_assistant
import telegram_bot

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, "06_Images")

scenes = youtube_agent.parse_scenes_from_file()
valid_scenes = [s for s in scenes if not youtube_agent.is_title_card_scene(s)]

gap_nums = ["20", "21", "22", "25", "26", "27", "28", "38"]
target_scenes = [s for s in valid_scenes if f"{s['number']:02d}" in gap_nums]

if not target_scenes:
    # If gaps completed, take next 5 scenes after 116
    target_scenes = [s for s in valid_scenes if s['number'] >= 117][:5]

print(f"Targeting {len(target_scenes)} scenes for parallel generation...")
batch = []
for s in target_scenes:
    num = f"{s['number']:02d}"
    padded_filename = f"{s['number']:03d}_Scene_{num}.png"
    out_path = os.path.join(img_dir, padded_filename)
    
    cfg = youtube_agent.get_channel_config()
    style_suffix = cfg["widescreen_suffix"]
    BG_COLORS = ["baby blue", "lemon yellow", "soft purple", "mint green", "soft orange", "vibrant teal"]
    scene_bg_color = BG_COLORS[s['number'] % len(BG_COLORS)]
    
    hair_lock = "Main character: curly black afro hair, pure white face (#FFFFFF), smooth head, black eyes, thin eyebrows, black hoodie with white atom symbol. "
    bg_lock = f"Background: solid vibrant {scene_bg_color} top half, light tan bottom half. "
    full_prompt = hair_lock + bg_lock + s['image_prompt'] + style_suffix
    
    batch.append({
        "num": num,
        "prompt": full_prompt,
        "output_path": out_path,
        "padded_filename": padded_filename,
        "narration": s.get("narration", "")
    })

print("🚀 Starting Parallel 5-Image Generation via Google Flow...")
success = gflow_assistant.generate_batch_imagen_images(batch, img_dir)

if success:
    print(f"SUCCESS! Generated {len(batch)} images in parallel.")
    album = []
    for item in batch:
        if os.path.exists(item["output_path"]):
            album.append((item["output_path"], f"📺 *Scene V{item['num']}* ({item['padded_filename']})\n\"{item['narration']}\""))
    if album:
        telegram_bot.send_message(f"📸 *Parallel 5-Image Batch Ready!* ({len(album)} Images)")
        telegram_bot.send_media_group(album)
        print("Sent photo album to Telegram!")
else:
    print("Parallel generation failed.")
