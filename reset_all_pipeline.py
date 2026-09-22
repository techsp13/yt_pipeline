import os
import json
import shutil
import sys

agent_dir = r"D:\youtube_automation_agent"

print("--- FULL PIPELINE RESET IN PROGRESS ---")

# 1. Reset agent_state.json
state_path = os.path.join(agent_dir, "agent_state.json")
fresh_state = {
    "step": 1,
    "channel": "history",
    "topic": None,
    "title": None,
    "thumbnail_concept": None,
    "script": None,
    "approved_scenes": {},
    "active": False,
    "auto_mode": True,
    "auto_approve_images": True,
    "auto_approve_breakdown": True
}
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(fresh_state, f, indent=4)
print("1. Reset agent_state.json to Step 1 (active=False, topic=None).")

# 2. Reset active_project.json
active_pointer = os.path.join(agent_dir, "active_project.json")
with open(active_pointer, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": None}, f, indent=4)
print("2. Cleared active_project.json pointer.")

# 3. Clear lock files and cache
locks_to_clear = [
    os.path.join(agent_dir, ".pipeline.lock"),
    os.path.join(agent_dir, ".gflow_project_id"),
    os.path.join(agent_dir, "pipeline_single_instance.lock")
]
for lf in locks_to_clear:
    if os.path.exists(lf):
        try:
            os.remove(lf)
            print(f"3. Removed {os.path.basename(lf)}")
        except Exception as e:
            print(f"   Could not remove {lf}: {e}")

# 4. Clean temporary build directories
for tmp_d in ["_gflow_tmp_0", "_gflow_single_tmp", "output_temp"]:
    full_p = os.path.join(agent_dir, tmp_d)
    if os.path.exists(full_p):
        try:
            shutil.rmtree(full_p, ignore_errors=True)
            print(f"4. Cleared temporary directory: {tmp_d}")
        except Exception as e:
            print(f"   Could not clear {tmp_d}: {e}")

# 5. Clean scratch python scripts
scratch_files = [
    os.path.join(agent_dir, "temp_analyze_ink.py"),
    os.path.join(agent_dir, "download_ink_subs.py"),
    os.path.join(agent_dir, "download_remaining_ink.py"),
    os.path.join(agent_dir, "deep_inspect_ink.py"),
    os.path.join(agent_dir, "ink_videos.json")
]
for sf in scratch_files:
    if os.path.exists(sf):
        try:
            os.remove(sf)
            print(f"5. Removed scratch file: {os.path.basename(sf)}")
        except Exception:
            pass

# 6. Send Telegram status notification
try:
    import telegram_bot
    telegram_bot.send_message(
        "🔄 *Pipeline Fully Reset!*\n\n"
        "All state, pointers, locks, and temporary cache have been cleared.\n"
        "The automation agent is now in clean idle mode.\n\n"
        "Ready to start fresh tomorrow! Whenever you're ready, simply send `/start` or `/start_video` to choose your channel and topic."
    )
    print("6. Sent Telegram notification.")
except Exception as e:
    print(f"6. Telegram notification skipped: {e}")

print("=== COMPLETE PIPELINE RESET SUCCESSFUL ===")
