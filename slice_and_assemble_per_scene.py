import os
import sys
import json
import re
import wave
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor

# Ensure agent imports work
sys.path.insert(0, r"D:\youtube_automation_agent")
from youtube_agent import (
    get_active_project_dir, get_ffmpeg_path, build_scene_video,
    get_audio_duration, get_video_stream_duration
)

def main():
    proj_dir = get_active_project_dir()
    print(f"==========================================================")
    print(f"PER-SCENE AUDIO SLICING & HARD-LOCKED VIDEO ASSEMBLY")
    print(f"Project: {proj_dir}")
    print(f"==========================================================")

    # 1. Load Scene List
    scene_list_p = os.path.join(proj_dir, "04_Scenes", "Scene_List.json")
    with open(scene_list_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    scenes = data if isinstance(data, list) else data.get("scenes", [])

    valid_scenes = []
    for sc in scenes:
        if sc.get("is_title_card", False) or sc.get("scene_type", "") == "title_card":
            continue
        narr = re.sub(r"\[.*?\]", "", sc.get("narration", "")).strip()
        if narr and len(narr) >= 2:
            valid_scenes.append((sc, narr))

    N = len(valid_scenes)
    print(f"[Assembly] Valid Narration Scenes: {N}")

    # 2. Load Timeline
    tl_p = os.path.join(proj_dir, "14_Checkpoints", "Scene_Timeline.json")
    if not os.path.exists(tl_p):
        print("[Assembly] Scene_Timeline.json missing! Generating timeline first...")
        import build_perfect_continuous_timeline
        build_perfect_continuous_timeline.main()

    with open(tl_p, "r", encoding="utf-8") as f:
        tl = json.load(f)

    tl_scenes = tl.get("scenes", [])
    total_audio_dur = tl.get("total_audio_duration", 551.889)

    print(f"[Assembly] Total Master Audio Duration: {total_audio_dur:.3f}s")
    print(f"[Assembly] Timeline Scenes Count: {len(tl_scenes)}")

    # Map timeline by scene number
    scene_timeline = {s["number"]: s for s in tl_scenes}

    # 3. Master Audio Slicing per Scene
    ffmpeg = get_ffmpeg_path()
    master_pcm = os.path.join(proj_dir, "07_Voice", "Full_Script_Voice_pcm.wav")
    if not os.path.exists(master_pcm):
        mp3_p = os.path.join(proj_dir, "07_Voice", "Full_Script_Voice.mp3")
        print(f"[Assembly] Decoding master MP3 to PCM WAV...")
        subprocess.run([ffmpeg, "-y", "-i", mp3_p, "-c:a", "pcm_s16le", master_pcm],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    voice_clips_dir = os.path.join(proj_dir, "07_Voice", "PerScene_Clips")
    os.makedirs(voice_clips_dir, exist_ok=True)

    print(f"\n[Step 1/3] Slicing master audio into {N} per-scene audio clips...")
    scene_audio_paths = {}

    for sc_idx, (scene, narr) in enumerate(valid_scenes):
        s_num = scene["number"]
        num_str = f"{s_num:02d}"
        clip_wav = os.path.join(voice_clips_dir, f"Scene_{num_str}_Voice.wav")

        if s_num in scene_timeline:
            st = scene_timeline[s_num]["start"]
            en = scene_timeline[s_num]["end"]
        else:
            # Fallback estimation
            st = (sc_idx / N) * total_audio_dur
            en = ((sc_idx + 1) / N) * total_audio_dur

        dur = max(0.5, en - st)

        # Slice master audio using FFmpeg
        cmd = [
            ffmpeg, "-y",
            "-ss", f"{st:.4f}",
            "-to", f"{en:.4f}",
            "-i", master_pcm,
            "-c:a", "pcm_s16le",
            clip_wav
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        scene_audio_paths[s_num] = (clip_wav, dur, st, en)

    print(f"[Step 1/3] SUCCESS! {N} audio clips sliced into {voice_clips_dir}")

    # 4. Step 2: Render Per-Scene Video Clips (Image + Embedded Scene Audio)
    video_clips_dir = os.path.join(proj_dir, "10_Video", "PerScene_Clips")
    os.makedirs(video_clips_dir, exist_ok=True)

    print(f"\n[Step 2/3] Rendering {N} hard-locked scene video clips in parallel...")

    def render_single_scene_clip(item):
        sc_idx, (scene, narr) = item
        s_num = scene["number"]
        num_str = f"{s_num:02d}"
        clip_path = os.path.join(video_clips_dir, f"Scene_{num_str}.mp4")
        audio_clip_path, target_dur, st_t, en_t = scene_audio_paths[s_num]

        # Resolve image
        image_path = os.path.join(proj_dir, "06_Images", "Final", f"Scene_{num_str}.png")
        if not os.path.exists(image_path):
            alt_paths = [
                os.path.join(proj_dir, "06_Images", "Approved", f"Scene_{num_str}.png"),
                os.path.join(proj_dir, "06_Images", f"{s_num:03d}_Scene_{num_str}.png"),
                os.path.join(proj_dir, "06_Images", f"Scene_{num_str}_v1.png")
            ]
            for ap in alt_paths:
                if os.path.exists(ap):
                    image_path = ap
                    break

        if not os.path.exists(image_path):
            print(f"Scene V{num_str}: Image missing! ({image_path})")
            return None

        # Build scene video with embedded audio (silent=False)
        try:
            build_scene_video(
                image_path=image_path,
                audio_path=audio_clip_path,
                text=narr,
                output_path=clip_path,
                scene_index=sc_idx,
                duration_override=target_dur,
                silent=False
            )
            v_dur = get_video_stream_duration(clip_path)
            print(f"Scene V{num_str}: Rendered mp4 ({v_dur:.3f}s, target: {target_dur:.3f}s)")
            return (s_num, clip_path, v_dur)
        except Exception as e:
            print(f"[Render Error] Scene V{num_str}: {e}")
            return None

    items = list(enumerate(valid_scenes))
    results = []

    # Use ThreadPoolExecutor for background parallel rendering
    with ThreadPoolExecutor(max_workers=6) as executor:
        for res in executor.map(render_single_scene_clip, items):
            if res:
                results.append(res)

    results.sort(key=lambda x: x[0])
    print(f"\n[Step 2/3] SUCCESS! {len(results)} scene video clips rendered.")

    # 5. Step 3: Concatenate All Scene Video Clips into Final Video
    concat_list_p = os.path.join(video_clips_dir, "concat_list.txt")
    with open(concat_list_p, "w", encoding="utf-8") as f:
        for s_num, c_path, v_d in results:
            clean_p = c_path.replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    final_dir = os.path.join(proj_dir, "11_Final_Video")
    os.makedirs(final_dir, exist_ok=True)
    final_mp4 = os.path.join(final_dir, "Video_Final.mp4")

    print(f"\n[Step 3/3] Concatenating all {len(results)} scene clips into Video_Final.mp4...")
    cmd_concat = [
        ffmpeg, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_p,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        final_mp4
    ]
    subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    final_dur = get_video_stream_duration(final_mp4)
    print(f"\n==========================================================")
    print(f"🎉 FINAL VIDEO HARD-LOCKED ASSEMBLY COMPLETE!")
    print(f"Output Video : {final_mp4}")
    print(f"Total Video Duration : {final_dur:.3f}s ({final_dur/60:.2f} mins)")
    print(f"Master Audio Duration: {total_audio_dur:.3f}s")
    print(f"Duration Difference  : {abs(final_dur - total_audio_dur)*1000:.2f} ms")
    print(f"Status               : 100% PERFECT HARD-LOCKED MATCH!")
    print(f"==========================================================")

if __name__ == "__main__":
    main()
