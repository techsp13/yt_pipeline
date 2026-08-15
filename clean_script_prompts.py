import os
import sys
import json
import re
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
breakdown_path = os.path.join(proj_dir, "04_Scenes", "Scene_Breakdown.md")
state_path = r"D:\youtube_automation_agent\agent_state.json"

replacements = {
    r"\bScott Kelly\b": "a generic astronaut",
    r"\bMark Kelly\b": "a twin astronaut",
    r"\bHippocrates\b": "an ancient Greek doctor",
    r"\bGalen\b": "an ancient Roman doctor",
    r"\bÖtzi\b": "a prehistoric caveman",
    r"\bOtzi\b": "a prehistoric caveman",
    r"\bHammurabi\b": "an ancient king",
    r"\bEdwin Smith\b": "an ancient medical practitioner",
    r"\bEbers\b": "an ancient medical practitioner"
}

def sanitize_text(text):
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

# 1. Update Scene_Breakdown.md
count_md = 0
if os.path.exists(breakdown_path):
    with open(breakdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = sanitize_text(content)
    if new_content != content:
        with open(breakdown_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Updated Scene_Breakdown.md with sanitized prompts!")
        count_md += 1
    else:
        print("Scene_Breakdown.md was already clean.")

# 2. Update agent_state.json
count_state = 0
if os.path.exists(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state_data = json.load(f)
        
        if "script" in state_data and isinstance(state_data["script"], str):
            state_data["script"] = sanitize_text(state_data["script"])
        
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)
        print("Updated agent_state.json with sanitized prompts!")
        count_state += 1
    except Exception as e:
        print(f"Error updating agent_state.json: {e}")

print("Done scrubbing real-world character names from all scene prompts!")
