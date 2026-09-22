"""
thumbnail_generator.py
======================
100% Native All-in-One Google Imagen 3 (gflow) YouTube Thumbnail Engine.
Always generates 5 distinct high-CTR thumbnail options for YouTube A/B testing:
1. Big bold hand-drawn 2D cartoon doodle yellow font with thick black marker outlines.
2. Channel-colored Speaking Mascot on the right with expressive high-CTR reaction poses.
3. Rich 2D webcomic/doodle background scene.
"""

import os
import sys
import json
import shutil
import re
from gflow_assistant import generate_imagen_image
try:
    from playwright_flow_generator import generate_image_playwright
except ImportError:
    generate_image_playwright = None

MASCOT_CHANNEL_PROMPTS = {
    "money": {
        "head_desc": "an expressive cute stickman mascot character with a smooth solid golden yellow round head (#F4C430), thick black marker outline, black dot eyes, wearing a black business suit and tie, with black stick limbs",
        "theme_desc": "An open massive bank vault overflowing with glowing gold bullion bars and stacks of cash under warm vibrant lighting"
    },
    "science": {
        "head_desc": "an expressive cute stickman mascot character with a smooth solid pure white round head (#FFFFFF), thick black marker outline, black dot eyes, wearing white scientist lab goggles and white lab coat, pointing excitedly with black stick limbs",
        "theme_desc": "A colossal glowing cosmic mystery with electric cyan energy accretion disk warping space and stars"
    },
    "history": {
        "head_desc": "an expressive cute stickman mascot character with a smooth solid tan-brown round head (#C89B78), thick black marker outline, black dot eyes, small neat mustache and chin goatee, wearing dynamic minimalist era-appropriate clothing matching the historical story, and black stick limbs",
        "theme_desc": "An epic ancient historical setting with mysterious glowing celestial artifacts, radiant relics, volumetric god rays, and dramatic environment"
    }
}

