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

PROFILE = "acc2"

PRODUCT_NAME = "Retro RGB Mechanical Keyboard"
CHARACTER_NAME = "Jax (Mini Desk Reviewer)"

IMAGE_PROMPT = (
    "Cinematic 9:16 vertical macro shot of Jax, a stylish 6-inch miniature modern character wearing a sleek black hoodie and mini headphones, "
    "standing on top of a retro RGB mechanical keyboard with glowing illuminated keys on a clean wooden desk, "
    "curious confident expression, looking down at the keyboard keys, shallow depth of field, warm ambient lighting, 8k resolution, photorealistic"
)

MOTION_PROMPT = (
    "Slow smooth cinematic macro camera push-in, Jax gently taps a key on the mechanical keyboard, "
    "a rainbow RGB wave ripple lights up across the keys, soft realistic lighting reflections, ultra high quality"
)

def step1_generate_keyframe():
    print("=" * 60)
    print("STEP 1: Generating 9:16 Product Keyframe via gflow Imagen/Nano...")
    print(f"Prompt: {IMAGE_PROMPT}")
    print("=" * 60)

    raw_img_dir = os.path.join(ASSETS_DIR, "raw_img")
    os.makedirs(raw_img_dir, exist_ok=True)

    cmd = [
        "gflow", "image", "t2i",
        IMAGE_PROMPT,
        "--model", "nano-pro",
        "--aspect", "9:16",
        "--out", raw_img_dir,
        "--profile", PROFILE
    ]

    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.time() - t0

    print(f"gflow image exited with code {res.returncode} in {dur:.1f}s")
    if res.stdout:
        print("Output:", res.stdout[:300])
    if res.stderr:
        print("Errors/Warnings:", res.stderr[:300])

    images = glob.glob(os.path.join(raw_img_dir, "*.png")) + glob.glob(os.path.join(raw_img_dir, "*.jpg"))
    if not images:
        print("[Retry] Retrying with model nano2...")
        cmd[4] = "nano2"
        res = subprocess.run(cmd, capture_output=True, text=True)
        images = glob.glob(os.path.join(raw_img_dir, "*.png")) + glob.glob(os.path.join(raw_img_dir, "*.jpg"))

    if images:
        latest_img = max(images, key=os.path.getmtime)
        target_img = os.path.join(ASSETS_DIR, "scene_1_keyframe.png")
        shutil.copy2(latest_img, target_img)
        print(f"[SUCCESS] Keyframe saved to: {target_img}")
        return target_img
    else:
        print("[ERROR] No image generated!")
        return None

def step2_generate_video(image_path):
    print("=" * 60)
    print("STEP 2: Animating Keyframe to Video via gflow Veo (i2v)...")
    print(f"Input Image: {image_path}")
    print(f"Motion Prompt: {MOTION_PROMPT}")
    print("=" * 60)

    raw_vid_dir = os.path.join(OUTPUT_DIR, "raw_vid")
    os.makedirs(raw_vid_dir, exist_ok=True)

    out_video = os.path.join(OUTPUT_DIR, "sample_review_reel.mp4")

    cmd = [
        "gflow", "video", "i2v",
        image_path,
        MOTION_PROMPT,
        "--model", "omni-flash",
        "--aspect", "9:16",
        "--duration", "6",
        "--out-dir", raw_vid_dir,
        "--profile", PROFILE
    ]

    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    dur = time.time() - t0

    print(f"gflow video exited with code {res.returncode} in {dur:.1f}s")
    if res.stdout:
        print("Output:", res.stdout[:300])
    if res.stderr:
        print("Errors/Warnings:", res.stderr[:300])

    videos = glob.glob(os.path.join(raw_vid_dir, "*.mp4"))
    if not videos:
        print("[Retry] Retrying with model veo-lite...")
        cmd_lite = [
            "gflow", "video", "i2v",
            image_path,
            MOTION_PROMPT,
            "--model", "veo-lite",
            "--aspect", "9:16",
            "--out-dir", raw_vid_dir,
            "--profile", PROFILE
        ]
        res = subprocess.run(cmd_lite, capture_output=True, text=True)
        videos = glob.glob(os.path.join(raw_vid_dir, "*.mp4"))

    if videos:
        latest_vid = max(videos, key=os.path.getmtime)
        shutil.copy2(latest_vid, out_video)
        print(f"[SUCCESS] Video created successfully at: {out_video}")
        return out_video
    else:
        print("[ERROR] No video was output.")
        return None

if __name__ == "__main__":
    keyframe = step1_generate_keyframe()
    if keyframe:
        video = step2_generate_video(keyframe)
        if video:
            print("\n" + "=" * 60)
            print(f"🎉 PIPELINE COMPLETE! Sample Video: {video}")
            print("=" * 60)
