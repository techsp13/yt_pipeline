import os
import sys
import json
import subprocess
import time

AGENT_DIR = r"D:\youtube_automation_agent"
sys.path.insert(0, AGENT_DIR)

import youtube_agent
import voiceover
import telegram_bot
import build_perfect_continuous_timeline

def main():
    print("=" * 60)
    print("  STEP 8: VOICE GENERATION & CONTINUOUS TIMELINE")
    print("=" * 60)

    proj_dir = youtube_agent.get_active_project_dir()
    print(f"Active Project: {proj_dir}")

    voice_dir = os.path.join(proj_dir, "07_Voice")
    os.makedirs(voice_dir, exist_ok=True)

    # 1. Parse scenes
    scene_list_file = os.path.join(proj_dir, "04_Scenes", "Scene_List.json")
    if os.path.exists(scene_list_file):
        with open(scene_list_file, "r", encoding="utf-8") as f:
            scenes = json.load(f)
    else:
        scenes = youtube_agent.parse_scenes_from_file()

    valid_scenes = []
    for sc in scenes:
        if sc.get("is_title_card", False) or sc.get("scene_type", "") == "title_card":
            continue
        narration = youtube_agent.clean_narration_text(sc.get("narration", ""))
        if narration and len(narration) >= 2:
            valid_scenes.append((sc, narration))

    print(f"Total scenes: {len(scenes)}, Narration scenes: {len(valid_scenes)}")
    telegram_bot.send_message(
        f"🎙️ *STEP 8: Voice Generation*\nGenerating full-script continuous narration ({len(valid_scenes)} scenes)..."
    )

    full_audio_path = os.path.join(voice_dir, "Full_Script_Voice.mp3")
    pcm_wav_path = os.path.join(voice_dir, "Full_Script_Voice_pcm.wav")

    delimiter = " ... "
    full_transcript = delimiter.join([n for _, n in valid_scenes])

    if os.path.exists(full_audio_path) and os.path.getsize(full_audio_path) > 10000:
        print(f"[Step 8] Full_Script_Voice.mp3 already exists ({os.path.getsize(full_audio_path)//1024} KB). Skipping TTS.")
        success = True
    else:
        print(f"[Step 8] Calling Cartesia TTS for full script ({len(full_transcript)} characters)...")
        t0 = time.time()
        success = voiceover.generate_speech(full_transcript, full_audio_path)
        print(f"[Step 8] Cartesia TTS returned {success} in {time.time()-t0:.1f}s")

    if not success or not os.path.exists(full_audio_path) or os.path.getsize(full_audio_path) < 1000:
        print("[Step 8] ERROR: Full script TTS generation failed!")
        telegram_bot.send_message("❌ *Step 8 Failed:* Full script voice generation error.")
        sys.exit(1)

    print(f"[Step 8] Full_Script_Voice.mp3 generated successfully ({os.path.getsize(full_audio_path)//1024} KB)")

    # 2. Convert to PCM WAV
    print(f"[Step 8] Converting to PCM WAV: {pcm_wav_path}...")
    ffmpeg = youtube_agent.get_ffmpeg_path()
    subprocess.run(
        [ffmpeg, "-y", "-i", full_audio_path, "-ac", "1", "-ar", "24000", pcm_wav_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
    print(f"[Step 8] PCM WAV saved ({os.path.getsize(pcm_wav_path)//1024} KB)")

    # 3. Build Timeline with faster-whisper forced alignment
    print("[Step 8] Building 100% gap-free frame-snapped continuous timeline...")
    build_perfect_continuous_timeline.main()

    timeline_path = os.path.join(proj_dir, "14_Checkpoints", "Scene_Timeline.json")
    if not os.path.exists(timeline_path):
        print(f"[Step 8] ERROR: {timeline_path} not found!")
        sys.exit(1)

    with open(timeline_path, "r", encoding="utf-8") as f:
        tl_data = json.load(f)

    tl_scenes_count = len(tl_data.get("scenes", []))
    total_audio_dur = tl_data.get("total_audio_duration", 0)
    print(f"[Step 8] Timeline contains {tl_scenes_count} scenes. Total audio duration: {total_audio_dur:.2f}s ({total_audio_dur/60:.1f} mins)")

    # 4. Advance State to Step 10
    state = youtube_agent.load_state()
    state["step"] = 10
    youtube_agent.save_state(state)
    youtube_agent.save_checkpoint(state, "Checkpoint_VoiceGeneration.json")

    pcfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(pcfg_path):
        with open(pcfg_path, "r", encoding="utf-8") as f:
            pcfg = json.load(f)
        pcfg["step"] = 10
        with open(pcfg_path, "w", encoding="utf-8") as f:
            json.dump(pcfg, f, indent=4)

    telegram_bot.send_message(
        f"✅ *Step 8: Voice Generation Complete!*\n\n"
        f"• Duration: *{total_audio_dur:.1f}s* (~{total_audio_dur/60:.1f} minutes)\n"
        f"• Total Scenes in Timeline: *{tl_scenes_count}*\n"
        f"• Continuity: *100% Gap-Free Frame-Snapped*\n"
        f"• Next Step: *Step 10 (Video Editing & Rendering)*"
    )
    print("=" * 60)
    print("  STEP 8 COMPLETED SUCCESSFULLY! ADVANCED TO STEP 10.")
    print("=" * 60)

if __name__ == "__main__":
    main()
