import os
import sys
import json
import time
import re
import random
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

import telegram_bot
import youtube_agent
import gflow_assistant

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, "06_Images")
chk_path = os.path.join(proj_dir, "04_Scenes", "Image_Checkpoints.json")

gap_nums = ["20", "21", "22", "25", "26", "27", "28", "38"]

scenes = youtube_agent.parse_scenes_from_file()
gap_scenes = [s for s in scenes if f"{s['number']:02d}" in gap_nums]

checkpoints = {}
if os.path.exists(chk_path):
    try:
        with open(chk_path, "r", encoding="utf-8") as f:
            checkpoints = json.load(f)
    except Exception:
        checkpoints = {}

print(f"Processing 8 Gap Scenes: {gap_nums}...")
telegram_bot.send_message(f"🖼️ *Generating {len(gap_scenes)} Missing Gap Scenes via Google Flow Imagen 4...*\nScenes: {', '.join(gap_nums)}")

# 1. Generate missing images for gaps
gap_data = []
for scene in gap_scenes:
    num = f"{scene['number']:02d}"
    padded_name = f"{scene['number']:03d}_Scene_{num}.png"
    out_path = os.path.join(img_dir, padded_name)
    
    prompt = scene["image_prompt"]
    cfg = youtube_agent.get_channel_config()
    style_suffix = cfg["widescreen_suffix"]
    BG_COLORS = ["baby blue", "lemon yellow", "soft purple", "mint green", "soft orange", "vibrant teal"]
    scene_bg_color = BG_COLORS[scene['number'] % len(BG_COLORS)]
    
    hair_lock = "Main character: curly black afro hair, pure white face (#FFFFFF), smooth head, black eyes, thin eyebrows, black hoodie with white atom symbol. "
    bg_lock = f"Background: solid vibrant {scene_bg_color} top half, light tan bottom half. "
    full_prompt = hair_lock + bg_lock + prompt + style_suffix

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1000:
        print(f"Generating Gap Scene V{num} ({padded_name})...")
        success = gflow_assistant.generate_imagen_image(full_prompt, out_path)
        if success:
            proj_id = gflow_assistant._get_saved_project_id()
            checkpoints[num] = {
                "project_id": proj_id,
                "scene_number": num,
                "filename": padded_name,
                "status": "pending",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(chk_path, "w", encoding="utf-8") as f:
                json.dump(checkpoints, f, indent=4)

    gap_data.append({
        "num": num,
        "prompt": full_prompt,
        "output_path": out_path,
        "padded_filename": padded_name,
        "narration": scene.get("narration", "")
    })

# 2. Send the 8 gap images to Telegram
telegram_bot.send_message(f"📸 *Gap Scenes Ready for Review! ({len(gap_data)} Images)*")
for i in range(0, len(gap_data), 5):
    sub = gap_data[i:i+5]
    album = [(d["output_path"], f"📺 *Scene V{d['num']}* ({d['padded_filename']})\n\"{d['narration']}\"") for d in sub]
    telegram_bot.send_media_group(album)

# 3. Interactive Review Loop
buttons = [
    [{"text": f"✅ Approve All 8 Gap Images", "callback_data": "approve_gap_all"}],
    [{"text": "❌ Reject (Reply /reject N)", "callback_data": "noop"}]
]
ctrl_msg = telegram_bot.send_message(
    f"🎨 *Gap Scenes Review ({', '.join(gap_nums)})*\n"
    f"• `/approve_all` — Approve all 8 gap images\n"
    f"• `/approve N` — Approve specific scene (e.g. `/approve 22`)\n"
    f"• `/reject N` — Reject & regenerate (e.g. `/reject 22`)",
    buttons=buttons
)

approved_set = set()
while len(approved_set) < len(gap_data):
    choice = youtube_agent.get_user_interaction(ctrl_msg)
    raw_lower = choice.lower().strip()

    if choice in ["approve_gap_all", "approve_all"] or "approve_all" in raw_lower or "approve all" in raw_lower:
        for item in gap_data:
            approved_set.add(item["num"])
        telegram_bot.send_message("✅ *All 8 Gap Scenes Approved!*")
        break

    elif choice.startswith("text:"):
        cmd_text = choice.split("text:", 1)[1].strip()
        cmd_lower = cmd_text.lower()

        if "/approve_all" in cmd_lower or "approve_all" in cmd_lower:
            for item in gap_data:
                approved_set.add(item["num"])
            telegram_bot.send_message("✅ *All 8 Gap Scenes Approved!*")
            break

        elif cmd_lower.startswith("/approve") or cmd_lower.startswith("approve "):
            nums = [f"{int(x):02d}" for x in re.findall(r"\b\d+\b", cmd_text)]
            for n in nums:
                if any(b["num"] == n for b in gap_data):
                    approved_set.add(n)
                    checkpoints[n] = checkpoints.get(n, {})
                    checkpoints[n]["status"] = "approved"
                    telegram_bot.send_message(f"✅ *Scene V{n} approved!* ({len(approved_set)}/8 in gap batch)")
            with open(chk_path, "w", encoding="utf-8") as f:
                json.dump(checkpoints, f, indent=4)

        elif cmd_lower.startswith("/reject") or cmd_lower.startswith("/regen"):
            rej_nums = [f"{int(x):02d}" for x in re.findall(r"\b\d+\b", cmd_text)]
            for t_num in rej_nums:
                target = next((item for item in gap_data if item["num"] == t_num), None)
                if target:
                    if t_num in approved_set:
                        approved_set.remove(t_num)
                    gen_prompt = target["prompt"] + f" (Seed variation: {random.randint(1000,999999)})"
                    telegram_bot.send_message(f"🔄 *Regenerating Scene V{t_num} via Google Flow...*")
                    try:
                        gflow_assistant.generate_imagen_image(gen_prompt, target["output_path"])
                        telegram_bot.send_photo(photo_path=target["output_path"], caption=f"🔄 *Updated Scene V{t_num}*\n\"{target['narration']}\"")
                    except Exception as e:
                        telegram_bot.send_message(f"⚠️ Error regenerating Scene V{t_num}: {e}")

# Save approved gap checkpoints
for item in gap_data:
    n = item["num"]
    checkpoints[n] = {
        "project_id": gflow_assistant._get_saved_project_id(),
        "scene_number": n,
        "filename": item["padded_filename"],
        "status": "approved",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    # Also copy to Approved and Final folders
    approved_path = os.path.join(img_dir, "Approved", f"Scene_{n}.png")
    final_path = os.path.join(img_dir, "Final", f"Scene_{n}.png")
    if os.path.exists(item["output_path"]):
        import shutil
        shutil.copy2(item["output_path"], approved_path)
        shutil.copy2(item["output_path"], final_path)

with open(chk_path, "w", encoding="utf-8") as f:
    json.dump(checkpoints, f, indent=4)

telegram_bot.send_message("🎉 *All 8 Gap Scenes Approved & Saved!* Gap scenes 1 to 116 are now 100% complete!")
print("Done processing gap scenes!")
