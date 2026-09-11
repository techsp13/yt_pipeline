import os
import sys
import json
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')
import telegram_bot

root = r"D:\youtube_automation_agent\channels\money\Revenue_vs_Profit_Where_Does_the_Money_Go_2026-09-04_182801\06_Images"
scenes_file = r"D:\youtube_automation_agent\channels\money\Revenue_vs_Profit_Where_Does_the_Money_Go_2026-09-04_182801\04_Scenes\Scene_List.json"

narrations = {}
with open(scenes_file, 'r', encoding='utf-8') as f:
    for s in json.load(f):
        narrations[s['number']] = s.get('narration', '')

all_files = [f for f in os.listdir(root) if f.endswith('.png') and not f.startswith('_')]
scene_map = {}
for i in range(1, 231):
    candidates = [f for f in all_files if f.endswith(f'Scene_{i}.png') or f.endswith(f'Scene_{i:02d}.png') or f.endswith(f'Scene_{i:03d}.png')]
    if candidates:
        scene_map[i] = os.path.join(root, candidates[0])

album_nums = [7, 13, 15, 17, 22, 33, 37, 40]
for a_idx in album_nums:
    start_scene = (a_idx - 1) * 5 + 1
    end_scene = a_idx * 5
    album = []
    for s_num in range(start_scene, end_scene + 1):
        path = scene_map[s_num]
        nar = narrations.get(s_num, '')
        album.append((path, f"Scene {s_num}\n\"{nar[:180]}\""))
    print(f"Resending Album {a_idx}/46 (Scenes {start_scene}..{end_scene})...", flush=True)
    telegram_bot.send_media_group(album)
    time.sleep(5.0)

print("All skipped albums resent successfully!")
