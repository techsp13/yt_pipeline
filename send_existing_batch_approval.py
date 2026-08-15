import os
import sys
import json
import time
import re
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))

import telegram_bot
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, "06_Images")
scenes = youtube_agent.parse_scenes_from_file()

chk_path = os.path.join(proj_dir, "04_Scenes", "Image_Checkpoints.json")
checkpoints = {}
if os.path.exists(chk_path):
    try:
        with open(chk_path, "r", encoding="utf-8") as f:
            checkpoints = json.load(f)
    except Exception:
        checkpoints = {}

# Gather all scenes that have existing local images
all_scene_data = []
scene_idx = 1
for scene in scenes:
    num = f"{scene['number']:02d}"
    if youtube_agent.is_title_card_scene(scene):
        continue

    # Look for image file
    padded_name = f"{scene_idx:03d}_Scene_{num}.png"
    matches = [os.path.join(img_dir, f) for f in os.listdir(img_dir)
               if (f == padded_name or f.startswith(f"Scene_{num}_v") or f.startswith(f"Scene_{int(num)}_v"))
               and os.path.getsize(os.path.join(img_dir, f)) > 1000]
    
    if matches:
        img_path = max(matches, key=os.path.getmtime)
        all_scene_data.append({
            "num": num,
            "scene_idx": scene_idx,
            "prompt": scene.get("image_prompt", ""),
            "output_path": img_path,
            "padded_filename": padded_name,
            "narration": scene.get("narration", "")
        })
    scene_idx += 1

total_found = len(all_scene_data)
print(f"Found {total_found} existing local images. Processing in 10-image batches...")
telegram_bot.send_message(f"📸 *Found {total_found} existing local scene images! Sending for batch approval...*")

BATCH_SIZE = 10
total_batches = (total_found + BATCH_SIZE - 1) // BATCH_SIZE

for batch_start in range(0, total_found, BATCH_SIZE):
    batch = all_scene_data[batch_start:batch_start + BATCH_SIZE]
    batch_num = (batch_start // BATCH_SIZE) + 1

    # Send 10 images in 2 albums of 5
    telegram_bot.send_message(f"📸 *Batch {batch_num}/{total_batches}: Review Scenes {batch[0]['num']}..{batch[-1]['num']}*")
    for i in range(0, len(batch), 5):
        sub = batch[i:i+5]
        album = [(d["output_path"], f"📺 *Scene V{d['num']}* ({os.path.basename(d['output_path'])})\n\"{d['narration']}\"") for d in sub]
        try:
            telegram_bot.send_media_group(album)
            time.sleep(1.5)
        except Exception as e:
            print(f"Error sending album: {e}")

    # Control message
    buttons = [
        [{"text": f"✅ Approve Batch {batch_num} ({len(batch)} Images)", "callback_data": "approve_all_batch"}],
        [{"text": "❌ Reject (Reply /reject N)", "callback_data": "noop"}]
    ]
    ctrl_msg = telegram_bot.send_message(
        f"🎨 *Batch {batch_num}/{total_batches} Actions*\n"
        f"• `/approve_all` — Approve all {len(batch)} images in this batch\n"
        f"• `/approve N` — Approve specific scene\n"
        f"• `/reject N` — Reject & regenerate scene",
        buttons=buttons
    )

    batch_approved = set()
    while len(batch_approved) < len(batch):
        choice = youtube_agent.get_user_interaction(ctrl_msg)
        raw_lower = choice.lower().strip()

        if choice in ["approve_all_batch", "approve_all"] or "approve_all" in raw_lower or "approve all" in raw_lower:
            for item in batch:
                batch_approved.add(item["num"])
            telegram_bot.send_message(f"✅ *Batch {batch_num}/{total_batches} approved!*")
            break

        elif choice.startswith("text:"):
            cmd_text = choice.split("text:", 1)[1].strip()
            cmd_lower = cmd_text.lower()

            if "/approve_all" in cmd_lower or "approve_all" in cmd_lower:
                for item in batch:
                    batch_approved.add(item["num"])
                telegram_bot.send_message(f"✅ *Batch {batch_num}/{total_batches} approved!*")
                break

            elif cmd_lower.startswith("/approve") or cmd_lower.startswith("approve "):
                nums = [f"{int(x):02d}" for x in re.findall(r"\b\d+\b", cmd_text)]
                for n in nums:
                    if any(b["num"] == n for b in batch):
                        batch_approved.add(n)
                        checkpoints[n] = {"scene_number": n, "status": "approved", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
                        telegram_bot.send_message(f"✅ *Scene V{n} approved!* ({len(batch_approved)}/{len(batch)} in batch)")

            elif cmd_lower.startswith("/reject") or cmd_lower.startswith("/regen"):
                rej_nums = [f"{int(x):02d}" for x in re.findall(r"\b\d+\b", cmd_text)]
                for t_num in rej_nums:
                    target = next((item for item in batch if item["num"] == t_num), None)
                    if target:
                        import gflow_assistant, random
                        if os.path.exists(target["output_path"]):
                            try:
                                os.remove(target["output_path"])
                            except Exception:
                                pass
                        gflow_assistant._clear_saved_project_id()
                        gen_prompt = target["prompt"] + f" (Seed variation {random.randint(10000,999999)}, new dynamic composition)"
                        telegram_bot.send_message(f"🔄 *Regenerating fresh Scene V{t_num} via Google Flow...*")
                        try:
                            gflow_assistant.generate_imagen_image(gen_prompt, target["output_path"])
                            if os.path.exists(target["output_path"]):
                                telegram_bot.send_photo(photo_path=target["output_path"], caption=f"🔄 *Updated Scene V{t_num}*\n\"{target['narration']}\"")
                            else:
                                telegram_bot.send_message(f"⚠️ Regeneration produced no output file for Scene V{t_num}.")
                        except Exception as e:
                            telegram_bot.send_message(f"⚠️ Error regenerating Scene V{t_num}: {e}")

    # Mark checkpoint
    for item in batch:
        n = item["num"]
        checkpoints[n] = {"scene_number": n, "filename": os.path.basename(item["output_path"]), "status": "approved"}
    with open(chk_path, "w", encoding="utf-8") as f:
        json.dump(checkpoints, f, indent=4)

telegram_bot.send_message("🎉 *All existing image batches reviewed & approved!* Ready to continue pipeline!")
print("Done batch review of existing images!")
