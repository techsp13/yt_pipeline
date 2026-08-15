"""
run_interactive_telegram_thumbnail.py
"""
import os, sys, json, re, shutil, zipfile

proj_dir = r"D:\youtube_automation_agent\channels\history\How_Did_Ancient_People_Stay_Cool_Without_Electrici_2026-08-11_084945"
sys.path.insert(0, r"D:\youtube_automation_agent")

active_json = r"D:\youtube_automation_agent\active_project.json"
with open(active_json, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": proj_dir}, f, indent=4)

from youtube_agent import (
    get_active_project_dir, get_channel_config, telegram_bot, get_user_interaction, load_state
)
import thumbnail_generator

def main():
    state = load_state()
    print("==========================================================")
    print("  INTERACTIVE TELEGRAM YOUTUBE THUMBNAIL GENERATOR")
    print("==========================================================")
    print(f"Active Project: {proj_dir}")

    scene_list_path = os.path.join(proj_dir, "04_Scenes", "Scene_List.json")
    thumb_dir = os.path.join(proj_dir, "12_Thumbnail")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, "Thumbnail.png")
    root_thumb_path = os.path.join(proj_dir, "Thumbnail.png")

def extract_seo_thumbnail_title(p_dir):
    """Extract top high-CTR thumbnail title from 02_SEO folder files."""
    seo_dir = os.path.join(p_dir, "02_SEO")
    if not os.path.exists(seo_dir):
        return None

    meta_p = os.path.join(seo_dir, "SEO_Metadata.json")
    if os.path.exists(meta_p):
        try:
            with open(meta_p, "r", encoding="utf-8") as f:
                data = json.load(f)
            top_rec = data.get("top_recommended_titles", []) or data.get("titles", [])
            for t in top_rec:
                if isinstance(t, str):
                    if "$" in t:
                        words = t.split()
                        return " ".join(words[:3]).upper()
                    elif "MISTAKE" in t.upper() or "BANKRUPT" in t.upper() or "SOLD" in t.upper():
                        return t.upper()[:25]
        except Exception:
            pass

    titles_md = os.path.join(seo_dir, "Titles.md")
    if os.path.exists(titles_md):
        try:
            with open(titles_md, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.search(r"1\.\s+\*\*(.*?)\*\*", content)
            if m:
                raw = m.group(1).strip()
                if "$" in raw:
                    return "$50 MILLION MISTAKE!"
                return raw.upper()[:25]
        except Exception:
            pass

    return None

def main():
    state = load_state()
    print("==========================================================")
    print("  INTERACTIVE TELEGRAM YOUTUBE THUMBNAIL GENERATOR")
    print("==========================================================")
    print(f"Active Project: {proj_dir}")

    scene_list_path = os.path.join(proj_dir, "04_Scenes", "Scene_List.json")
    thumb_dir = os.path.join(proj_dir, "12_Thumbnail")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, "Thumbnail.png")
    root_thumb_path = os.path.join(proj_dir, "Thumbnail.png")

    channel_cfg = get_channel_config()
    channel_name = channel_cfg.get("profile", channel_cfg.get("name", "history")).lower()
    titles_md = os.path.join(proj_dir, "02_SEO", "Titles.md")
    selected_title = state.get("title", "How Did Ancient People Stay Cool Without Electricity?")
    if os.path.exists(titles_md):
        with open(titles_md, "r", encoding="utf-8") as f:
            t_content = f.read()
            m = re.search(r"Locked Title:\s*(.*)", t_content)
            if m:
                selected_title = m.group(1).strip()

    seo_thumb_text = extract_seo_thumbnail_title(proj_dir)
    if seo_thumb_text:
        default_click_text = seo_thumb_text
    else:
        st_lower = selected_title.lower()
        if "freeze" in st_lower or "ice" in st_lower:
            default_click_text = "WHY NO FREEZE?!"
        elif "money" in st_lower or "rich" in st_lower or "bank" in st_lower or "wealth" in st_lower:
            default_click_text = "SECRET TO RICHES!"
        elif "space" in st_lower or "black hole" in st_lower or "star" in st_lower or "universe" in st_lower or "planet" in st_lower or "science" in st_lower:
            default_click_text = "COSMIC SECRETS!"
        elif channel_name == "money":
            default_click_text = "HOW THEY GOT RICH!"
        elif channel_name == "science":
            default_click_text = "HOW IT WORKS!"
        else:
            default_click_text = "HOW THEY SURVIVED!"

    # Ask user on Telegram for Thumbnail Title Text
    print("\n📲 Prompting user on Telegram for Thumbnail Title Text...")
    buttons = [[
        {"text": f"Use Default: '{default_click_text}' 🚀", "callback_data": "use_default_title"}
    ]]
    prompt_msg = telegram_bot.send_message(
        f"🖼️ *Thumbnail Title Prompt*\n\n"
        f"Video Title: _{selected_title}_\n\n"
        f"Reply to this message with your desired **Thumbnail Title Text** (e.g. `THE SECRET REVEALED!`), or click the button below to use default:",
        buttons=buttons
    )

    reply = get_user_interaction(prompt_msg)
    clean_reply = reply.replace("text:", "").strip()

    if clean_reply and clean_reply.lower() not in ["use_default_title", "default", "ok", "yes"]:
        click_text = clean_reply.upper()
        telegram_bot.send_message(f"✅ *Thumbnail Title Set:* `{click_text}`")
    else:
        click_text = default_click_text
        telegram_bot.send_message(f"✅ *Using Default Thumbnail Title:* `{click_text}`")

    # Interactive loop
    all_scenes_prompts = []
    if os.path.exists(scene_list_path):
        try:
            with open(scene_list_path, "r", encoding="utf-8") as f:
                all_sc = json.load(f)
            all_scenes_prompts = [s.get("image_prompt", s.get("narration", "")) for s in all_sc if s.get("image_prompt")]
        except Exception:
            pass

    if not all_scenes_prompts:
        all_scenes_prompts = [selected_title]

    poses = ["mind_blown", "pointing_right", "explaining"]
    thumb_count = 0

    approved = False
    while not approved:
        thumb_count += 1
        prompt_idx = (thumb_count - 1) % len(all_scenes_prompts)
        pose_name = poses[(thumb_count - 1) % len(poses)]
        bg_prompt = f"Key subject from: {all_scenes_prompts[prompt_idx][:120]}"

        print(f"\n🎨 Generating Thumbnail Option #{thumb_count} (Pose: {pose_name}, Text: '{click_text}')...")
        thumbnail_generator.generate_thumbnail(
            prompt=bg_prompt,
            text_overlay=click_text,
            pose_name=pose_name,
            output_path=thumb_path
        )

        if os.path.exists(thumb_path):
            shutil.copyfile(thumb_path, root_thumb_path)
            
            buttons = [
                [
                    {"text": "Approve 🚀", "callback_data": "approve_thumb"},
                    {"text": "Regenerate 🔄", "callback_data": "regen_thumb"}
                ],
                [
                    {"text": "✏️ Change / Reset Text", "callback_data": "reset_title_text"}
                ]
            ]
            
            select_msg = telegram_bot.send_photo(
                root_thumb_path,
                caption=f"🎨 *Thumbnail Suggestion #{thumb_count}*\n_{selected_title}_\nText: *{click_text}*\n\nClick *Approve 🚀* to lock this thumbnail, *Regenerate 🔄* for a new pose/object, or *✏️ Change / Reset Text* to enter new title text!",
                buttons=buttons
            )

            choice = get_user_interaction(select_msg)
            clean_choice = choice.replace("text:", "").strip()
            clean_lower = clean_choice.lower()
            
            if "approve" in clean_lower or clean_lower in ["approve_thumb", "approve", "publish", "yes", "/yes"]:
                approved = True
                telegram_bot.send_message(f"✅ *Thumbnail Approved!* Saved as final Thumbnail.")
                break
            elif "reset" in clean_lower or "change" in clean_lower or clean_lower == "reset_title_text":
                text_prompt_msg = telegram_bot.send_message(
                    f"✏️ *Reset Thumbnail Title Text*\n\n"
                    f"Current Text: `{click_text}`\n"
                    f"Reply to this message with your **New Thumbnail Title Text** (e.g. `THE SECRET REVEALED!`):"
                )
                text_reply = get_user_interaction(text_prompt_msg)
                new_text = text_reply.replace("text:", "").strip().upper()
                if new_text and new_text.lower() not in ["cancel", "back", "no"]:
                    click_text = new_text
                    telegram_bot.send_message(f"✅ *Thumbnail Title Reset To:* `{click_text}`")
                else:
                    telegram_bot.send_message("ℹ️ *Thumbnail title text unchanged.*")
            else:
                telegram_bot.send_message("🔄 *Generating new Thumbnail option...*")

    print("\n🎉 Thumbnail approved & final delivery complete!")

if __name__ == "__main__":
    main()
