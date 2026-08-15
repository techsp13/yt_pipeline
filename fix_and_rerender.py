"""
fix_and_rerender.py
====================
Deletes placeholder audio for visual-only scenes (empty narration),
clears their clip checkpoints so Step 10 re-renders cleanly,
then sets state to Step 10 and restarts the pipeline.
"""
import os
import sys
import json
import shutil

PROJ_DIR = r"D:\youtube_automation_agent\channels\history\ancient_human_drink_chai_or_morning_drink_2026-07-29_085235"
ACTIVE_PTR = r"D:\youtube_automation_agent\active_project.json"
LOCK_FILE  = r"D:\youtube_automation_agent\.pipeline.lock"

# Point active project to this one
with open(ACTIVE_PTR, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": PROJ_DIR}, f, indent=4)

# ── 1. Load scene breakdown to identify visual-only scenes ──────────────────
import re

breakdown = os.path.join(PROJ_DIR, "04_Scenes", "Scene_Breakdown.md")
with open(breakdown, "r", encoding="utf-8") as f:
    content = f.read()

parts = re.split(r"\*\*V(\d+)\*\*", content)
visual_only = []
for i in range(1, len(parts), 2):
    scene_num = int(parts[i])
    block = parts[i + 1]
    m = re.search(r'\*\*Narration\s*:?\*\*\s*"([^"]*)"', block, re.IGNORECASE)
    narration = m.group(1).strip() if m else ""
    if not narration or len(narration) < 2:
        visual_only.append(scene_num)

print(f"Visual-only scenes detected ({len(visual_only)}): {visual_only}")

# ── 2. Delete placeholder audio + checkpoint MKV for those scenes ──────────
voice_dir = os.path.join(PROJ_DIR, "07_Voice")
checkpoint_dir = os.path.join(PROJ_DIR, "14_Checkpoints")
temp_dirs = [
    r"D:\youtube_automation_agent\_gflow_tmp_0",
    r"D:\youtube_automation_agent\_gflow_single_tmp",
]

deleted_audio = []
deleted_clips  = []
deleted_meta   = []

for n in visual_only:
    num = f"{n:02d}"
    audio_path = os.path.join(voice_dir, f"Scene_{num}_Voice.mp3")
    meta_path  = os.path.join(checkpoint_dir, f"Scene_{num}_Metadata.json")

    if os.path.exists(audio_path):
        os.remove(audio_path)
        deleted_audio.append(f"Scene_{num}_Voice.mp3")

    if os.path.exists(meta_path):
        os.remove(meta_path)
        deleted_meta.append(f"Scene_{num}_Metadata.json")

    # Also delete rendered .mkv clips from temp dirs
    for td in temp_dirs:
        clip = os.path.join(td, f"Scene_{num}.mkv")
        if os.path.exists(clip):
            os.remove(clip)
            deleted_clips.append(clip)

print(f"Deleted audio files : {deleted_audio}")
print(f"Deleted clip caches : {deleted_clips}")
print(f"Deleted metadata    : {deleted_meta}")

# ── 3. Also delete the old Final Video so it gets regenerated ───────────────
final_video = os.path.join(PROJ_DIR, "11_Final_Video", "Video_Final.mp4")
if os.path.exists(final_video):
    os.remove(final_video)
    print(f"Deleted old Video_Final.mp4 — will be re-rendered.")

# ── 4. Set pipeline step to 10 ─────────────────────────────────────────────
cfg_file = os.path.join(PROJ_DIR, "Project_Config.json")
with open(cfg_file, "r", encoding="utf-8") as f:
    state = json.load(f)

state["step"] = 10
with open(cfg_file, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4)

print("Step set to 10. All corrupt audio removed. Ready for clean re-render.")
print(f"\nRun: python youtube_agent.py")
