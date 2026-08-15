import os
import json
import telegram_bot
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
img_dir = os.path.join(proj_dir, "06_Images")

scenes_01_05 = []
for i in range(1, 6):
    num = f"{i:02d}"
    path = os.path.join(img_dir, f"{num:03d}_Scene_{num}.png")
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        scenes_01_05.append(path)

print(f"Found {len(scenes_01_05)} generated images for Batch 1 (Scenes 01..05).")

if len(scenes_01_05) == 5:
    telegram_bot.send_message("📸 *Batch 1 Ready! (Scenes 01..05)*\nReview images below:")
    telegram_bot.send_photo_album(scenes_01_05, caption="Batch 1: Scenes 01 to 05")
    buttons = [
        [
            {"text": "✅ Approve All (Scenes 01..05)", "callback_data": "approve_all_batch"}
        ]
    ]
    telegram_bot.send_message("Reply `/approve_all`, `/approve 1 3`, or `/reject 2`:", buttons=buttons)
    print("Re-sent Batch 1 (Scenes 01..05) to Telegram successfully!")
else:
    print("Not all 5 images found yet.")
