"""
thumbnail_generator.py
======================
100% Native All-in-One Google Imagen 3 (gflow) YouTube Thumbnail Engine.
Generates:
1. Big bold hand-drawn 2D cartoon doodle yellow font with thick black marker outlines.
2. Channel-colored Speaking Mascot on the right with expressive high-CTR reaction.
3. Rich 2D webcomic/doodle background scene.
"""

import os
import sys
import json
from gflow_assistant import generate_imagen_image
try:
    from playwright_flow_generator import generate_image_playwright
except ImportError:
    generate_image_playwright = None

MASCOT_CHANNEL_PROMPTS = {
    "money": {
        "head_desc": "an expressive cute stickman mascot character with a smooth solid golden yellow round head (#F4C430), thick black marker outline, black dot eyes, wearing a black business suit and tie, with a shocked mind-blown reaction and black stick limbs",
        "theme_desc": "An open massive bank vault overflowing with glowing gold bullion bars and stacks of cash under warm vibrant lighting"
    },
    "science": {
        "head_desc": "an expressive cute stickman mascot character with a smooth solid pure white round head (#FFFFFF), thick black marker outline, black dot eyes, wearing white scientist lab goggles and white lab coat, pointing excitedly with black stick limbs",
        "theme_desc": "A colossal glowing cosmic mystery with electric cyan energy accretion disk warping space and stars"
    },
    "history": {
        "head_desc": "an expressive cute stickman mascot character with a smooth solid tan-brown round head (#C89B78), thick black marker outline, black dot eyes, small neat mustache and chin goatee, wearing dynamic minimalist era-appropriate clothing matching the historical story (e.g. prehistoric animal fur wrap for stone age/caveman, linen kilt for ancient Egypt, classical tunic for antiquity, medieval clothing for middle ages), wide shocked eyes and open mouth, hands on cheeks in extreme shock, and black stick limbs",
        "theme_desc": "An epic ancient historical setting with mysterious glowing celestial artifacts, radiant relics, volumetric god rays, and dramatic environment"
    }
}


import re

def sanitize_thumbnail_text(text: str) -> str:
    """
    Cleans thumbnail text to guarantee:
    - Zero markdown asterisks (** or *)
    - Zero special symbols (#, @, $, %, ^, &, *, ~, `, _, +, =, /, \\, |, <, >, (, ), [, ], {, }, ", ', etc.)
    - Zero prompt/label prefixes like 'Thumbnail Title:', 'Hook:', 'Text:'
    - Preserves clean uppercase alphanumeric text with YouTube clickbait punctuation (? and !)
    """
    if not text:
        return "SECRETS REVEALED!"
    
    # 1. Strip common label prefixes like "Thumbnail Title:", "Text:", "Hook:", etc.
    cleaned = re.sub(
        r'^(?:[*_\s]*thumbnail\s*(?:title|text|concept|prompt|hook)?[:\s*_-]*|[*_\s]*hook[:\s*_-]*|[*_\s]*text[:\s*_-]*)',
        '',
        str(text),
        flags=re.IGNORECASE
    )
    
    # 2. Strip quotes and apostrophes without adding spaces (e.g. DON'T -> DONT)
    cleaned = re.sub(r'["\'“”‘’`«»]', '', cleaned)
    
    # 3. Strip all markdown asterisks, underlines, tildes
    cleaned = cleaned.replace('*', ' ').replace('_', ' ').replace('~', ' ')
    
    # 4. Remove ALL special symbols, keeping ONLY letters, digits, spaces, ?, and !
    cleaned = re.sub(r'[^a-zA-Z0-9\s?!]', ' ', cleaned)
    
    # 5. Clean up excessive punctuation and collapse whitespace
    cleaned = re.sub(r'[?!]{3,}', '?!', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()
    
    # 6. Fallback if empty
    if not cleaned or not any(c.isalnum() for c in cleaned):
        cleaned = "SECRETS REVEALED!"
        
    return cleaned

def sanitize_prompt_text(text: str) -> str:
    """Cleans background prompt string of stray markdown asterisks and label prefixes."""
    if not text:
        return ""
    cleaned = re.sub(r'^(?:[*_\s]*thumbnail\s*(?:concept|prompt|title)?[:\s*_-]*)', '', str(text), flags=re.IGNORECASE)
    cleaned = cleaned.replace('**', '').replace('__', '').replace('*', '').strip()
    return cleaned


def generate_thumbnail(prompt: str, text_overlay: str, output_path: str,
                       pose_name: str = "4.png", channel: str = "history",
                       custom_mascot_desc: str = None):
    """
    Generates a 100% native all-in-one 16:9 YouTube thumbnail via Google Imagen 3 (gflow)
    with native Doodle Yellow typography, channel mascot, and scene background.
    Guarantees text_overlay contains NO markdown asterisks (**) or special symbols.
    """
    ch_key = channel.lower().strip()
    if "money" in ch_key or "cash" in ch_key:
        cfg = MASCOT_CHANNEL_PROMPTS["money"]
    elif "sci" in ch_key or "tech" in ch_key or "lab" in ch_key:
        cfg = MASCOT_CHANNEL_PROMPTS["science"]
    else:
        cfg = MASCOT_CHANNEL_PROMPTS["history"]

    clean_text = sanitize_thumbnail_text(text_overlay)
    raw_subject = prompt.strip() if prompt else cfg["theme_desc"]
    scene_subject = sanitize_prompt_text(raw_subject)
    mascot_desc = custom_mascot_desc.strip() if custom_mascot_desc else cfg['head_desc']

    # Construct the master 100% native GFlow prompt
    full_prompt = (
        f"A viral YouTube thumbnail in clean 2D webcomic cartoon doodle art style. "
        f"TEXT: Big bold hand-drawn 2D cartoon doodle bubble lettering across the top that reads '{clean_text}' in 100% solid bright saturated golden yellow (#FFCC00) with thick heavy black ink marker outlines around every letter. Perfectly sharp, readable, high-contrast YouTube thumbnail typography. "
        f"MASCOT: On the right side, {mascot_desc}. "
        f"BACKGROUND: {scene_subject}. "
        f"STYLE: 2D hand-drawn webcomic cartoon doodle illustration, crisp bold ink outlines, vibrant saturated colors, 16:9 widescreen YouTube thumbnail format, high CTR composition."
    )

    print(f"[Thumbnail] Generating 100% Native GFlow Thumbnail with Doodle Yellow Font: '{clean_text}'...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ok = False
    if generate_image_playwright:
        ok = generate_image_playwright(full_prompt, output_path, aspect_ratio="16:9")
    if not ok:
        ok = generate_imagen_image(full_prompt, output_path, aspect_ratio="16:9")

    if ok and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        print(f"[Thumbnail] Successfully generated master thumbnail: {output_path}")
        return True
    else:
        print(f"[Thumbnail Error] Native generation failed for {output_path}")
        return False
