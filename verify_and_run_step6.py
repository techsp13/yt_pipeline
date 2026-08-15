import os
import json

agent_dir = r"D:\youtube_automation_agent"
proj_dir = r"D:\youtube_automation_agent\channels\science\What_if_all_the_ice_on_Earth_melted_tomorrow_2026-07-28_103839"

# 1. Update active_project.json
active_ptr = os.path.join(agent_dir, "active_project.json")
with open(active_ptr, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": proj_dir}, f, indent=4)
print(f"Updated active_project.json -> {proj_dir}")

# 2. Update agent_state.json
state_path = os.path.join(agent_dir, "agent_state.json")
with open(state_path, "r", encoding="utf-8") as f:
    state = json.load(f)

state["step"] = 6
state["active"] = True
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4)
print("Updated agent_state.json to Step 6.")

# 3. Update Project_Config.json inside project folder
cfg_path = os.path.join(proj_dir, "Project_Config.json")
if os.path.exists(cfg_path):
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["step"] = 6
    cfg["active"] = True
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)
    print("Updated Project_Config.json to Step 6.")

print("Setup complete. Ready to run youtube_agent.py!")
