"""
generate_stickman_cap_samples.py
Renders the stickman presenter wearing a green doodle-style cap and saves the
reference images into thumbnail_stickman_assets/ (same naming convention as the
existing stickman assets there).

Usage:
    python generate_stickman_cap_samples.py
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from PIL import Image
from stickman_engine import get_animation_frames

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "thumbnail_stickman_assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Existing asset name -> engine animation
POSES = [
    ("stickman_explaining_cap.png",           "explain_two_hands"),
    ("stickman_confident_presenter_cap.png",  "confident_stance"),
    ("stickman_pointing_left_cap.png",        "point_left"),
    ("stickman_pointing_right_cap.png",       "point"),
    ("stickman_surprised_cap.png",            "surprise"),
    ("stickman_celebrating_cap.png",          "celebrate"),
]


def render_cap_pose(animation: str, cap_color: str = "green") -> Image.Image:
    """Middle frame of the animation with the cap on, cropped to content."""
    frames = get_animation_frames(animation, loops=1, cx=540, cy=1380, s=1.0,
                                  cap=True, cap_color=cap_color)
    stick = frames[len(frames) // 2] if frames else frames[0]
    bbox = stick.getbbox()
    if bbox:
        stick = stick.crop(bbox)
    return stick


def main():
    print("[CapSamples] Generating stickman + green doodle cap reference images...")
    for filename, animation in POSES:
        stick = render_cap_pose(animation)
        out = os.path.join(ASSETS_DIR, filename)
        stick.save(out)
        print(f"  ✓ {filename}  ({stick.width}x{stick.height})")
    print(f"Done → {ASSETS_DIR}")


if __name__ == "__main__":
    main()
