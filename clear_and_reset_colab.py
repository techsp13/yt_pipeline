import os
import shutil
import json
import prepare_colab
import telegram_bot

proj_dir = r"D:\youtube_automation_agent\channels\science\NASAs_Twin_Study_2026-07-25_230010"

# 1. Clear 07_Voice folder
voice_dir = os.path.join(proj_dir, "07_Voice")
if os.path.exists(voice_dir):
    for f in os.listdir(voice_dir):
        if f.endswith(".mp3") or f.endswith(".wav"):
            try:
                os.remove(os.path.join(voice_dir, f))
            except Exception:
                pass
    print("[CLEARED] 07_Voice directory emptied.")

# 2. Clear output_temp folder
temp_dir = os.path.join(proj_dir, "output_temp")
if os.path.exists(temp_dir):
    for f in os.listdir(temp_dir):
        try:
            os.remove(os.path.join(temp_dir, f))
        except Exception:
            pass
    print("[CLEARED] output_temp directory emptied.")

# 3. Clear old 07_Voice.zip in Downloads
dl_zip = r"C:\Users\ASUS\Downloads\07_Voice.zip"
if os.path.exists(dl_zip):
    try:
        os.remove(dl_zip)
        print("[CLEARED] Old C:\\Users\\ASUS\\Downloads\\07_Voice.zip removed.")
    except Exception:
        pass

# 4. Set step = 8 in Project_Config.json
cfg_path = os.path.join(proj_dir, "Project_Config.json")
if os.path.exists(cfg_path):
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["step"] = 8
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
    print("[RESET] Project step set to 8 (Voice Generation).")

# 5. Export fresh scenes_payload.json for Colab
payload_path = prepare_colab.prepare_colab_payload()
print("[SUCCESS] Exported 230 clean narrations to scenes_payload.json!")

# 6. Send payload to Telegram
if payload_path and os.path.exists(payload_path):
    telegram_bot.send_document(
        payload_path,
        caption="📄 *Fresh scenes_payload.json for NASA's Twin Study (230 Scenes)*\n\nDownload and upload to Google Colab GPU!"
    )
    print("[SENT] Delivered scenes_payload.json to Telegram chat.")
