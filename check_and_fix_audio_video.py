import os
import json
import shutil
import youtube_agent
import voiceover

agent_dir = r"D:\youtube_automation_agent"
active_ptr = os.path.join(agent_dir, "active_project.json")

with open(active_ptr, "r", encoding="utf-8") as f:
    proj_dir = json.load(f).get("active_project_dir")

print(f"Active Project: {proj_dir}")

if proj_dir and os.path.exists(proj_dir):
    voice_dir = os.path.join(proj_dir, "07_Voice")
    os.makedirs(voice_dir, exist_ok=True)

    scenes = youtube_agent.parse_scenes_from_file()
    print(f"Auditing voiceovers for {len(scenes)} scenes...")

    regenerated_count = 0
    for idx, scene in enumerate(scenes, 1):
        if youtube_agent.is_title_card_scene(scene):
            continue
        num = f"{scene['number']:02d}"
        audio_path = os.path.join(voice_dir, f"Scene_{num}_Voice.mp3")
        raw_narr = scene.get("narration", "")
        clean_narr = youtube_agent.clean_narration_text(raw_narr)
        if not clean_narr or len(clean_narr) < 2:
            clean_narr = f"Scene {scene['number']} narration."

        # Regenerate audio if file is missing, empty, or contained headers
        needs_regen = False
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            needs_regen = True
        elif any(header in raw_narr.upper() for header in ["ACT 1", "ACT 2", "ACT 3", "ACT 4", "NARRATOR:", "FACT-CHECK"]):
            needs_regen = True

        if needs_regen:
            print(f"[{idx}/{len(scenes)}] Regenerating clean TTS Scene V{num}: \"{clean_narr[:50]}...\"")
            success = voiceover.generate_speech(clean_narr, audio_path)
            if success:
                regenerated_count += 1

    print(f"Audio Audit Complete! Regenerated {regenerated_count} audio files.")

    # Reset state to Step 10 (Video Editing & Rendering)
    state_path = os.path.join(agent_dir, "agent_state.json")
    with open(state_path, "r", encoding="utf-8") as f:
        st = json.load(f)
    st["step"] = 10
    st["active"] = True
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=4)

    cfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["step"] = 10
        cfg["active"] = True
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

    print("State updated to Step 10. Ready for video compilation.")