MASCOT_POSES = {
    "mind_blown": "hands on cheeks in extreme mind-blown shock, wide open mouth in awe and disbelief",
    "pointing_right": "energetically pointing both stick hands toward the central subject with a wide excited smile",
    "explaining": "holding a clipboard and gesturing with one hand in an authoritative scientist pose",
    "shocked": "jumping back in comic alarm with wide eyes and open mouth",
    "curious": "hand on chin with a tilted head and curious, intrigued expression",
}


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
                       pose_name: str = "mind_blown", channel: str = "history",
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

    pose_key = str(pose_name).lower().replace(".png", "").strip()
    if pose_key in MASCOT_POSES:
        pose_action = MASCOT_POSES[pose_key]
        mascot_desc = f"{mascot_desc}, {pose_action}"

    # Construct the master 100% native GFlow prompt
    full_prompt = (
        f"A viral YouTube thumbnail in clean 2D webcomic cartoon doodle art style. "
        f"TEXT: Big bold hand-drawn 2D cartoon doodle bubble lettering across the top that reads '{clean_text}' in 100% solid bright saturated golden yellow (#FFCC00) with thick heavy black ink marker outlines around every letter. Perfectly sharp, readable, high-contrast YouTube thumbnail typography. "
        f"MASCOT: On the right side, {mascot_desc}. "
        f"BACKGROUND: {scene_subject}. Clean atmospheric background, strictly NO math equations, NO numbers, NO chemical formulas, NO chalkboard equations, NO floating symbols, NO background text. "
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


def generate_5_thumbnails(
    proj_dir: str,
    topic: str = "",
    title: str = "",
    channel: str = "science",
    custom_concept: str = None,
    custom_hook: str = None,
    force_regen: bool = False
) -> list:
    """
    Generates 5 distinct high-CTR YouTube thumbnail options for YouTube A/B testing:
    - 5 unique viral hook texts
    - 5 unique visual scenes/focal subjects
    - 5 unique mascot reaction poses
    Saves as:
      - 12_Thumbnail/Thumbnail_1.png ... Thumbnail_5.png
      - 12_Thumbnail/Thumbnail.png (Option 1 default)
      - Project root Thumbnail.png
    """
    thumb_dir = os.path.join(proj_dir, "12_Thumbnail")
    os.makedirs(thumb_dir, exist_ok=True)
    master_thumb = os.path.join(thumb_dir, "Thumbnail.png")
    root_thumb = os.path.join(proj_dir, "Thumbnail.png")
    
    # 1. Gather context from SEO Titles and Scenes
    titles_file = os.path.join(proj_dir, "02_SEO", "Titles.md")
    scenes_file = os.path.join(proj_dir, "04_Scenes", "Scene_List.json")
    
    suggested_titles = []
    if os.path.exists(titles_file):
        try:
            with open(titles_file, "r", encoding="utf-8") as f:
                c = f.read()
            for line in c.splitlines():
                m = re.match(r"^\s*\d+\.\s*(.+)", line.strip())
                if m:
                    suggested_titles.append(m.group(1).strip())
        except Exception:
            pass
            
    scene_prompts = []
    if os.path.exists(scenes_file):
        try:
            with open(scenes_file, "r", encoding="utf-8") as f:
                sc_list = json.load(f)
            for sc in sc_list:
                p = sc.get("image_prompt", "")
                if p and len(p) > 20:
                    scene_prompts.append(p)
        except Exception:
            pass

    # 2. Build 5 distinct concepts & hook texts
    options_cfg = []
    is_mosquito = "mosquito" in (topic + title).lower()
    is_money = any(w in (topic + title).lower() for w in ["money", "rich", "wealth", "bank"])
    is_space = any(w in (topic + title).lower() for w in ["space", "black hole", "telescope", "star"])

    # Option 1: Primary custom hook or default
    hook_1 = custom_hook if custom_hook else ("WHY YOU?" if is_mosquito else "THE SECRET!")
    concept_1 = custom_concept if custom_concept else (f"The main central subject representing {topic or title}")
    options_cfg.append({
        "id": 1,
        "hook": sanitize_thumbnail_text(hook_1),
        "prompt": concept_1,
        "pose": "mind_blown",
        "title": title or "Master Concept"
    })
    
    # Option 2: Scientific / Sensory Mechanism
    hook_2 = "THE SMELL?!" if is_mosquito else ("THE SECRET!" if is_money else "HOW IT WORKS!")
    concept_2 = (
        "Thermal infrared heat-vision scan showing human skin glowing red and releasing microscopic chemical plumes "
        "and drifting gas bubbles into the air toward curious cartoon mosquitoes with magnifying lens"
        if is_mosquito else
        (scene_prompts[min(20, len(scene_prompts)-1)][:160] if scene_prompts else f"A dramatic high-tech visual breakdown of {topic}")
    )
    options_cfg.append({
        "id": 2,
        "hook": sanitize_thumbnail_text(hook_2),
        "prompt": concept_2,
        "pose": "pointing_right",
        "title": suggested_titles[0] if len(suggested_titles) > 0 else "Sensory Mechanism"
    })
    
    # Option 3: Deep Laboratory / Scientific Revelation (DNA / Evidence)
    hook_3 = "YOUR BLOOD?!" if is_mosquito else ("WHERE IT GOES!" if is_money else "FROM SPACE?!")
    concept_3 = (
        "A brightly lit genetics research laboratory with test tubes filled with glowing neon red liquid, "
        "a large easel whiteboard with DNA double helix diagram and chemical formulas, and an inquisitive mosquito"
        if is_mosquito else
        (scene_prompts[min(70, len(scene_prompts)-1)][:160] if scene_prompts else f"Inside the laboratory proving the secret of {topic}")
    )
    options_cfg.append({
        "id": 3,
        "hook": sanitize_thumbnail_text(hook_3),
        "prompt": concept_3,
        "pose": "explaining",
        "title": suggested_titles[1] if len(suggested_titles) > 1 else "Scientific Proof"
    })
    
    # Option 4: The Invisible Beacon / Mystery Angle
    hook_4 = "HIDDEN SIGNAL!" if is_mosquito else ("THE BIG TRAP!" if is_money else "COSMIC MYSTERY!")
    concept_4 = (
        "A dark bedroom at night where invisible glowing green and cyan carbon dioxide smoke currents drift like ocean currents "
        "across the room, forming an aerodynamic highway connecting a resting mosquito to human skin"
        if is_mosquito else
        (scene_prompts[min(120, len(scene_prompts)-1)][:160] if scene_prompts else f"The hidden invisible secret behind {topic}")
    )
    options_cfg.append({
        "id": 4,
        "hook": sanitize_thumbnail_text(hook_4),
        "prompt": concept_4,
        "pose": "shocked",
        "title": suggested_titles[2] if len(suggested_titles) > 2 else "Hidden Mystery"
    })
    
    # Option 5: The Contrast / Counter-Intuitive Truth (Victim vs Untouched)
    hook_5 = "ONLY YOU?!" if is_mosquito else ("STOP DOING THIS!" if is_money else "DONT TOUCH!")
    concept_5 = (
        "A split screen comparison: on the left a person sleeping peacefully and completely untouched with zero bites, "
        "on the right the viewer covered in itchy red welts surrounded by cartoon target crosshairs and a mosquito swarm"
        if is_mosquito else
        (scene_prompts[min(180, len(scene_prompts)-1)][:160] if scene_prompts else f"The stark contrasting reality of {topic}")
    )
    options_cfg.append({
        "id": 5,
        "hook": sanitize_thumbnail_text(hook_5),
        "prompt": concept_5,
        "pose": "curious",
        "title": suggested_titles[3] if len(suggested_titles) > 3 else "Counter-Intuitive Truth"
    })

    # 3. Generate each of the 5 thumbnails
    results = []
    for opt in options_cfg:
        opt_id = opt["id"]
        out_p = os.path.join(thumb_dir, f"Thumbnail_{opt_id}.png")
        opt["path"] = out_p
        
        # Check if already generated
        if not force_regen and os.path.exists(out_p) and os.path.getsize(out_p) > 5000:
            print(f"[Thumbnail {opt_id}/5] Already exists ({os.path.getsize(out_p)//1024} KB) -> {out_p}")
            opt["success"] = True
            results.append(opt)
            continue
            
        # If Option 1 and master Thumbnail exists, copy it
        if opt_id == 1 and not force_regen and os.path.exists(master_thumb) and os.path.getsize(master_thumb) > 5000:
            shutil.copyfile(master_thumb, out_p)
            print(f"[Thumbnail 1/5] Reused existing master Thumbnail.png -> {out_p}")
            opt["success"] = True
            results.append(opt)
            continue
            
        print(f"\n🎨 [Thumbnail {opt_id}/5] Generating Option #{opt_id}: Hook='{opt['hook']}', Pose='{opt['pose']}'...")
        ok = generate_thumbnail(
            prompt=opt["prompt"],
            text_overlay=opt["hook"],
            output_path=out_p,
            pose_name=opt["pose"],
            channel=channel
        )
        opt["success"] = ok
        results.append(opt)
        
    # Ensure master Thumbnail.png exists (copy Option 1 by default)
    thumb_1 = os.path.join(thumb_dir, "Thumbnail_1.png")
    if os.path.exists(thumb_1):
        if not os.path.exists(master_thumb) or force_regen:
            shutil.copyfile(thumb_1, master_thumb)
        if not os.path.exists(root_thumb) or force_regen:
            shutil.copyfile(thumb_1, root_thumb)
            
    print(f"\n✅ All 5 Thumbnails ready in {thumb_dir}!")
    return results
