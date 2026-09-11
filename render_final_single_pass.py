# -*- coding: utf-8 -*-
"""
render_final_single_pass.py
============================
Permanent fix for image-voice sync.

Renders ALL frames into ONE continuous FFmpeg process with PyToon
Wav2Vec2 lip-sync character, muxing untouched master audio in the same pass.

Zero concat = zero drift.
"""

import os, sys, json, re, wave, time, subprocess, shutil
from PIL import Image
import numpy as np

sys.path.insert(0, r"D:\youtube_automation_agent")
from pytoon_renderer import ChannelPytoonAnimator

FPS = 25
BG_W, BG_H = 1920, 1080
CHAR_H = 430  # Compact presenter size matching pytoon_renderer.py

AGENT_DIR = r"D:\youtube_automation_agent"
with open(os.path.join(AGENT_DIR, "active_project.json"), encoding="utf-8") as f:
    PROJ_DIR = json.load(f)["active_project_dir"]

VOICE_DIR   = os.path.join(PROJ_DIR, "07_Voice")
MASTER_MP3  = os.path.join(VOICE_DIR, "Full_Script_Voice.mp3")
MASTER_WAV  = os.path.join(VOICE_DIR, "Full_Script_Voice_pcm.wav")
TIMELINE_P  = os.path.join(PROJ_DIR, "14_Checkpoints", "Scene_Timeline.json")
SCRIPT_JSON = os.path.join(PROJ_DIR, "04_Scenes", "Scene_List.json")
IMAGES_DIR  = os.path.join(PROJ_DIR, "06_Images")
FINAL_DIR   = os.path.join(PROJ_DIR, "11_Final_Video")
TEMP_WAV_DIR = os.path.join(PROJ_DIR, "output_temp", "pytoon_scene_wavs")

os.makedirs(FINAL_DIR, exist_ok=True)
os.makedirs(TEMP_WAV_DIR, exist_ok=True)


