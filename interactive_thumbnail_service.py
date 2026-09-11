import os
import sys
import io
import time
import json
import shutil

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, r"D:\youtube_automation_agent")
from dotenv import load_dotenv
load_dotenv(r"D:\youtube_automation_agent\.env")

import telegram_bot
from playwright_flow_generator import generate_image_playwright

PROJ_DIR = r"D:\youtube_automation_agent\channels\science\NASA_Just_Launched_a_Telescope_That_Can_See_100_Mo_2026-09-01_115815"
THUMB_DIR = os.path.join(PROJ_DIR, "12_Thumbnail")
OUT_THUMB = os.path.join(THUMB_DIR, "Thumbnail.png")
ROOT_THUMB = os.path.join(PROJ_DIR, "Thumbnail.png")
CONFIG_PATH = os.path.join(PROJ_DIR, "Project_Config.json")
AGENT_STATE_PATH = r"D:\youtube_automation_agent\agent_state.json"

POSES = [
    {
        "name": "explaining",
        "desc": "an expressive cute stickman mascot character with a smooth solid pure white round head (#FFFFFF), thick black marker outline, black dot eyes, wearing white scientist lab goggles and white lab coat, pointing excitedly with black stick limbs"
    },
    {
        "name": "mind_blown",
        "desc": "an expressive cute stickman mascot character with a smooth solid pure white round head (#FFFFFF), thick black marker outline, wide shocked dot eyes, wearing white scientist lab goggles pushed slightly up and white lab coat, with hands on cheeks in mind-blown shock and awe, black stick limbs"
    },
    {
        "name": "pointing_right",
        "desc": "an expressive cute stickman mascot character with a smooth solid pure white round head (#FFFFFF), thick black marker outline, excited wide eyes and big smile, wearing white scientist lab goggles and white lab coat, energetically pointing both hands toward the cosmic center, black stick limbs"
    }
]

BACKGROUNDS = [
    "A colossal glowing cosmic mystery with electric cyan energy accretion disk warping space and stars, NASA Nancy Grace Roman Space Telescope scanning deep space",
    "A colossal breathtaking cosmic panoramic view with Nancy Grace Roman Space Telescope floating in space, scanning a dense glittering expanse of millions of galaxies and glowing electric cyan and deep blue nebulae stretching across infinity",
    "A dramatic ultra-wide field of deep space featuring glowing spiral galaxies, cosmic dust filaments in electric cyan and magenta, and the sleek Roman Space Telescope with high-tech sunshield"
]

def update_state_step(new_step):
    for p in [CONFIG_PATH, AGENT_STATE_PATH]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                d["step"] = new_step
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(d, f, indent=2)
                print(f"Updated {p} step -> {new_step}")
            except Exception as e:
                print(f"Error updating {p}: {e}")

