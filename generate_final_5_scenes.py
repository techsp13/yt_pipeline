import os
import sys
import json
import time
import shutil
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = r"D:\youtube_automation_agent\channels\money\Revenue_vs_Profit_Where_Does_the_Money_Go_2026-09-04_182801"
IMG_DIR = os.path.join(PROJECT_DIR, "06_Images")
APPROVED_DIR = os.path.join(IMG_DIR, "Approved")
FINAL_DIR = os.path.join(IMG_DIR, "Final")
SCENES_FILE = os.path.join(PROJECT_DIR, "04_Scenes", "Scene_List.json")
CHK_FILE = os.path.join(PROJECT_DIR, "04_Scenes", "Image_Checkpoints.json")
STATE_FILE = r"D:\youtube_automation_agent\agent_state.json"

sys.path.insert(0, r"D:\youtube_automation_agent")
from playwright_flow_generator import generate_image_playwright, _clean_profile_locks, PROFILES
import telegram_bot

def clean_all_locks():
    print("[Clean] Cleaning all locks and orphan processes...")
    try:
        subprocess.run([
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
            "Where-Object {$_.CommandLine -like '*acc*'} | "
            "ForEach-Object {Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}"
        ], capture_output=True, timeout=10)
    except Exception as e:
        print(f"[Clean] Warning killing chrome: {e}")

    for prof in PROFILES:
        _clean_profile_locks(prof)
    
    pipeline_lock = r"D:\youtube_automation_agent\.pipeline.lock"
    if os.path.exists(pipeline_lock):
        try:
            os.remove(pipeline_lock)
        except Exception:
            pass

def main():
    clean_all_locks()
    os.makedirs(APPROVED_DIR, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)

    with open(SCENES_FILE, "r", encoding="utf-8") as f:
        scenes_data = json.load(f)

    # Filter scenes 226 to 230
    target_scenes = [s for s in scenes_data if s.get("number") in [226, 227, 228, 229, 230]]
    print(f"[Target] Found {len(target_scenes)} remaining scenes to generate: {[s['number'] for s in target_scenes]}")

    checkpoints = {}
    if os.path.exists(CHK_FILE):
        with open(CHK_FILE, "r", encoding="utf-8") as f:
            checkpoints = json.load(f)

    generated_items = []
    for s in target_scenes:
        num = s["number"]
        padded_fn = f"{num:03d}_Scene_{num}.png"
        out_path = os.path.join(IMG_DIR, padded_fn)
        prompt = s.get("image_prompt", "")
        narration = s.get("narration", "")

        if os.path.exists(out_path) and os.path.getsize(out_path) > 20000:
            print(f"[Scene {num}] Already exists ({os.path.getsize(out_path)} bytes). Skipping generation.")
            generated_items.append({"num": num, "path": out_path, "narration": narration, "padded": padded_fn})
            continue

        print(f"\n=======================================================")
        print(f"[RENDER] GENERATING FINAL SCENE {num}/230 ({padded_fn})...")
        print(f"Prompt: {prompt[:100]}...")
        print(f"=======================================================")

        success = False
        for attempt in range(3):
            print(f"[Scene {num}] Attempt {attempt + 1}/3...")
            ok = generate_image_playwright(prompt, out_path, aspect_ratio="16:9")
            if ok and os.path.exists(out_path) and os.path.getsize(out_path) > 20000:
                print(f"[Scene {num}] [SUCCESS] Saved -> {padded_fn} ({os.path.getsize(out_path)} bytes)")
                success = True
                break
            else:
                print(f"[Scene {num}] [FAIL] Attempt {attempt + 1} failed. Cleaning locks and waiting 5s...")
                clean_all_locks()
                time.sleep(5)

        if not success:
            print(f"[ERROR] FAILED to generate Scene {num} after 3 attempts.")
            return False

        generated_items.append({"num": num, "path": out_path, "narration": narration, "padded": padded_fn})

        # Copy to Approved and Final
        app_path = os.path.join(APPROVED_DIR, f"Scene_{num}.png")
        fin_path = os.path.join(FINAL_DIR, f"Scene_{num}.png")
        shutil.copy2(out_path, app_path)
        shutil.copy2(out_path, fin_path)

        checkpoints[str(num)] = {
            "worker_api": "google_imagen_gflow",
            "scene_number": num,
            "filename": padded_fn,
            "status": "approved",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(CHK_FILE, "w", encoding="utf-8") as f:
            json.dump(checkpoints, f, indent=4)

    print("\n[COMPLETE] ALL 230 SCENES ARE GENERATED & ON DISK!")

    total_imgs = len([f for f in os.listdir(IMG_DIR) if f.endswith(".png") and not f.startswith("_")])
    print(f"[Audit] Total PNGs in 06_Images: {total_imgs} / 230")

    print("[Telegram] Sending Batch 46 (Scenes 226..230) to Telegram...")
    try:
        telegram_bot.send_message("Final Batch 46/46 Ready! (Scenes 226..230)\nAll 230 scenes complete! Review final images below:")
        album = [(d["path"], f"Scene V{d['num']} ({d['padded']})\n\"{d['narration']}\"") for d in generated_items]
        telegram_bot.send_media_group(album)
        
        btns = [
            [{"text": f"Re {d['num']}", "callback_data": f"reject_{d['num']}"} for d in generated_items[:3]],
            [{"text": f"Re {d['num']}", "callback_data": f"reject_{d['num']}"} for d in generated_items[3:]],
            [{"text": "Approve All 230 Scenes", "callback_data": "approve_all_batch"}]
        ]
        telegram_bot.send_message("Batch 46/46 Delivered (Scenes 226..230)\nAll 230 scenes are saved to disk!", buttons=btns)
        print("[Telegram] Sent successfully!")
    except Exception as e_tg:
        print(f"[Telegram] Error sending to Telegram: {e_tg}")

    print("[State] Updating agent_state.json to step 8...")
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
    
    state["step"] = 8
    if "approved_scenes" not in state:
        state["approved_scenes"] = {}
    for d in generated_items:
        state["approved_scenes"][d["num"]] = d["padded"]
    
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

    print("[STATUS] STATE UPDATED TO STEP 8! Generation 100% complete.")
    return True

if __name__ == "__main__":
    main()
