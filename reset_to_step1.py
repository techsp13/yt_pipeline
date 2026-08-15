import os
import json

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

# Clear active_project.json
active_ptr = os.path.join(agent_dir, "active_project.json")
with open(active_ptr, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": None}, f, indent=4)

# Clear Google Flow Project ID & locks
for fname in [".gflow_project_id", ".pipeline.lock"]:
    fpath = os.path.join(agent_dir, fname)
    if os.path.exists(fpath):
        try:
            os.remove(fpath)
        except Exception:
            pass

print("Pipeline state reset to Step 1!")
