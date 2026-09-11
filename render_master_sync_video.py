import os, sys, json, re, wave, time, subprocess, shutil
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import numpy as np

# Add repo to sys.path
sys.path.insert(0, r"D:\youtube_automation_agent")
from stickman_engine import build_presenter_sequence

FPS = 25
AGENT_DIR = r"D:\youtube_automation_agent"
ACTIVE_JSON = os.path.join(AGENT_DIR, "active_project.json")

with open(ACTIVE_JSON, encoding="utf-8") as f:
    ACTIVE_PROJ = json.load(f)["active_project_dir"]

VOICE_DIR       = os.path.join(ACTIVE_PROJ, "07_Voice")
CHECKPOINT_DIR  = os.path.join(ACTIVE_PROJ, "14_Checkpoints")
SCENES_DIR      = os.path.join(ACTIVE_PROJ, "04_Scenes")
IMAGES_DIR      = os.path.join(ACTIVE_PROJ, "06_Images")
FINAL_VIDEO_DIR = os.path.join(ACTIVE_PROJ, "11_Final_Video")
TEMP_CLIPS_DIR  = os.path.join(ACTIVE_PROJ, "output_temp", "master_sync_clips")

MASTER_MP3    = os.path.join(VOICE_DIR, "Full_Script_Voice.mp3")
MASTER_WAV    = os.path.join(VOICE_DIR, "Full_Script_Voice_pcm.wav")
SCRIPT_JSON   = os.path.join(SCENES_DIR, "Scene_List.json")
TIMELINE_PATH = os.path.join(CHECKPOINT_DIR, "Scene_Timeline.json")
FINAL_VIDEO_P = os.path.join(FINAL_VIDEO_DIR, "Video_Final.mp4")

os.makedirs(TEMP_CLIPS_DIR, exist_ok=True)
os.makedirs(FINAL_VIDEO_DIR, exist_ok=True)

def get_wav_duration(p):
    with wave.open(p, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())

total_audio_dur = get_wav_duration(MASTER_WAV)
total_frames = int(round(total_audio_dur * FPS))

print("==========================================================")
print("  MASTER AUDIO-VISUAL EXACT WORD-SYNC PIPELINE")
print("==========================================================")
print(f"Project             : {ACTIVE_PROJ}")
print(f"Master Audio Dur    : {total_audio_dur:.4f}s ({total_frames} frames at {FPS} FPS)")

# 1. Load Timeline
if not os.path.exists(TIMELINE_PATH):
    print("Generating Scene_Timeline.json via build_perfect_continuous_timeline...")
    import build_perfect_continuous_timeline
    build_perfect_continuous_timeline.main()

with open(TIMELINE_PATH, "r", encoding="utf-8") as f:
    tl_data = json.load(f)

timeline_scenes = tl_data.get("scenes", [])
print(f"Loaded {len(timeline_scenes)} timeline scenes.")

# 2. Load Script
with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
    script_data = json.load(f)
raw_scenes = script_data if isinstance(script_data, list) else script_data.get("scenes", [])
scene_narr_map = {s["number"]: s.get("narration", "") for s in raw_scenes}

# 3. Render Silent Scene Video Clip with Animated Stickman
def render_single_scene(item):
    idx, ts = item
    s_num = ts["number"]
    num_str = f"{s_num:02d}"
    target_dur = ts["duration"]
    target_frames = ts["frame_count"]
    narr_text = scene_narr_map.get(s_num, "")

    clip_out = os.path.join(TEMP_CLIPS_DIR, f"Scene_{num_str}.mp4")

    # Image resolution
    alt_paths = [
        os.path.join(IMAGES_DIR, f"{s_num:03d}_Scene_{num_str}.png"),
        os.path.join(IMAGES_DIR, "Final", f"Scene_{num_str}.png"),
        os.path.join(IMAGES_DIR, "Approved", f"Scene_{num_str}.png"),
        os.path.join(IMAGES_DIR, f"Scene_{num_str}_v1.png")
    ]
    img_p = None
    for ap in alt_paths:
        if os.path.exists(ap):
            img_p = ap
            break

    if not img_p:
        print(f"ERROR: No image found for Scene {num_str}!")
        return None

    # Load Background Image
    BG_W, BG_H = 1920, 1080
    bg_img = Image.open(img_p).convert("RGBA").resize((BG_W, BG_H), Image.LANCZOS)

    # Generate Stickman Animated Presenter Frames
    STICK_H = 620  # Presenter size in bottom corner
    STICK_W = int(1080 / 1920 * STICK_H)
    pos_x = int(BG_W * 0.10)
    pos_y = BG_H - STICK_H + 20

    raw_stick_frames, _, _ = build_presenter_sequence(
        narration=narr_text,
        total_frames=target_frames,
        scene_index=idx,
        cy=1380.0,
        s=2.2,
        bg_color=(0, 0, 0, 0)
    )

    # Pipe composited RGB frames into FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{BG_W}x{BG_H}", "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-an",
        clip_out
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for f_i in range(target_frames):
        stick_idx = min(f_i, len(raw_stick_frames) - 1)
        stick_img = raw_stick_frames[stick_idx].resize((STICK_W, STICK_H), Image.LANCZOS)
        
        frame = bg_img.copy()
        frame.alpha_composite(stick_img, dest=(pos_x, pos_y))
        frame_rgb = frame.convert("RGB")
        proc.stdin.write(frame_rgb.tobytes())

    proc.stdin.close()
    proc.wait()

    if os.path.exists(clip_out) and os.path.getsize(clip_out) > 1000:
        print(f"Scene V{num_str}: Rendered {target_frames} frames ({target_dur:.2f}s) -> {os.path.basename(clip_out)}")
        return (idx, s_num, clip_out, target_frames)
    else:
        print(f"FAILED Scene V{num_str}!")
        return None

print(f"\nRendering {len(timeline_scenes)} silent scene clips with speaking stickman (8 worker threads)...")
t0 = time.time()

items = list(enumerate(timeline_scenes))
rendered_clips = []

with ThreadPoolExecutor(max_workers=8) as executor:
    for res in executor.map(render_single_scene, items):
        if res:
            rendered_clips.append(res)

rendered_clips.sort(key=lambda x: x[0])
print(f"\nSUCCESS! {len(rendered_clips)}/{len(timeline_scenes)} clips rendered in {time.time()-t0:.1f}s")

# 4. Concatenate All Clips
concat_txt = os.path.join(ACTIVE_PROJ, "output_temp", "master_concat_list.txt")
with open(concat_txt, "w", encoding="utf-8") as f:
    for _, s_num, c_path, _ in rendered_clips:
        clean_p = c_path.replace("\\", "/")
        f.write(f"file '{clean_p}'\n")

# 5. Mux Untouched Master Audio in ONE SINGLE PASS
print("\nConcatenating visual stream and muxing 100% UNTOUCHED master audio in 1 pass...")
t1 = time.time()

cmd_final = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_txt,
    "-i", MASTER_MP3,
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    FINAL_VIDEO_P
]
subprocess.run(cmd_final, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

print(f"==========================================================")
print(f"MASTER VIDEO ASSEMBLY COMPLETE in {time.time()-t1:.1f}s!")
print(f"Final Video : {FINAL_VIDEO_P}")
print(f"File Size   : {os.path.getsize(FINAL_VIDEO_P)/(1024*1024):.2f} MB")
print(f"==========================================================")