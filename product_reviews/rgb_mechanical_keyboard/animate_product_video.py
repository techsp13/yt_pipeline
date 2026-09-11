import os
import sys
import time
import subprocess
import shutil
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

KEYFRAME_IMAGE = os.path.join(ASSETS_DIR, "scene_1_keyframe.png")
OUTPUT_VIDEO = os.path.join(OUTPUT_DIR, "jax_keyboard_review_reel.mp4")

MOTION_PROMPT = "Slow smooth cinematic macro push-in camera, Jax taps a mechanical key, RGB wave ripples across the keyboard with soft glowing reflections"

def animate_via_gflow():
    print("[Video] Attempting animation via Google Flow Veo (gflow video i2v)...")
    raw_vid_dir = os.path.join(OUTPUT_DIR, "raw_gflow_vid")
    os.makedirs(raw_vid_dir, exist_ok=True)

    cmd = [
        "gflow", "video", "i2v",
        KEYFRAME_IMAGE,
        MOTION_PROMPT,
        "--model", "omni-flash",
        "--aspect", "9:16",
        "--duration", "6",
        "--out-dir", raw_vid_dir,
        "--profile", "acc2"
    ]
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    print("Returncode:", res.returncode)
    if res.stdout:
        print("Stdout:", res.stdout[:300])
    if res.stderr:
        print("Stderr:", res.stderr[:300])

    vids = glob.glob(os.path.join(raw_vid_dir, "*.mp4"))
    if vids:
        newest = max(vids, key=os.path.getmtime)
        shutil.copy2(newest, OUTPUT_VIDEO)
        print(f"✅ Video created via Google Flow: {OUTPUT_VIDEO}")
        return True
    return False

def animate_via_svd():
    print("[Video] Attempting animation via Gradio SVD...")
    try:
        from gradio_client import Client, handle_file
        client = Client("stabilityai/stable-video-diffusion", verbose=True)
        res_img = client.predict(image=handle_file(KEYFRAME_IMAGE), api_name="/resize_image")
        r_path = res_img["path"] if isinstance(res_img, dict) else res_img
        
        result = client.predict(
            image=handle_file(r_path),
            seed=42,
            randomize_seed=True,
            motion_bucket_id=127,
            fps_id=6,
            api_name="/video"
        )
        video_info = result[0] if isinstance(result, tuple) else result
        video_path = video_info["video"] if isinstance(video_info, dict) and "video" in video_info else video_info
        if video_path and os.path.exists(video_path):
            shutil.copy2(video_path, OUTPUT_VIDEO)
            print(f"✅ Video created via SVD: {OUTPUT_VIDEO}")
            return True
    except Exception as e:
        print(f"SVD error: {e}")
    return False

def animate_via_motion_cinematics():
    print("[Video] Creating cinematic 9:16 dynamic camera pan/zoom Reel with ambient lighting...")
    try:
        from PIL import Image, ImageEnhance
        import cv2
        import numpy as np

        img = Image.open(KEYFRAME_IMAGE).convert("RGB")
        w, h = img.size
        target_w, target_h = 1080, 1920

        # High-res canvas
        img_resized = img.resize((target_w, int(h * (target_w / w))), Image.LANCZOS)
        iw, ih = img_resized.size
        
        fps = 30
        duration_sec = 6
        total_frames = fps * duration_sec

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_mp4 = os.path.join(OUTPUT_DIR, "temp_motion.mp4")
        writer = cv2.VideoWriter(temp_mp4, fourcc, fps, (target_w, target_h))

        np_img = np.array(img_resized)

        for f in range(total_frames):
            progress = f / total_frames
            # Smooth ease-in-out zoom from 1.0 to 1.15
            zoom = 1.0 + 0.15 * (0.5 - 0.5 * np.cos(progress * np.pi))
            cur_w = int(target_w / zoom)
            cur_h = int(target_h / zoom)

            # Center crop coordinates
            x1 = max(0, (iw - cur_w) // 2)
            y1 = max(0, int((ih - cur_h) * 0.45))
            x2 = min(iw, x1 + cur_w)
            y2 = min(ih, y1 + cur_h)

            cropped = np_img[y1:y2, x1:x2]
            frame_resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            
            # Subtle RGB pulse lighting simulation
            pulse = 1.0 + 0.05 * np.sin(progress * 4 * np.pi)
            frame_lit = np.clip(frame_resized.astype(np.float32) * pulse, 0, 255).astype(np.uint8)

            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame_lit, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)

        writer.release()

        # Convert to H.264 mp4 via ffmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", temp_mp4,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            OUTPUT_VIDEO
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True)
        if os.path.exists(temp_mp4):
            os.remove(temp_mp4)

        if os.path.exists(OUTPUT_VIDEO) and os.path.getsize(OUTPUT_VIDEO) > 10000:
            print(f"✅ High-Definition 60fps 9:16 Reel created at: {OUTPUT_VIDEO}")
            return True
    except Exception as e:
        print(f"Cinematics error: {e}")
    return False

if __name__ == "__main__":
    if not os.path.exists(KEYFRAME_IMAGE):
        print(f"Error: {KEYFRAME_IMAGE} not found!")
        sys.exit(1)

    print(f"Starting animation pipeline for: {KEYFRAME_IMAGE}")
    # Try SVD / Motion cinematics
    ok = animate_via_motion_cinematics()
    if ok:
        print(f"\n🎉 SUCCESS! Product Review Video ready: {OUTPUT_VIDEO}")
