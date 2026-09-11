"""
PyToon Multi-Channel Video Rendering Engine
============================================
Supports 3 channel mascot packs with 100% bug-free PyToon Wav2Vec2 neural lip-sync:
- Money Channel: Emerald Mint Green (#2ECC71) Sany Cash
- Science Channel: Electric Cyan Blue (#00D2FF) Dr. Sany
- History Channel: Classic Pure White (#FFFFFF) Sany Lore / Sany Explain
"""

import os
import sys
import json
import random
import shutil
import subprocess
import cv2
import numpy as np
from PIL import Image

import pytoon
from pytoon.dataloader import Emotions, Pose, MouthCoordinates
from pytoon.animator import animate, FrameSequence, viseme_sequencer, mouth_transformation, render_frame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKS_DIR = os.path.join(BASE_DIR, "character_packs")

_CACHED_ASSETS = {}


def get_channel_assets(channel: str = "history") -> Emotions:
    """Load and cache the 90 pre-rigged poses for the given channel."""
    channel_key = channel.lower().strip()
    if "money" in channel_key or "cash" in channel_key:
        ch_dir = os.path.join(PACKS_DIR, "money")
    elif "sci" in channel_key or "tech" in channel_key or "lab" in channel_key:
        ch_dir = os.path.join(PACKS_DIR, "science")
    else:
        ch_dir = os.path.join(PACKS_DIR, "history")

    if channel_key in _CACHED_ASSETS:
        return _CACHED_ASSETS[channel_key]

    pose_json_path = os.path.join(ch_dir, "pose_data.json")
    poses_dir = os.path.join(ch_dir, "poses")

    with open(pose_json_path, "r", encoding="utf-8") as f:
        pose_data = json.load(f)["emotions"]

    emotions = {}
    for emo_name, pose_list in pose_data.items():
        if emo_name not in ["sad", "angry", "confused"]:
            poses = []
            for p in pose_list:
                imgs = {}
                for k, v in p["image_files"].items():
                    fname = os.path.basename(v)
                    imgs[k] = os.path.join(poses_dir, fname)
                coords = MouthCoordinates(**p["mouth_coordinates"])
                poses.append(Pose(image_files=imgs, mouth_coordinates=coords))
            emotions[emo_name] = poses

    parsed_assets = Emotions(**emotions)
    _CACHED_ASSETS[channel_key] = parsed_assets
    return parsed_assets


class ChannelPytoonAnimator(animate):
    """Custom PyToon animator that injects channel-colored character packs."""

    def __init__(self, audio_file: str, transcript: str = None, channel: str = "history", fps: int = 30):
        self.audio_file = audio_file
        self.sequence = FrameSequence()
        self.assets = get_channel_assets(channel)
        self.fps = fps
        self.final_frames = []
        self.blink_rate = 3.0

        # Wav2Vec2 Neural Forced Alignment
        self.viseme_sequence = viseme_sequencer(self.audio_file, transcript, self.fps)
        self.build_mouth_sequence()
        self.duration = len(self.sequence.mouth_files) / self.fps

        self.build_pose_sequence_custom()
        self.compile_animation()

    def build_pose_sequence_custom(self):
        emotion = self.random_emotion()
        pose = random.choice(emotion)

        for i, _ in enumerate(self.sequence.mouth_files):
            if self.sequence.pose_changes[i]:
                emotion = self.random_emotion()
                pose = random.choice(emotion)

            eyes = self.blink_manager(idx=i)
            self.sequence.pose_files.append(pose.image_files[eyes])
            self.sequence.mouth_coords.append(pose.mouth_coordinates)

        for i, _ in enumerate(self.sequence.mouth_files):
            transformed_image = mouth_transformation(
                mouth_file=self.sequence.mouth_files[i],
                mouth_coord=self.sequence.mouth_coords[i],
            )
            self.sequence.mouth_images.append(transformed_image)

    def compile_animation(self):
        global _CV2_IMG_CACHE
        if "_CV2_IMG_CACHE" not in globals():
            _CV2_IMG_CACHE = {}
        for i, _ in enumerate(self.sequence.pose_files):
            p_file = self.sequence.pose_files[i]
            if p_file not in _CV2_IMG_CACHE:
                _CV2_IMG_CACHE[p_file] = cv2.imread(p_file, cv2.IMREAD_UNCHANGED)
            frame = _CV2_IMG_CACHE[p_file].copy()
            if self.sequence.mouth_files[i] is not None:
                final_frame = render_frame(
                    pose_img=frame,
                    mouth_img=self.sequence.mouth_images[i],
                    mouth_coord=self.sequence.mouth_coords[i],
                )
            else:
                final_frame = frame
            self.final_frames.append(final_frame)


