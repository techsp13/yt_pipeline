import os
import json

agent_dir = r"D:\youtube_automation_agent"
active_ptr = os.path.join(agent_dir, "active_project.json")

with open(active_ptr, "r", encoding="utf-8") as f:
    proj_dir = json.load(f).get("active_project_dir")

print(f"Active Project: {proj_dir}")

if proj_dir and os.path.exists(proj_dir):
    cfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["step"] = 6
        cfg["approved_scenes"] = {}
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

    state_path = os.path.join(agent_dir, "agent_state.json")
    with open(state_path, "r", encoding="utf-8") as f:
        st = json.load(f)
    st["step"] = 6
    st["approved_scenes"] = {}
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=4)

    # Clear Image_Checkpoints.json
    chk_path = os.path.join(proj_dir, "04_Scenes", "Image_Checkpoints.json")
    if os.path.exists(chk_path):
        with open(chk_path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)

    print("Project state reset to Step 6 starting at SCENE 1!")
