import os
import sys
import json
import re
import textwrap
import subprocess
import shutil

AGENT_DIR = r"D:\youtube_automation_agent"
sys.path.insert(0, AGENT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import youtube_agent
import creative_assistant
import telegram_bot
import thumbnail_generator

def main():
    print("=" * 60)
    print("  STEP 11: FINAL DELIVERABLES & THUMBNAIL GENERATION")
    print("=" * 60)

    proj_dir = youtube_agent.get_active_project_dir()
    state = youtube_agent.load_state()
    topic = state.get("topic", "Revenue vs Profit: Where Does the Money Go?")
    title = state.get("title", "Revenue vs Profit: Where Does the Money Go?")

    print(f"Project: {proj_dir}")
    print(f"Topic  : {topic}")
    print(f"Title  : {title}")

    # 1. Save Full Script
    script_dir = os.path.join(proj_dir, "03_Script")
    os.makedirs(script_dir, exist_ok=True)
    script_path = os.path.join(script_dir, "Final_Script.md")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(state.get("script", ""))
    print("Saved Final_Script.md")

    # 2. Generate SEO Metadata
    print("Generating SEO Metadata...")
    seo_text = creative_assistant.generate_seo_metadata(topic, title)
    seo_dir = os.path.join(proj_dir, "02_SEO")
    os.makedirs(seo_dir, exist_ok=True)

    def get_seo_section(text, header_names):
        for name in header_names:
            pattern = rf"(?:^|\n)[*_\s]*{name}[*_\s]*:[*_\s]*(.*?)(?=\n[*_\s]*(?:SEO Title|SEO Description|Description|Keywords|Tags|Hashtags|Thumbnail Title|Thumbnail Text|Thumbnail Concept|Thumbnail Prompt)[*_\s]*:|\Z)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                raw_val = match.group(1).strip()
                raw_val = re.sub(r'^(?:\*\*|\*|__|_)\s*', '', raw_val)
                raw_val = re.sub(r'\s*(?:\*\*|\*|__|_)$', '', raw_val)
                return raw_val.strip()
        return ""

    desc = get_seo_section(seo_text, ["SEO Description", "Description"])
    keywords = get_seo_section(seo_text, ["Keywords"])
    tags = get_seo_section(seo_text, ["Tags"])
    hashtags = get_seo_section(seo_text, ["Hashtags"])

    if not desc: desc = f"Educational financial documentary about {topic}. Title: {title}"
    if not keywords: keywords = f"{topic}, revenue vs profit, business finance, money, stick figure"
    if not tags: tags = keywords
    if not hashtags: hashtags = f"#RevenueVsProfit #BusinessFinance #MoneyExplained"

    with open(os.path.join(seo_dir, "Description.md"), "w", encoding="utf-8") as f:
        f.write(desc)
    with open(os.path.join(seo_dir, "Keywords.md"), "w", encoding="utf-8") as f:
        f.write(keywords)
    with open(os.path.join(seo_dir, "Tags.md"), "w", encoding="utf-8") as f:
        f.write(tags)
    with open(os.path.join(seo_dir, "Hashtags.md"), "w", encoding="utf-8") as f:
        f.write(hashtags)
    print("Saved SEO files: Description, Keywords, Tags, Hashtags.")

    # Send SEO summary to Telegram
    chunks = textwrap.wrap(seo_text, width=3500, replace_whitespace=False)
    for chunk in chunks:
        telegram_bot.send_message(f"📋 *SEO Metadata Generated:*\n\n{chunk}")

    # 3. Generate Subtitles File (SRT) from Scene_Timeline.json
    print("Generating Subtitle.srt...")
    srt_dir = os.path.join(proj_dir, "09_Subtitles")
    os.makedirs(srt_dir, exist_ok=True)
    srt_path = os.path.join(srt_dir, "Subtitle.srt")
    timeline_path = os.path.join(proj_dir, "14_Checkpoints", "Scene_Timeline.json")
    scenes = youtube_agent.parse_scenes_from_file()

    if os.path.exists(timeline_path):
        with open(timeline_path, "r", encoding="utf-8") as f:
            tl = json.load(f)
        tl_map = {s["number"]: s for s in tl.get("scenes", [])}
        with open(srt_path, "w", encoding="utf-8") as f:
            srt_idx = 1
            for scene in scenes:
                narr = (scene.get("narration") or "").strip()
                if not narr or youtube_agent.is_title_card_scene(scene):
                    continue
                s_info = tl_map.get(scene["number"])
                if s_info:
                    st = s_info["start"]
                    en = s_info["end"]
                else:
                    st = 0.0
                    en = 5.0
                start_h, start_m, start_s = int(st // 3600), int((st % 3600) // 60), st % 60
                end_h, end_m, end_s = int(en // 3600), int((en % 3600) // 60), en % 60
                f.write(f"{srt_idx}\n")
                f.write(f"{start_h:02d}:{start_m:02d}:{int(start_s):02d},{int((start_s%1)*1000):03d} --> ")
                f.write(f"{end_h:02d}:{end_m:02d}:{int(end_s):02d},{int((end_s%1)*1000):03d}\n")
                f.write(f"{narr}\n\n")
                srt_idx += 1
    print("Saved Subtitle.srt")

    # 4. Generate Clean Subtitle Script
    subtitles_clean_dir = os.path.join(proj_dir, "17_Subtitles_Clean")
    os.makedirs(subtitles_clean_dir, exist_ok=True)
    clean_narration_lines = []
    for scene in scenes:
        narration = (scene.get("narration") or "").strip()
        if narration and not youtube_agent.is_title_card_scene(scene):
            clean_narration_lines.append(narration)
    clean_text = "\n".join(clean_narration_lines)
    clean_txt_path = os.path.join(subtitles_clean_dir, "Subtitle_Clean.txt")
    with open(clean_txt_path, "w", encoding="utf-8") as f:
        f.write(clean_text)
    print("Saved Subtitle_Clean.txt")
    telegram_bot.send_message("✍️ *Clean subtitle script text file generated and saved to '17_Subtitles_Clean/Subtitle_Clean.txt'*")

    # 5. Generate Timestamps
    timestamps_dir = os.path.join(proj_dir, "16_Timestamps")
    os.makedirs(timestamps_dir, exist_ok=True)
    timestamps_path = os.path.join(timestamps_dir, "Timestamps.txt")
    timestamps_text = youtube_agent.generate_youtube_timestamps(proj_dir)
    with open(timestamps_path, "w", encoding="utf-8") as f:
        f.write(timestamps_text)
    print("Saved Timestamps.txt")
    telegram_bot.send_message(f"⏱️ *Timestamps saved to '16_Timestamps/Timestamps.txt'*\n\n```\n{timestamps_text}\n```")

    # 6. Extract Voice_Final.wav
    final_video_path = os.path.join(proj_dir, "11_Final_Video", "Video_Final.mp4")
    voice_final_path = os.path.join(proj_dir, "07_Voice", "Voice_Final.wav")
    if os.path.exists(final_video_path):
        print(f"Extracting master audio to: {voice_final_path}")
        ffmpeg = youtube_agent.get_ffmpeg_path()
        subprocess.run([
            ffmpeg, "-y", "-i", final_video_path, "-vn", "-c:a", "pcm_s16le", voice_final_path
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("Saved Voice_Final.wav")

    # 7. Automated YouTube Thumbnail Generation
    print("\n🎨 Generating YouTube Thumbnail...")
    thumb_dir = os.path.join(proj_dir, "12_Thumbnail")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, "Thumbnail.png")
    root_thumb_path = os.path.join(proj_dir, "Thumbnail.png")

    click_text = "WHERE DOES IT GO?!"
    bg_prompt = "A massive open golden vault overflowing with glowing gold coins, currency stacks, and financial charts in clean 2D doodle cartoon style"

    print(f"Generating thumbnail with hook: '{click_text}'...")
    telegram_bot.send_message(f"🎨 *Generating YouTube Thumbnail Option*\nHook: `{click_text}`\nTheme: Open Gold Vault & Currency Stash...")

    thumbnail_generator.generate_thumbnail(
        prompt=bg_prompt,
        text_overlay=click_text,
        output_path=thumb_path,
        pose_name="pointing_right",
        channel="money"
    )

    if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 5000:
        shutil.copyfile(thumb_path, root_thumb_path)
        print(f"Thumbnail generated successfully ({os.path.getsize(thumb_path)//1024} KB)")

        buttons = [
            [
                {"text": "Approve 🚀", "callback_data": "approve_thumb"},
                {"text": "Regenerate 🔄", "callback_data": "regen_thumb"}
            ]
        ]
        telegram_bot.send_photo(
            root_thumb_path,
            caption=f"🎨 *YouTube Thumbnail Suggestion*\n*{title}*\nHook: *{click_text}*\n\nClick *Approve 🚀* to finalize, or *Regenerate 🔄* to create an alternative!",
            buttons=buttons
        )

    # Advance state to Step 15 (Shorts generation)
    state["step"] = 15
    youtube_agent.save_state(state)
    youtube_agent.save_checkpoint(state, "Checkpoint_FinalDeliverables.json")

    pcfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(pcfg_path):
        with open(pcfg_path, "r", encoding="utf-8") as f:
            pcfg = json.load(f)
        pcfg["step"] = 15
        with open(pcfg_path, "w", encoding="utf-8") as f:
            json.dump(pcfg, f, indent=4)

    print("=" * 60)
    print("  STEP 11 COMPLETED SUCCESSFULLY! ADVANCED TO STEP 15.")
    print("=" * 60)

if __name__ == "__main__":
    main()
