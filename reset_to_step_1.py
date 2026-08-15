"""
reset_to_step_1.py
"""
import os, sys, json, shutil

proj_dir = r"D:\youtube_automation_agent"
sys.path.insert(0, proj_dir)

from youtube_agent import (
    STATE_FILE_PATH, ACTIVE_POINTER_FILE, LOCK_FILE_PATH, telegram_bot
)

print("==========================================================")
print("             RESETTING PIPELINE TO STEP 1                 ")
print("==========================================================")

# 1. Remove active project pointer
if os.path.exists(ACTIVE_POINTER_FILE):
    try:
        os.remove(ACTIVE_POINTER_FILE)
        print("Cleared active_project.json")
    except Exception as e:
        print(f"Notice: {e}")

# 2. Reset agent_state.json to Step 1
fresh_state = {
    "step": 1,
    "channel": "history",
    "topic": None,
    "title": None,
    "thumbnail_concept": None,
    "script": None,
    "approved_scenes": {},
    "approved_short_scenes": {},
    "active": False
}

if os.path.exists(STATE_FILE_PATH):
    try:
        with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(fresh_state, f, indent=4)
        print("Reset agent_state.json to Step 1")
    except Exception as e:
        print(f"Error resetting state: {e}")

# 3. Clean lock files
for lf in [LOCK_FILE_PATH, os.path.join(proj_dir, ".gflow_project_id"), os.path.join(proj_dir, ".pipeline.lock")]:
    if os.path.exists(lf):
        try:
            os.remove(lf)
            print(f"Removed lock: {lf}")
        except Exception:
            pass

# 4. Clean temporary build directories
for tmp_d in ["_gflow_tmp_0", "_gflow_single_tmp", "output_temp"]:
    full_p = os.path.join(proj_dir, tmp_d)
    if os.path.exists(full_p):
        try:
            shutil.rmtree(full_p, ignore_errors=True)
            print(f"Cleaned temp dir: {tmp_d}")
        except Exception:
            pass

print("\nPipeline reset to Step 1 complete.")
telegram_bot.send_message(
    "🔄 *Pipeline Reset to Step 1 Complete!*\n\n"
    "State, active project pointer, & cache cleared!\n"
    "Ready for your next video topic or channel execution!"
)
