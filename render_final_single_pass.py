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
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

sys.path.insert(0, r"D:\youtube_automation_agent")
from pytoon_renderer import ChannelPytoonAnimator

FPS = 25
BG_W, BG_H = 1920, 1080
CHAR_H = 430  # Compact presenter size matching pytoon_renderer.py

# Subtitle typography setup (Bold high-contrast modern font)
SUBTITLE_FONT = None
for fp in ['C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/tahoma.ttf']:
    if os.path.exists(fp):
        try:
            SUBTITLE_FONT = ImageFont.truetype(fp, 42)
            break
        except Exception:
            pass
if SUBTITLE_FONT is None:
    SUBTITLE_FONT = ImageFont.load_default()

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


def pre_render_kinetic_subtitles(text, target_frames, font, W=1920, H=1080):
    """Pre-computes kinetic word-highlighted subtitle overlays for the scene."""
    words = [w for w in text.split() if w.strip()]
    if not words or font is None:
        return []
    
    sub_h = 130
    sub_y1 = H - 150
    sub_y2 = sub_y1 + sub_h
    space_w = font.getbbox(' ')[2] - font.getbbox(' ')[0]
    
    MAX_WORDS_PER_SCREEN = 6
    chunks = []
    for i in range(0, len(words), MAX_WORDS_PER_SCREEN):
        chunks.append(words[i:i + MAX_WORDS_PER_SCREEN])
    
    word_states = []
    for chunk in chunks:
        w_widths = [font.getbbox(w)[2] - font.getbbox(w)[0] for w in chunk]
        tot_w = sum(w_widths) + space_w * (len(chunk) - 1)
        sx = max(60, (W - tot_w) // 2)
        
        for local_idx in range(len(chunk)):
            img = Image.new('RGBA', (W, sub_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            cx = sx
            for j, (w, ww) in enumerate(zip(chunk, w_widths)):
                # Active word glows in bright gold/yellow, inactive words in clean white
                color = (255, 230, 0, 255) if j == local_idx else (255, 255, 255, 255)
                draw.text((cx, sub_h // 2), w, font=font, fill=color, stroke_width=4, stroke_fill=(0, 0, 0, 255), anchor='lm')
                cx += ww + space_w
            arr = np.array(img, dtype=np.float32)
            alpha = arr[:, :, 3:4] / 255.0
            rgb = arr[:, :, :3] * alpha
            inv_alpha = 1.0 - alpha
            word_states.append((rgb, inv_alpha, sub_y1, sub_y2))
            
    return word_states


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
def should_show_presenter(sn: int, total_scenes: int, narr: str) -> bool:
    """
    Professional Video Editor Presenter Cadence (15-25% strategic screen time):
    1. Hook (Scenes 1-5): Presenter is on-screen making direct eye contact with the viewer.
    2. Act Transitions (Every ~40 scenes for 2 scenes): Re-anchors the viewer to the new chapter.
    3. Outro (Last 6 scenes): Delivers the final philosophical conclusion.
    4. Conversational Prompts: Direct 2nd-person calls to viewer ('think about', 'look at', 'consider').
    5. Main Immersion Scenes: Presenter is hidden to give 100% full-screen cinematic focus to the artwork.
    """
    if os.environ.get("FORCE_ALL_PRESENTER", "0") == "1":
        return True
    if sn <= 5:
        return True
    if sn >= total_scenes - 5:
        return True
    if sn % 40 in [0, 1]:
        return True
    lower = narr.lower()
    conversational_triggers = [
        "think about how you feel", "look at our modern", "consider the sheer",
        "where is the tribe", "we look at those", "look at your", "be honest"
    ]
    if any(k in lower for k in conversational_triggers):
        return True
    return False


def main():
    total_dur = get_wav_duration(MASTER_WAV)
    total_frames = int(round(total_dur * FPS))

    cfg_p = os.path.join(PROJ_DIR, "Project_Config.json")
    ch_name = "money"
    if os.path.exists(cfg_p):
        with open(cfg_p, "r", encoding="utf-8") as cf:
            ch_name = json.load(cf).get("channel", "money")

    # Pre-Render Sync Lock & Asset Gatekeeper
    from av_sync_guardian import pre_render_sync_check, post_render_sync_audit
    sync_check = pre_render_sync_check(PROJ_DIR)
    if not sync_check["passed"]:
        print(f"❌ [CRITICAL SYNC ERROR] {sync_check.get('error')}. Aborting render.")
        sys.exit(1)

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

    # 3. Check for clean mixed audio (BGM ducked under voice, ZERO SFX)
    mixed_audio_p = os.path.join(PROJ_DIR, "08_Background_Music", "Final_Mixed_Audio.mp3")
    if not os.path.exists(mixed_audio_p) or os.path.getsize(mixed_audio_p) < 1000:
        print("\n[Audio] Generating clean voiceover + ducked BGM mix (ZERO SFX)...")
        try:
            from audio_mixer_engine import mix_master_audio
            mix_master_audio(PROJ_DIR, ch_name, include_sfx=False)
        except Exception as e:
            print(f"  [WARN] Audio mixing failed ({e}), using raw voice")
    
    audio_to_mux = mixed_audio_p if (os.path.exists(mixed_audio_p) and os.path.getsize(mixed_audio_p) > 1000) else MASTER_MP3
    print(f"\n[Step 2/{3}] Selected Audio Track: {audio_to_mux}")

    output_mp4 = os.path.join(FINAL_DIR, "Video_Final.mp4")
    print(f"  Output MP4: {output_mp4}")

    cmd = [
        "ffmpeg", "-y",
        # Video input: raw RGB frames from stdin
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{BG_W}x{BG_H}", "-r", str(FPS),
        "-i", "pipe:0",
        # Audio input: clean master audio with ducked BGM (ZERO SFX)
        "-i", audio_to_mux,
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
    print(f"\n[Step 3/{3}] Rendering {N} scenes with Ken Burns Motion, PyToon & Kinetic Subtitles...")
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

        # Load background and clean any Gemini/Google Flow watermark before sizing & rendering
        from watermark_remover import remove_gemini_watermark
        raw_bg_pil = Image.open(img_p).convert("RGB")
        clean_bg_pil = remove_gemini_watermark(raw_bg_pil)

        # Dynamic Ken Burns Camera Motion Setup
        # Pre-resize background slightly larger (1.025x) for subtle, slow, cinematic breathing float
        SCALE_FACTOR = 1.025
        BIG_W = int(round(BG_W * SCALE_FACTOR))
        BIG_H = int(round(BG_H * SCALE_FACTOR))
        big_bg = clean_bg_pil.resize((BIG_W, BIG_H), Image.BILINEAR)
        big_arr = np.array(big_bg, dtype=np.uint8)
        max_dx = BIG_W - BG_W
        max_dy = BIG_H - BG_H

        # Alternating motion modes across scenes:
        # 0: Push-In (Slow Subtle Zoom-In)
        # 1: Push-Out (Slow Subtle Zoom-Out)
        # 2: Pan Left-to-Right (Slow Glide)
        # 3: Pan Right-to-Left (Slow Glide)
        motion_mode = i % 4

        # Pre-render kinetic word-highlighted subtitles for this scene
        pre_rendered_subs = pre_render_kinetic_subtitles(narr, target_frames, SUBTITLE_FONT, BG_W, BG_H)
        n_subs = len(pre_rendered_subs)

        # Professional Video Editor Pacing: Selective presenter appearance (~15-25% screen time)
        show_presenter = should_show_presenter(sn, N, narr)
        char_frames = []
        if show_presenter:
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

        # High-speed frame rendering and piping
        n_pr = len(pre_rendered_chars)
        for fi in range(target_frames):
            t_raw = fi / max(1, target_frames - 1)
            # Smooth cosine easing: starts gently, glides subtly, slows gently (no abrupt jerks)
            t = 0.5 * (1.0 - np.cos(np.pi * t_raw))

            # 1. Ken Burns camera motion crop (subtle, slow cinematic motion)
            if motion_mode == 0:  # Push-In (Slow Zoom In)
                cw = int(BIG_W - t * max_dx)
                ch = int(BIG_H - t * max_dy)
                x0 = max(0, min(BIG_W - cw, (BIG_W - cw) // 2))
                y0 = max(0, min(BIG_H - ch, (BIG_H - ch) // 2))
                frame = cv2.resize(big_arr[y0:y0+ch, x0:x0+cw], (BG_W, BG_H), interpolation=cv2.INTER_LINEAR)
            elif motion_mode == 1:  # Push-Out (Slow Zoom Out)
                cw = int(BG_W + t * max_dx)
                ch = int(BG_H + t * max_dy)
                x0 = max(0, min(BIG_W - cw, (BIG_W - cw) // 2))
                y0 = max(0, min(BIG_H - ch, (BIG_H - ch) // 2))
                frame = cv2.resize(big_arr[y0:y0+ch, x0:x0+cw], (BG_W, BG_H), interpolation=cv2.INTER_LINEAR)
            elif motion_mode == 2:  # Pan Left-to-Right
                x0 = max(0, min(BIG_W - BG_W, int(t * max_dx)))
                y0 = max_dy // 2
                frame = big_arr[y0:y0+BG_H, x0:x0+BG_W].copy()
            else:  # Pan Right-to-Left
                x0 = max(0, min(BIG_W - BG_W, int((1.0 - t) * max_dx)))
                y0 = max_dy // 2
                frame = big_arr[y0:y0+BG_H, x0:x0+BG_W].copy()

            # 2. PyToon presenter character alpha blending
            if pre_rendered_chars:
                c_rgb, c_inv_alpha = pre_rendered_chars[min(fi, n_pr - 1)]
                patch = frame[y1:y2, x1:x2].astype(np.float32)
                frame[y1:y2, x1:x2] = (c_rgb + patch * c_inv_alpha).astype(np.uint8)

            # 3. Kinetic Word-Highlighted Subtitle overlay
            if n_subs > 0:
                s_idx = min(n_subs - 1, int(fi / target_frames * n_subs))
                s_rgb, s_inv_alpha, sy1, sy2 = pre_rendered_subs[s_idx]
                sub_patch = frame[sy1:sy2, :].astype(np.float32)
                frame[sy1:sy2, :] = (s_rgb + sub_patch * s_inv_alpha).astype(np.uint8)

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
    print(f"  MOTION       : Slow, subtle cinematic Ken Burns (2.5% cosine float)")
    print(f"  CHARACTER    : PyToon Wav2Vec2 Neural Lip-Sync")
    print(f"  AUDIO        : Clean Master Voice + Ducked BGM (ZERO SFX)")
    print(f"{'=' * 60}")

    # 7. Certified A/V Synchronization Audit
    log_dir = os.path.join(PROJ_DIR, "13_Logs")
    sync_audit = post_render_sync_audit(output_mp4, MASTER_WAV, log_dir)

    # Send notification to Telegram
    try:
        import telegram_bot
        telegram_bot.send_message(
            f"🎉 *Full Video Render Complete!*\n\n"
            f"• **Duration:** {total_written/FPS:.2f}s ({total_written} frames @ {FPS} FPS)\n"
            f"• **File Size:** {file_mb:.1f} MB\n"
            f"• **Sync Certification:** ✅ {sync_audit['sync_verdict']} ({sync_audit['stream_drift_ms']} ms drift)\n"
            f"• **Motion:** Slow, subtle cinematic Ken Burns (2.5% cosine float)\n"
            f"• **Audio:** Clean Voiceover + Ducked BGM (ZERO Sound Effects)\n"
            f"• **Character:** PyToon Wav2Vec2 Neural Lip-Sync ({'15-20% Dynamic Screen Time' if os.environ.get('FORCE_ALL_PRESENTER') != '1' else '100% Constant'})\n"
            f"• **Render Time:** {total_time/60:.1f} min\n\n"
            f"📁 Saved to: `11_Final_Video\\Video_Final.mp4`"
        )
    except Exception as e:
        print(f"Telegram notice: {e}")


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    main()
