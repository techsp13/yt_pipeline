"""
run_interactive_short_approval.py
"""
import os, sys, json

proj_dir = r"D:\youtube_automation_agent\channels\history\How_Did_Ancient_People_Stay_Cool_Without_Electrici_2026-08-11_084945"
sys.path.insert(0, r"D:\youtube_automation_agent")

active_json = r"D:\youtube_automation_agent\active_project.json"
with open(active_json, "w", encoding="utf-8") as f:
    json.dump({"active_project_dir": proj_dir}, f, indent=4)

from youtube_agent import generate_short_video, load_state, save_state, telegram_bot

def main():
    state = load_state()
    print("Resetting approved_short_scenes state for Telegram interactive image approval...")
    state["approved_short_scenes"] = {}
    save_state(state)

    telegram_bot.send_message(
        "📱 *Starting YouTube Short Image Approval Flow!*\n\n"
        "I will now generate 9:16 vertical images scene-by-scene and send each to Telegram for your review and approval (Approve ✅ / Regenerate 🔄 / Edit ✏️)."
    )

    print("Launching generate_short_video with interactive Telegram image approval loop...")
    generate_short_video(state)

if __name__ == "__main__":
    main()
