import os
import json
import sys
import shutil

import youtube_agent
import gflow_assistant

proj_dir = youtube_agent.get_active_project_dir()
print(f"Active project: {proj_dir}")

# Clear Image Checkpoints
chk_path = os.path.join(proj_dir, "04_Scenes", "Image_Checkpoints.json")
if os.path.exists(chk_path):
    with open(chk_path, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=4)
    print("Cleared Image_Checkpoints.json")

# Clear Google Flow Project ID for fresh creation
gflow_assistant._clear_saved_project_id()

# Set step = 6 in state
state_path = r"D:\youtube_automation_agent\agent_state.json"
state = youtube_agent.load_state()
state["step"] = 6
state["approved_scenes"] = {}
youtube_agent.save_state(state)
print("Reset state to Step 6 (approved_scenes={})")

print("Ready to generate from Scene 1 in 5-image separate batches!")
