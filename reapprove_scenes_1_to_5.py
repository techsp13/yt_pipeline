import os
import json
import shutil

agent_dir = r"D:\youtube_automation_agent"
active_ptr = os.path.join(agent_dir, "active_project.json")

with open(active_ptr, "r", encoding="utf-8") as f:
    proj_dir = json.load(f).get("active_project_dir")

print(f"Active Project: {proj_dir}")

if proj_dir and os.path.exists(proj_dir):
    img_dir = os.path.join(proj_dir, "06_Images")
    app_dir = os.path.join(img_dir, "Approved")
    fin_dir = os.path.join(img_dir, "Final")
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(fin_dir, exist_ok=True)

    approved_map = {}
    for i in range(1, 6):
        num = f"{i:02d}"
        fn = f"{i:03d}_Scene_{num}.png"
        src_path = os.path.join(img_dir, fn)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(app_dir, f"Scene_{num}.png"))
            shutil.copy2(src_path, os.path.join(fin_dir, f"Scene_{num}.png"))
            approved_map[num] = fn
            print(f"Copied Scene {num} -> Approved & Final")

    # Update Project_Config.json
    cfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["approved_scenes"].update(approved_map)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        print("Updated Project_Config.json approved scenes.")

    # Update agent_state.json
    state_path = os.path.join(agent_dir, "agent_state.json")
    with open(state_path, "r", encoding="utf-8") as f:
        st = json.load(f)
    st["approved_scenes"].update(approved_map)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=4)
    print("Updated agent_state.json approved scenes.")

    print("RE-APPROVED SCENES 1 TO 5 SUCCESSFULLY!")