def run_service():
    print("Starting interactive thumbnail service...", flush=True)
    thumb_count = 2
    click_text = "100X MORE SKY!"
    
    # We already generated Option #2, so we start by presenting Option #2
    buttons = [
        [
            {"text": "Approve 🚀", "callback_data": "approve_thumb"},
            {"text": "Regenerate 🔄", "callback_data": "regen_thumb"}
        ],
        [
            {"text": "✏️ Change / Reset Text", "callback_data": "reset_title_text"}
        ]
    ]

    # Send Option #2 photo to Telegram
    caption = (
        f"🎨 *YouTube Thumbnail Option #{thumb_count} Generated!*\n"
        f"_NASA's New Telescope: See 100x More Sky! What's Hidden?_\n"
        f"Pose: *Mind Blown 🤯* | Text: *{click_text}*\n\n"
        f"Click *Approve 🚀* to lock this thumbnail, *Regenerate 🔄* for another variation, or *✏️ Change / Reset Text* to edit text!"
    )
    select_msg = telegram_bot.send_photo(ROOT_THUMB, caption=caption, buttons=buttons)
    print(f"Sent Option #{thumb_count} to Telegram. Waiting for interaction...", flush=True)

    while True:
        choice = telegram_bot.wait_for_interaction(select_msg)
        clean_choice = choice.replace("text:", "").strip().lower()
        print(f"Received choice: {clean_choice}", flush=True)

        if "approve" in clean_choice or clean_choice in ["approve_thumb", "approve", "publish", "yes", "/yes"]:
            telegram_bot.send_message(f"✅ *Thumbnail Approved!* Locked as final master Thumbnail.")
            update_state_step(15)
            print("Thumbnail approved! Step advanced to 15. Service exiting successfully.", flush=True)
            break

        elif "reset" in clean_choice or "change" in clean_choice or clean_choice == "reset_title_text":
            text_prompt_msg = telegram_bot.send_message(
                f"✏️ *Reset Thumbnail Title Text*\n\n"
                f"Current Text: `{click_text}`\n"
                f"Reply to this message with your **New Thumbnail Title Text** (e.g. `SECRETS REVEALED!`):"
            )
            text_reply = telegram_bot.wait_for_interaction(text_prompt_msg)
            new_text = text_reply.replace("text:", "").strip().upper()
            if new_text and new_text.lower() not in ["cancel", "back", "no"]:
                click_text = new_text
                telegram_bot.send_message(f"✅ *Thumbnail Title Reset To:* `{click_text}`")
            else:
                telegram_bot.send_message("ℹ️ *Thumbnail title text unchanged.*")
            
            # Now regenerate with updated text
            thumb_count += 1
            pose_info = POSES[(thumb_count - 1) % len(POSES)]
            bg_info = BACKGROUNDS[(thumb_count - 1) % len(BACKGROUNDS)]
            v_path = os.path.join(THUMB_DIR, f"Thumbnail_v{thumb_count}.png")

            telegram_bot.send_message(f"🔄 *Generating Thumbnail Option #{thumb_count} with text '{click_text}'...* Please wait!")
            full_prompt = (
                f"A viral YouTube thumbnail in clean 2D webcomic cartoon doodle art style. "
                f"TEXT: Big bold hand-drawn 2D cartoon doodle bubble lettering across the top that reads '{click_text}' in 100% solid bright saturated golden yellow (#FFCC00) with thick heavy black ink marker outlines around every letter. Perfectly sharp, readable, high-contrast YouTube thumbnail typography. "
                f"MASCOT: On the right side, {pose_info['desc']}. "
                f"BACKGROUND: {bg_info}. "
                f"STYLE: 2D hand-drawn webcomic cartoon doodle illustration, crisp bold ink outlines, vibrant saturated colors, 16:9 widescreen YouTube thumbnail format, high CTR composition."
            )

            ok = generate_image_playwright(full_prompt, v_path, aspect_ratio="16:9")
            if ok and os.path.exists(v_path):
                shutil.copyfile(v_path, OUT_THUMB)
                shutil.copyfile(v_path, ROOT_THUMB)
                caption = (
                    f"🎨 *Thumbnail Option #{thumb_count} Generated!*\n"
                    f"_NASA's New Telescope: See 100x More Sky! What's Hidden?_\n"
                    f"Pose: *{pose_info['name']}* | Text: *{click_text}*\n\n"
                    f"Click *Approve 🚀* to lock this thumbnail, *Regenerate 🔄* for another variation, or *✏️ Change / Reset Text* to edit text!"
                )
                select_msg = telegram_bot.send_photo(ROOT_THUMB, caption=caption, buttons=buttons)
            else:
                telegram_bot.send_message(f"⚠️ *Generation error on Option #{thumb_count}*. Retrying...")

        elif "regen" in clean_choice or clean_choice == "regen_thumb":
            thumb_count += 1
            pose_info = POSES[(thumb_count - 1) % len(POSES)]
            bg_info = BACKGROUNDS[(thumb_count - 1) % len(BACKGROUNDS)]
            v_path = os.path.join(THUMB_DIR, f"Thumbnail_v{thumb_count}.png")

            telegram_bot.send_message(f"🔄 *Generating Thumbnail Option #{thumb_count} (Pose: {pose_info['name']})...* Please wait!")
            full_prompt = (
                f"A viral YouTube thumbnail in clean 2D webcomic cartoon doodle art style. "
                f"TEXT: Big bold hand-drawn 2D cartoon doodle bubble lettering across the top that reads '{click_text}' in 100% solid bright saturated golden yellow (#FFCC00) with thick heavy black ink marker outlines around every letter. Perfectly sharp, readable, high-contrast YouTube thumbnail typography. "
                f"MASCOT: On the right side, {pose_info['desc']}. "
                f"BACKGROUND: {bg_info}. "
                f"STYLE: 2D hand-drawn webcomic cartoon doodle illustration, crisp bold ink outlines, vibrant saturated colors, 16:9 widescreen YouTube thumbnail format, high CTR composition."
            )

            ok = generate_image_playwright(full_prompt, v_path, aspect_ratio="16:9")
            if ok and os.path.exists(v_path):
                shutil.copyfile(v_path, OUT_THUMB)
                shutil.copyfile(v_path, ROOT_THUMB)
                caption = (
                    f"🎨 *Thumbnail Option #{thumb_count} Generated!*\n"
                    f"_NASA's New Telescope: See 100x More Sky! What's Hidden?_\n"
                    f"Pose: *{pose_info['name']}* | Text: *{click_text}*\n\n"
                    f"Click *Approve 🚀* to lock this thumbnail, *Regenerate 🔄* for another variation, or *✏️ Change / Reset Text* to edit text!"
                )
                select_msg = telegram_bot.send_photo(ROOT_THUMB, caption=caption, buttons=buttons)
            else:
                telegram_bot.send_message(f"⚠️ *Generation error on Option #{thumb_count}*. Retrying...")

if __name__ == "__main__":
    run_service()
