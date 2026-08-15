import os
import sys
import json
import re

import youtube_agent
import gflow_assistant

scenes = youtube_agent.parse_scenes_from_file()
gap_nums = ["20", "21", "22", "25", "26", "27", "28", "38"]
gap_scenes = [s for s in scenes if f"{s['number']:02d}" in gap_nums]

cfg = youtube_agent.get_channel_config()
style_suffix = cfg["widescreen_suffix"]
BG_COLORS = ["baby blue", "lemon yellow", "soft purple", "mint green", "soft orange", "vibrant teal"]

print("--- GAP SCENE PROMPTS ---")
for s in gap_scenes[:5]:
    num = f"{s['number']:02d}"
    scene_bg_color = BG_COLORS[s['number'] % len(BG_COLORS)]
    hair_lock = "Main character: curly black afro hair, pure white face (#FFFFFF), smooth head, black eyes, thin eyebrows, black hoodie with white atom symbol. "
    bg_lock = f"Background: solid vibrant {scene_bg_color} top half, light tan bottom half. "
    full_prompt = hair_lock + bg_lock + s['image_prompt'] + style_suffix
    clean_p = gflow_assistant.sanitize_prompt_for_safety(full_prompt)
    print(f"=== SCENE V{num} ===")
    print(clean_p)
    print()