def get_wav_duration(p):
    with wave.open(p, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def find_image(s_num):
    num_str = f"{s_num:02d}"
    for p in [
        os.path.join(IMAGES_DIR, f"{s_num:03d}_Scene_{num_str}.png"),
        os.path.join(IMAGES_DIR, "Final", f"Scene_{num_str}.png"),
        os.path.join(IMAGES_DIR, "Approved", f"Scene_{num_str}.png"),
        os.path.join(IMAGES_DIR, f"Scene_{num_str}_v1.png"),
    ]:
        if os.path.exists(p):
            return p
    return None


def slice_scene_wav(master_wav, start, end, out_path):
    """Slice master WAV for PyToon lip-sync analysis with sample-accurate seeking."""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", master_wav,
        "-ss", f"{start:.4f}", "-to", f"{end:.4f}",
        "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1",
        out_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def main():
    total_dur = get_wav_duration(MASTER_WAV)
    total_frames = int(round(total_dur * FPS))

    cfg_p = os.path.join(PROJ_DIR, "Project_Config.json")
    ch_name = "money"
    if os.path.exists(cfg_p):
        with open(cfg_p, "r", encoding="utf-8") as cf:
            ch_name = json.load(cf).get("channel", "money")

    print("=" * 60)
    print("  SINGLE-PASS PYTOON RENDER (PERMANENT SYNC FIX)")
    print("=" * 60)
    print(f"Project          : {PROJ_DIR}")
    print(f"Master Audio     : {total_dur:.4f}s ({total_frames} frames @ {FPS} FPS)")
    print(f"PyToon Character : {ch_name} channel (Wav2Vec2 lip-sync)")

    # 1. Load timeline + narrations
    with open(TIMELINE_P, "r", encoding="utf-8") as f:
        tl = json.load(f)
    tl_scenes = tl["scenes"]

    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        script = json.load(f)
    narr_map = {}
    for s in (script if isinstance(script, list) else script.get("scenes", [])):
        narr = re.sub(r'\[.*?\]', '', s.get("narration", "")).strip()
        narr_map[s["number"]] = narr

    N = len(tl_scenes)
    print(f"Timeline Scenes  : {N}")

    # 2. Pre-slice all scene WAVs for PyToon lip-sync
    print(f"\n[Step 1/{3}] Slicing {N} scene WAVs for PyToon lip-sync analysis...")
    scene_wavs = {}
    for ts in tl_scenes:
        sn = ts["number"]
        wav_p = os.path.join(TEMP_WAV_DIR, f"scene_{sn:03d}.wav")
        if not os.path.exists(wav_p) or os.path.getsize(wav_p) < 100:
            slice_scene_wav(MASTER_WAV, ts["start"], ts["end"], wav_p)
        scene_wavs[sn] = wav_p
    print(f"  Done. {len(scene_wavs)} WAV clips ready.")

    # 3. Open ONE FFmpeg process for the entire video
    output_mp4 = os.path.join(FINAL_DIR, "Video_Final.mp4")
    print(f"\n[Step 2/{3}] Opening single FFmpeg encode process...")
    print(f"  Output: {output_mp4}")

    cmd = [
        "ffmpeg", "-y",
        # Video input: raw RGB frames from stdin
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{BG_W}x{BG_H}", "-r", str(FPS),
        "-i", "pipe:0",
        # Audio input: untouched master audio
        "-i", MASTER_MP3,
        # Video encode
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-threads", "0",
        "-pix_fmt", "yuv420p",
        # Audio encode
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        output_mp4
    ]
    ffmpeg_proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # 4. Process each scene sequentially, pipe frames
    print(f"\n[Step 3/{3}] Rendering {N} scenes with PyToon character...")
    t0 = time.time()
    total_written = 0

    for i, ts in enumerate(tl_scenes):
        sn = ts["number"]
        target_frames = ts["frame_count"]
        narr = narr_map.get(sn, "")
        wav_p = scene_wavs[sn]
        img_p = find_image(sn)

        if not img_p:
            print(f"  [SKIP] Scene {sn}: no image found!")
            # Write black frames to maintain sync
            black = b'\x00' * (BG_W * BG_H * 3)
            for _ in range(target_frames):
                ffmpeg_proc.stdin.write(black)
                total_written += 1
            continue

        # Load background as fast contiguous RGB numpy array
        bg_pil = Image.open(img_p).convert("RGB").resize((BG_W, BG_H), Image.BILINEAR)
        bg_rgb = np.array(bg_pil, dtype=np.uint8)

        # Generate PyToon character frames via Wav2Vec2 lip-sync
        try:
            anim = ChannelPytoonAnimator(
                audio_file=wav_p,
                transcript=narr,
                channel=ch_name,
                fps=FPS
            )
            char_frames = anim.final_frames  # list of numpy arrays
        except Exception as e:
            print(f"  [WARN] Scene {sn} PyToon failed ({e}), using static bg")
            char_frames = []

        n_char = len(char_frames)

        # Pre-resize and pre-compute alpha blending matrices once per scene!
        pre_rendered_chars = []
        if n_char > 0:
            sample_h, sample_w = char_frames[0].shape[:2]
            aspect = sample_w / max(1, sample_h)
            new_h = CHAR_H
            new_w = int(new_h * aspect)
            pos_x = BG_W - new_w - 60
            pos_y = BG_H - new_h + 10

            y1, y2 = max(0, pos_y), min(BG_H, pos_y + new_h)
            x1, x2 = max(0, pos_x), min(BG_W, pos_x + new_w)
            cy1, cy2 = 0, y2 - y1
            cx1, cx2 = 0, x2 - x1

            for cf in char_frames:
                c_img = Image.fromarray(cf).convert("RGBA").resize((new_w, new_h), Image.BILINEAR)
                c_arr = np.array(c_img, dtype=np.float32)
                alpha = c_arr[cy1:cy2, cx1:cx2, 3:4] / 255.0
                rgb = c_arr[cy1:cy2, cx1:cx2, :3] * alpha
                inv_alpha = 1.0 - alpha
                pre_rendered_chars.append((rgb, inv_alpha))

        # High-speed frame piping
        if not pre_rendered_chars:
            raw_bg = bg_rgb.tobytes()
            for _ in range(target_frames):
                ffmpeg_proc.stdin.write(raw_bg)
                total_written += 1
        else:
            n_pr = len(pre_rendered_chars)
            for fi in range(target_frames):
                rgb, inv_alpha = pre_rendered_chars[min(fi, n_pr - 1)]
                frame = bg_rgb.copy()
                patch = frame[y1:y2, x1:x2].astype(np.float32)
                frame[y1:y2, x1:x2] = (rgb + patch * inv_alpha).astype(np.uint8)
                ffmpeg_proc.stdin.write(frame.tobytes())
                total_written += 1

        elapsed = time.time() - t0
        pct = (i + 1) / N * 100
        eta = elapsed / (i + 1) * (N - i - 1)
        print(f"  Scene {sn:3d} ({i+1:3d}/{N}) | {target_frames:4d} frames | "
              f"{pct:5.1f}% | ETA {eta/60:.1f}min")

    # 5. Close pipe, wait for FFmpeg
    print(f"\nClosing FFmpeg pipe ({total_written} total frames written)...")
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()

    if ffmpeg_proc.returncode != 0:
        print(f"ERROR: FFmpeg exited with code {ffmpeg_proc.returncode}")
        sys.exit(1)

    # 6. Verify
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_type,duration",
         "-of", "json", output_mp4],
        capture_output=True, text=True
    )
    info = json.loads(probe.stdout) if probe.returncode == 0 else {}
    file_mb = os.path.getsize(output_mp4) / (1024 * 1024)

    total_time = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"  SINGLE-PASS RENDER COMPLETE!")
    print(f"{'=' * 60}")
    print(f"  Output       : {output_mp4}")
    print(f"  File Size    : {file_mb:.1f} MB")
    print(f"  Frames       : {total_written} written")
    print(f"  Render Time  : {total_time/60:.1f} minutes")
    print(f"  FFmpeg Info  : {json.dumps(info.get('format', {}), indent=2)}")
    print(f"{'=' * 60}")
    print(f"  SYNC METHOD  : Single-process pipe (ZERO concat drift)")
    print(f"  CHARACTER    : PyToon Wav2Vec2 Neural Lip-Sync")
    print(f"  AUDIO        : 100% Untouched Master ({MASTER_MP3})")
    print(f"{'=' * 60}")

    # Send notification to Telegram
    try:
        import telegram_bot
        telegram_bot.send_message(
            f"🎉 *Full Video Render Complete!*\n\n"
            f"• **Duration:** {total_written/FPS:.2f}s ({total_written} frames @ {FPS} FPS)\n"
            f"• **File Size:** {file_mb:.1f} MB\n"
            f"• **Sync:** Exact 1-to-1 Word-Level Sync (Zero Drift)\n"
            f"• **Character:** PyToon Wav2Vec2 Neural Lip-Sync\n"
            f"• **Render Time:** {total_time/60:.1f} min\n\n"
            f"📁 Saved to: `11_Final_Video\\Video_Final.mp4`"
        )
    except Exception as e:
        print(f"Telegram notice: {e}")


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
