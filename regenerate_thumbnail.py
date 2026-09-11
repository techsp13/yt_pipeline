import os
import sys
import shutil

AGENT_DIR = r"D:\youtube_automation_agent"
sys.path.insert(0, AGENT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import youtube_agent
import telegram_bot
import thumbnail_generator

def main():
    print("=" * 60)
    print("  REGENERATING YOUTUBE THUMBNAIL (OPTION 2)")
    print("=" * 60)

    proj_dir = youtube_agent.get_active_project_dir()
    state = youtube_agent.load_state()
    title = state.get("title", "Revenue vs Profit: Where Does the Money Go?")

    thumb_dir = os.path.join(proj_dir, "12_Thumbnail")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_v2_path = os.path.join(thumb_dir, "Thumbnail_v2.png")
    thumb_master_path = os.path.join(thumb_dir, "Thumbnail.png")
    root_thumb_path = os.path.join(proj_dir, "Thumbnail.png")

    # High-CTR Leaky Bucket & Empty Vault Concept
    click_text = "WHERE'S THE PROFIT?!"
    bg_prompt = (
        "A giant rustic wooden bucket with the word REVENUE boldly written in marker on its side, "
        "overflowing with dollar bills at the top, but with multiple large cartoon holes leaking gushing streams "
        "of green money and gold coins onto the ground below. Clean 2D doodle webcomic cartoon style, "
        "vibrant saturated colors, generous negative space."
    )

    telegram_bot.send_message(
        f"🎨 *Regenerating YouTube Thumbnail (Option 2)*\n"
        f"Hook: `{click_text}`\n"
        f"Theme: The Leaking Revenue Bucket..."
    )

    print(f"Calling thumbnail_generator with Hook: '{click_text}'...")
    ok = thumbnail_generator.generate_thumbnail(
        prompt=bg_prompt,
        text_overlay=click_text,
        output_path=thumb_v2_path,
        pose_name="mind_blown",
        channel="money"
    )

    if ok and os.path.exists(thumb_v2_path) and os.path.getsize(thumb_v2_path) > 5000:
        # Copy to primary Thumbnail.png
        shutil.copyfile(thumb_v2_path, thumb_master_path)
        shutil.copyfile(thumb_v2_path, root_thumb_path)
        size_kb = os.path.getsize(thumb_v2_path) // 1024
        print(f"SUCCESS! New thumbnail generated: {thumb_v2_path} ({size_kb} KB)")

        buttons = [
            [
                {"text": "Approve 🚀", "callback_data": "approve_thumb"},
                {"text": "Regenerate Again 🔄", "callback_data": "regen_thumb"}
            ]
        ]
        telegram_bot.send_photo(
            root_thumb_path,
            caption=(
                f"🎨 *YouTube Thumbnail Suggestion (Option 2)*\n"
                f"*{title}*\n"
                f"Hook: *{click_text}*\n\n"
                f"Click *Approve 🚀* to lock this new thumbnail, or *Regenerate Again 🔄* for another variation!"
            ),
            buttons=buttons
        )
        print("Dispatched new thumbnail to Telegram with approval buttons!")
    else:
        print("ERROR: Failed to generate new thumbnail!")
        sys.exit(1)

if __name__ == "__main__":
    main()
