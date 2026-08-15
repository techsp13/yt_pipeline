import os
import json
import shutil

agent_dir = r"D:\youtube_automation_agent"

# Reset agent_state.json
state_path = os.path.join(agent_dir, "agent_state.json")
fresh_state = {
    "step": 1,
    "topic": None,
    "title": None,
    "thumbnail_concept": None,
    "script": None,
    "approved_scenes": {},
    "active": True
}
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(fresh_state, f, indent=4)
print("1. Reset agent_state.json to Step 1.")

# Clear active_project.json pointer
active_ptr = os.path.join(agent_dir, "active_project.json")
with open(active_ptr, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": None}, f, indent=4)
print("2. Cleared active_project.json pointer.")

# Clear Google Flow Project ID
gflow_pid = os.path.join(agent_dir, ".gflow_project_id")
if os.path.exists(gflow_pid):
    try:
        os.remove(gflow_pid)
        print("3. Cleared .gflow_project_id.")
    except Exception:
        pass

# Clear pipeline lock
lock_file = os.path.join(agent_dir, ".pipeline.lock")
if os.path.exists(lock_file):
    try:
        os.remove(lock_file)
        print("4. Cleared .pipeline.lock.")
    except Exception:
        pass

print("PIPELINE FULLY RESET FOR SHORT 10-SECOND TEST VIDEO!")
