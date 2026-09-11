import os
import sys
import json
import time

AGENT_DIR = r"D:\youtube_automation_agent"
sys.path.insert(0, AGENT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import youtube_agent
import render_final_single_pass

def main():
    print("=" * 60)
    print("  STEP 10: SINGLE-PASS PYTOON VIDEO RENDERING")
    print("=" * 60)

    proj_dir = youtube_agent.get_active_project_dir()
    print(f"Active Project: {proj_dir}")

    t0 = time.time()
    render_final_single_pass.main()
    render_time = time.time() - t0

    output_mp4 = os.path.join(proj_dir, "11_Final_Video", "Video_Final.mp4")
    if not os.path.exists(output_mp4) or os.path.getsize(output_mp4) < 1000000:
        print(f"[Step 10 ERROR] Output video not found or too small: {output_mp4}")
        sys.exit(1)

    file_mb = os.path.getsize(output_mp4) / (1024 * 1024)
    print(f"[Step 10 SUCCESS] Video_Final.mp4 rendered ({file_mb:.1f} MB in {render_time/60:.1f} mins)")

    # Advance state to Step 11
    state = youtube_agent.load_state()
    state["step"] = 11
    youtube_agent.save_state(state)
    youtube_agent.save_checkpoint(state, "Checkpoint_VideoEditing.json")

    pcfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(pcfg_path):
        with open(pcfg_path, "r", encoding="utf-8") as f:
            pcfg = json.load(f)
        pcfg["step"] = 11
        with open(pcfg_path, "w", encoding="utf-8") as f:
            json.dump(pcfg, f, indent=4)

    print("=" * 60)
    print("  STEP 10 COMPLETED SUCCESSFULLY! ADVANCED TO STEP 11.")
    print("=" * 60)

if __name__ == "__main__":
    main()
