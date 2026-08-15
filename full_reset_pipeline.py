import os
import json
import sys

agent_dir = r"D:\youtube_automation_agent"

# 1. Reset agent_state.json
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
print("1. Reset agent_state.json to Step 1 (topic=None).")

# 2. Reset active_project.json
active_pointer = os.path.join(agent_dir, "active_project.json")
with open(active_pointer, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": None}, f, indent=4)
print("2. Cleared active_project.json pointer.")

# 3. Clear gflow cached project ID
gflow_pid_file = os.path.join(agent_dir, ".gflow_project_id")
if os.path.exists(gflow_pid_file):
    try:
        os.remove(gflow_pid_file)
        print("3. Cleared .gflow_project_id.")
    except Exception:
        pass

# 4. Clear lock file
lock_path = os.path.join(agent_dir, ".pipeline.lock")
if os.path.exists(lock_path):
    try:
        os.remove(lock_path)
        print("4. Cleared .pipeline.lock.")
    except Exception:
        pass

print("FULL PIPELINE RESET COMPLETE!")
