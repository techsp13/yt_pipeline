import os, sys, json, re, wave, time, subprocess, shutil
from PIL import Image
import numpy as np

sys.path.insert(0, r"D:\youtube_automation_agent")
from pytoon_renderer import ChannelPytoonAnimator

FPS = 25
BG_W, BG_H = 1920, 1080
CHAR_H = 430

AGENT_DIR = r"D:\youtube_automation_agent"
with open(os.path.join(AGENT_DIR, "active_project.json"), encoding="utf-8") as f:
    PROJ_DIR = json.load(f)["active_project_dir"]

VOICE_DIR    = os.path.join(PROJ_DIR, "07_Voice")
MASTER_MP3   = os.path.join(VOICE_DIR, "Full_Script_Voice.mp3")
MASTER_WAV   = os.path.join(VOICE_DIR, "Full_Script_Voice_pcm.wav")
IMAGES_DIR   = os.path.join(PROJ_DIR, "06_Images")
FINAL_DIR    = os.path.join(PROJ_DIR, "11_Final_Video")
TEMP_WAV_DIR = os.path.join(PROJ_DIR, "output_temp", "verification_wavs")
os.makedirs(TEMP_WAV_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

# Define the exact 6 scenes requested by the user
scenes = [
    {"num": 1, "start": 0.00,  "end": 2.24,  "dur": 2.24, "narr": "You’re standing in tall grass,"},
    {"num": 2, "start": 2.24,  "end": 4.08,  "dur": 1.84, "narr": "heart thumping. The air smells"},
    {"num": 3, "start": 4.08,  "end": 6.76,  "dur": 2.68, "narr": "like dust and something else…"},
    {"num": 4, "start": 6.76,  "end": 8.60,  "dur": 1.84, "narr": "…something wild. You grip your"},
    {"num": 5, "start": 8.60,  "end": 11.48, "dur": 2.88, "narr": "spear, or maybe a muzzle-loader,"},
    {"num": 6, "start": 11.48, "end": 13.60, "dur": 2.12, "narr": "your eyes scanning the horizon,"},
]

total_dur = 13.60
total_frames = int(round(total_dur * FPS))

print("==========================================================")
print("  RENDERING VERIFICATION VIDEO: SCENES 1 TO 6")
print("==========================================================")
print(f"Total Duration: {total_dur:.2f}s ({total_frames} frames @ {FPS} FPS)")

# 1. Slice audio for the 6 scenes for PyToon Wav2Vec2 analysis
for sc in scenes:
    sn = sc["num"]
    wav_p = os.path.join(TEMP_WAV_DIR, f"scene_{sn:03d}.wav")
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{sc['start']:.4f}", "-to", f"{sc['end']:.4f}",
        "-i", MASTER_WAV,
        "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
        wav_p
    ]
    subprocess.run(cmd, check=True)
    sc["wav"] = wav_p

# Slice master audio segment (0.00s to 13.60s)
sample_audio = os.path.join(TEMP_WAV_DIR, "master_sample_13.6s.wav")
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-ss", "0.0000", "-to", f"{total_dur:.4f}",
    "-i", MASTER_WAV,
    "-c:a", "pcm_s16le",
    sample_audio
], check=True)

# 2. Open single FFmpeg pipe
out_mp4 = os.path.join(FINAL_DIR, "Verification_Scenes_1_to_6.mp4")

cmd_ffmpeg = [
    "ffmpeg", "-y",
    "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{BG_W}x{BG_H}", "-r", str(FPS),
    "-i", "pipe:0",
    "-i", sample_audio,
    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    "-movflags", "+faststart",
    out_mp4
]

proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 3. Render and pipe each scene's frames
total_written = 0
for sc in scenes:
    sn = sc["num"]
    target_frames = int(round(sc["dur"] * FPS))
    narr = sc["narr"]
    wav_p = sc["wav"]
    img_name = f"{sn:03d}_Scene_{sn:02d}.png"
    img_p = os.path.join(IMAGES_DIR, img_name)

    print(f"Rendering Scene {sn} ({sc['start']:.2f}s -> {sc['end']:.2f}s | {target_frames} frames)...")
    print(f"  Image: {img_name}")
    print(f"  Narration: {narr}")

    bg = Image.open(img_p).convert("RGBA").resize((BG_W, BG_H), Image.LANCZOS)

    anim = ChannelPytoonAnimator(
        audio_file=wav_p,
        transcript=narr,
        channel="history",
        fps=FPS
    )
    char_frames = anim.final_frames
    n_char = len(char_frames)

    for fi in range(target_frames):
        frame = bg.copy()
        if n_char > 0:
            ci = min(fi, n_char - 1)
            char_np = char_frames[ci]
            char_img = Image.fromarray(char_np).convert("RGBA")

            w, h = char_img.size
            aspect = w / h
            new_h = CHAR_H
            new_w = int(new_h * aspect)
            char_resized = char_img.resize((new_w, new_h), Image.LANCZOS)

            pos_x = BG_W - new_w - 60
            pos_y = BG_H - new_h + 10
            frame.alpha_composite(char_resized, dest=(pos_x, pos_y))

        proc.stdin.write(frame.convert("RGB").tobytes())
        total_written += 1

proc.stdin.close()
proc.wait()

print(f"\n==========================================================")
print(f"✅ VERIFICATION VIDEO READY!")
print(f"Output Video : {out_mp4}")
print(f"Total Frames : {total_written} ({total_written/FPS:.2f}s)")
print(f"File Size    : {os.path.getsize(out_mp4)/(1024*1024):.2f} MB")
print(f"==========================================================")

# Send to Telegram for instant mobile check
try:
    import telegram_bot
    telegram_bot.send_video(out_mp4, caption="🎬 *Verification Video: Scenes 1 to 6 (1:1 Word Sync + PyToon)*\n\n• Scene 1 (0.00s-2.24s): Tall grass\n• Scene 2 (2.24s-4.08s): Heart thumping\n• Scene 3 (4.08s-6.76s): Dust\n• Scene 4 (6.76s-8.60s): Gripping spear\n• Scene 5 (8.60s-11.48s): Spear & muzzle-loader\n• Scene 6 (11.48s-13.60s): Scanning horizon")
    print("Sent to Telegram successfully!")
except Exception as e:
    print(f"Telegram send notice: {e}")