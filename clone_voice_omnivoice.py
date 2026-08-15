import os
import sys
import json
import youtube_agent
import voiceover

proj_dir = youtube_agent.get_active_project_dir()
print(f"[INFO] Active Project Directory: {proj_dir}")

ref_voice_path = os.path.join(os.path.dirname(__file__), "reference_voice.wav")
if not os.path.exists(ref_voice_path):
    print(f"[ERROR] Reference voice not found at: {ref_voice_path}")
    sys.exit(1)

print(f"[INFO] Using Reference Voice: {ref_voice_path}")

scenes = youtube_agent.parse_scenes_from_file()
voice_dir = os.path.join(proj_dir, "07_Voice")
os.makedirs(voice_dir, exist_ok=True)

# 1. Zero-shot voice cloning in reference_voice.wav for all scenes
generated_count = 0
for idx, scene in enumerate(scenes, 1):
    num = f"{scene['number']:02d}"
    audio_path = os.path.join(voice_dir, f"Scene_{num}_Voice.mp3")
    narration = scene.get("narration", "")
    
    if youtube_agent.is_title_card_scene(scene):
        continue

    clean_text = youtube_agent.clean_narration_text(narration)
    if not clean_text or len(clean_text) < 2:
        clean_text = f"Scene {scene['number']} illustration."

    print(f"[{idx}/{len(scenes)}] Cloning voice for Scene V{num} in reference voice...")
    try:
        voiceover.generate_speech(clean_text, audio_path)
        generated_count += 1
        print(f"[SUCCESS] Scene V{num} cloned.")
    except Exception as e:
        print(f"[ERROR] Scene V{num} error: {e}")

print(f"[SUCCESS] Cloned {generated_count} scenes into 07_Voice in your reference voice!")

# 2. Reset temp clips
temp_dir = os.path.join(proj_dir, "output_temp")
if os.path.exists(temp_dir):
    for f in os.listdir(temp_dir):
        try:
            os.remove(os.path.join(temp_dir, f))
        except Exception:
            pass

# 3. Update step to 10
state = youtube_agent.load_state()
state["step"] = 10
youtube_agent.save_state(state)

print("[COMPLETE] Step 10 Video Compilation ready!")
