import os
import json
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
print(f"Active project dir: {proj_dir}")

# Clear Image_Checkpoints.json
chk_path = os.path.join(proj_dir, "04_Scenes", "Image_Checkpoints.json")
if os.path.exists(chk_path):
    with open(chk_path, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)
    print("Cleared Image_Checkpoints.json")

# Set step = 6 in agent_state.json
state_path = r"D:\youtube_automation_agent\agent_state.json"
state = youtube_agent.load_state()
state["step"] = 6
state["approved_scenes"] = {}
youtube_agent.save_state(state)
print("Updated agent_state.json to Step 6.")
