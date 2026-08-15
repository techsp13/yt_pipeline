import os
import json
import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python regenerate_scene.py <scene_number>")
        print("Example: python regenerate_scene.py 116")
        return

    scene_num = sys.argv[1].strip()
    # Format scene number with leading zero if needed (e.g. 05 or 116)
    if len(scene_num) == 1:
        scene_num_str = f"0{scene_num}"
    else:
        scene_num_str = scene_num

    # 1. Load active project
    active_path = r"D:\youtube_automation_agent\active_project.json"
    if not os.path.exists(active_path):
        print("Error: No active project found.")
        return

    with open(active_path, "r", encoding="utf-8") as f:
        proj_dir = json.load(f)["active_project_dir"]

    cfg_path = os.path.join(proj_dir, "Project_Config.json")
    if not os.path.exists(cfg_path):
        print(f"Error: Config file not found at {cfg_path}")
        return

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # 2. Reset the approved scene and step
    if scene_num_str in cfg.get("approved_scenes", {}):
        del cfg["approved_scenes"][scene_num_str]
        print(f"Removed scene V{scene_num_str} from approved list.")
    else:
        print(f"Warning: Scene V{scene_num_str} was not found in approved list. Continuing anyway.")

    cfg["step"] = 6
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

    print(f"Project step reset to Step 6. Restarting pipeline to regenerate Scene V{scene_num_str}...")

    # 3. Start youtube_agent.py
    subprocess.Popen([sys.executable, "youtube_agent.py"], cwd=r"D:\youtube_automation_agent", creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    main()
