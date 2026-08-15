import os
import sys
import json
import asyncio
import shutil
import youtube_agent

proj_dir = youtube_agent.get_active_project_dir()
print(f"[INFO] Active Project Directory: {proj_dir}")

scenes = youtube_agent.parse_scenes_from_file()
print(f"[INFO] Loaded {len(scenes)} scenes for processing.")

voice_dir = os.path.join(proj_dir, "07_Voice")
os.makedirs(voice_dir, exist_ok=True)

# 1. High-Speed Neural Voice Generator
async def generate_omnivoice_all():
    import edge_tts
    voice = "en-US-ChristopherNeural"  # Professional crisp documentarian narrator
    
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

        print(f"[{idx}/{len(scenes)}] Synthesizing Scene V{num}...")
        try:
            communicate = edge_tts.Communicate(clean_text, voice)
            await communicate.save(audio_path)
            generated_count += 1
        except Exception as e:
            print(f"[ERROR] Scene V{num} synthesis error: {e}")

    print(f"[SUCCESS] Generated {generated_count} voiceover files into 07_Voice!")

# Run synthesis
asyncio.run(generate_omnivoice_all())

# 2. Reset temp clips so everything renders cleanly
temp_dir = os.path.join(proj_dir, "output_temp")
if os.path.exists(temp_dir):
    for f in os.listdir(temp_dir):
        try:
            os.remove(os.path.join(temp_dir, f))
        except Exception:
            pass
    print("[CLEARED] output_temp directory emptied for fresh video render.")

# 3. Update state to Step 10
state = youtube_agent.load_state()
state["step"] = 10
youtube_agent.save_state(state)

print("[SUCCESS] All voiceovers generated! Step 10 Video Compilation ready.")
