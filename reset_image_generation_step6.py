import os
import json
import shutil

agent_dir = r"D:\youtube_automation_agent"
active_ptr = os.path.join(agent_dir, "active_project.json")

with open(active_ptr, "r", encoding="utf-8") as f:
    proj_dir = json.load(f).get("active_project_dir")

print(f"Active Project: {proj_dir}")

if proj_dir and os.path.exists(proj_dir):
    # 1. Clear 06_Images directory
    img_dir = os.path.join(proj_dir, "06_Images")
    if os.path.exists(img_dir):
        shutil.rmtree(img_dir)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(os.path.join(img_dir, "Approved"), exist_ok=True)
        os.makedirs(os.path.join(img_dir, "Final"), exist_ok=True)
        print("1. Cleared 06_Images directory.")

    # 2. Clear Checkpoints
    chk_dir = os.path.join(proj_dir, "14_Checkpoints")
    if os.path.exists(chk_dir):
        for f in os.listdir(chk_dir):
            if "image" in f.lower() or "scene" in f.lower() or f.endswith(".json"):
                try:
                    os.remove(os.path.join(chk_dir, f))
                except Exception:
                    pass
        print("2. Cleared image checkpoints.")

    # 3. Update Project_Config.json to Step 6 with empty approved_scenes
    cfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["step"] = 6
        cfg["approved_scenes"] = {}
        cfg["active"] = True
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        print("3. Updated Project_Config.json to Step 6.")

# 4. Update root agent_state.json to Step 6
state_path = os.path.join(agent_dir, "agent_state.json")
with open(state_path, "r", encoding="utf-8") as f:
    state = json.load(f)
state["step"] = 6
state["approved_scenes"] = {}
state["active"] = True
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4)
print("4. Updated agent_state.json to Step 6.")

# 5. Clear lock
lock_file = os.path.join(agent_dir, ".pipeline.lock")
if os.path.exists(lock_file):
    try:
        os.remove(lock_file)
    except Exception:
        pass

print("CLEARED ALL APPROVED IMAGES AND RESET PIPELINE TO STEP 6!")