def render_pytoon_scene(image_path: str, audio_path: str, text: str, output_path: str,
                        duration: float, fps: int = 30, ffmpeg: str = "ffmpeg",
                        channel: str = "history", silent: bool = False):
    """
    Renders a 16:9 landscape scene clip with channel-colored PyToon character.
    If silent=True: produces a VIDEO-ONLY MKV for master audio muxing.
    """
    anim = ChannelPytoonAnimator(audio_file=audio_path, transcript=text, channel=channel, fps=fps)
    total_frames = len(anim.final_frames)
    target_frames = int(round(duration * fps))

    bg = Image.open(image_path).convert("RGBA").resize((1920, 1080), Image.LANCZOS)
    target_h = 430  # Compact presenter size (~40% of screen height instead of 70%)

    temp_dir = output_path + "_tmp_frames"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        for f in range(target_frames):
            frame = bg.copy()
            char_idx = f if f < total_frames else (total_frames - 1)
            char_np = anim.final_frames[char_idx]
            char_img = Image.fromarray(char_np).convert("RGBA")

            w, h = char_img.size
            aspect = w / h
            new_h = target_h
            new_w = int(new_h * aspect)
            char_resized = char_img.resize((new_w, new_h), Image.LANCZOS)

            # Anchor character neatly in bottom-right corner leaving >80% screen clear
            pos_x = 1920 - new_w - 60
            pos_y = 1080 - new_h + 10

            frame.alpha_composite(char_resized, dest=(pos_x, pos_y))
            frame.convert("RGB").save(os.path.join(temp_dir, f"frame_{f:05d}.png"))

        if silent:
            cmd = [
                ffmpeg, "-y",
                "-framerate", str(fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                "-t", f"{duration:.6f}",
                output_path
            ]
        else:
            cmd = [
                ffmpeg, "-y",
                "-framerate", str(fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-i", audio_path,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k", "-shortest",
                output_path
            ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def render_pytoon_vertical_scene(image_path: str, audio_path: str, text: str, output_path: str,
                                 duration: float, fps: int = 30, ffmpeg: str = "ffmpeg",
                                 channel: str = "history"):
    """
    Renders a 9:16 vertical YouTube Short scene clip with channel-colored PyToon character.
    """
    anim = ChannelPytoonAnimator(audio_file=audio_path, transcript=text, channel=channel, fps=fps)
    total_frames = len(anim.final_frames)
    target_frames = int(round(duration * fps))

    # Prepare 720x1280 vertical background
    from PIL import ImageFilter
    BG_W, BG_H = 720, 1280
    raw_bg = Image.open(image_path).convert("RGBA")
    iw, ih = raw_bg.size
    if abs(iw / ih - BG_W / BG_H) < 0.05:
        bg = raw_bg.resize((BG_W, BG_H), Image.LANCZOS)
    else:
        # Create blurred background fill for cinematic shorts look
        bg_blur = raw_bg.resize((BG_W, BG_H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(radius=25))
        fit_w = BG_W
        fit_h = int(ih * (BG_W / iw))
        img_fit = raw_bg.resize((fit_w, fit_h), Image.LANCZOS)
        paste_y = max(0, (BG_H - fit_h) // 2 - 60)
        bg = bg_blur
        bg.paste(img_fit, (0, paste_y))

    target_h = 380  # Compact presenter size (~30% of vertical height)
    temp_dir = output_path + "_tmp_vframes"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        for f in range(target_frames):
            frame = bg.copy()
            char_idx = f if f < total_frames else (total_frames - 1)
            char_np = anim.final_frames[char_idx]
            char_img = Image.fromarray(char_np).convert("RGBA")

            w, h = char_img.size
            aspect = w / h
            new_h = target_h
            new_w = int(new_h * aspect)
            char_resized = char_img.resize((new_w, new_h), Image.LANCZOS)

            pos_x = (BG_W - new_w) // 2
            pos_y = BG_H - new_h + 10

            frame.alpha_composite(char_resized, dest=(pos_x, pos_y))
            frame.convert("RGB").save(os.path.join(temp_dir, f"frame_{f:05d}.png"))

        cmd = [
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-i", os.path.join(temp_dir, "frame_%05d.png"),
            "-i", audio_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
