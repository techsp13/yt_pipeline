import os
import sys
import shutil
import json
import youtube_agent
import voiceover

proj_dir = youtube_agent.get_active_project_dir()
print("[INFO] Active project directory:", proj_dir)

# 1. Parse all scenes from breakdown
scenes = youtube_agent.parse_scenes_from_file()
print(f"[INFO] Found {len(scenes)} total scenes.")

voice_dir = os.path.join(proj_dir, "07_Voice")
os.makedirs(voice_dir, exist_ok=True)

# 2. Generate local voiceovers for any scene missing audio or force fresh generation
generated_count = 0
for idx, scene in enumerate(scenes, 1):
    num = f"{scene['number']:02d}"
    audio_path = os.path.join(voice_dir, f"Scene_{num}_Voice.mp3")
    narration = scene.get("narration", "")
    
    if youtube_agent.is_title_card_scene(scene):
        continue

    # Clean narration text
    clean_text = youtube_agent.clean_narration_text(narration)
    if not clean_text or len(clean_text) < 2:
        clean_text = f"Scene {scene['number']} illustration."

    # Check if voice file missing or broken (<5KB)
    needs_gen = False
    if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 5000:
        needs_gen = True

    if needs_gen:
        print(f"[{idx}/{len(scenes)}] Generating Local Voiceover for Scene V{num}...")
        try:
            voiceover.generate_speech(clean_text, audio_path)
            generated_count += 1
            print(f"[SUCCESS] Scene V{num} generated.")
        except Exception as e:
            print(f"[ERROR] Failed to generate Scene V{num}: {e}")

print(f"[COMPLETE] Local voice generation complete. Generated {generated_count} files.")

# 3. Update state to Step 10 and launch compilation
state = youtube_agent.load_state()
state["step"] = 10
youtube_agent.save_state(state)

print("[LAUNCHING] Starting Step 10 Video Compilation...")
