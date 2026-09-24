# -*- coding: utf-8 -*-
"""
production_history_tracker.py
=============================
Automated Video Production History Tracker & Git Synchronization Engine.

1. Automatically scans all channels (history, money, science).
2. Extracts metadata for every video produced (Date, Channel, Topic, Title, Duration, Words, Status).
3. Generates and updates:
   - VIDEO_PRODUCTION_HISTORY.csv (Spreadsheet compatible with Excel / Google Sheets)
   - VIDEO_PRODUCTION_HISTORY.md (GitHub markdown table with links and summaries)
4. Provides a one-click or automated git commit & push to GitHub origin/main.
"""

import os
import sys
import json
import csv
import re
import wave
import subprocess
from datetime import datetime

# UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

AGENT_DIR = r"D:\youtube_automation_agent"
CHANNELS_DIR = os.path.join(AGENT_DIR, "channels")
CSV_PATH = os.path.join(AGENT_DIR, "VIDEO_PRODUCTION_HISTORY.csv")
MD_PATH = os.path.join(AGENT_DIR, "VIDEO_PRODUCTION_HISTORY.md")


def get_audio_duration(wav_path: str) -> float:
    try:
        if os.path.exists(wav_path):
            with wave.open(wav_path, "rb") as wf:
                return round(wf.getnframes() / float(wf.getframerate()), 2)
    except Exception:
        pass
    return 0.0


def scan_all_projects() -> list:
    """Scans all channel subdirectories for created projects and extracts metadata."""
    projects = []
    if not os.path.exists(CHANNELS_DIR):
        return projects

    for channel in ["history", "money", "science"]:
        ch_dir = os.path.join(CHANNELS_DIR, channel)
        if not os.path.exists(ch_dir):
            continue

        for entry in os.listdir(ch_dir):
            p_dir = os.path.join(ch_dir, entry)
            if not os.path.isdir(p_dir) or entry == "branding":
                continue

            cfg_file = os.path.join(p_dir, "Project_Config.json")
            if not os.path.exists(cfg_file):
                continue

            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                continue

            topic = cfg.get("topic", entry)
            title = cfg.get("title") or (cfg.get("suggested_titles", [topic])[0] if cfg.get("suggested_titles") else topic)
            
            # Extract date from folder name or file creation
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', entry)
            if date_match:
                date_str = date_match.group(1)
            else:
                mtime = os.path.getmtime(cfg_file)
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

            # Word count
            script_text = cfg.get("script", "")
            clean_words = re.sub(r'\(Visual:.*?\)', '', script_text)
            clean_words = re.sub(r'\*\*.*?\*\*', '', clean_words).split()
            word_count = len(clean_words)

            # Master audio duration
            voice_dir = os.path.join(p_dir, "07_Voice")
            wav_file = os.path.join(voice_dir, "Full_Script_Voice_pcm.wav")
            if not os.path.exists(wav_file):
                wav_file = os.path.join(voice_dir, "Voice_Final.wav")
            dur = get_audio_duration(wav_file)

            # Check final video file
            video_file = os.path.join(p_dir, "11_Final_Video", "Video_Final.mp4")
            if os.path.exists(video_file) and os.path.getsize(video_file) > 1024 * 1024:
                status = "✅ Final Video Ready"
                video_mb = round(os.path.getsize(video_file) / (1024 * 1024), 1)
            elif dur > 30:
                status = "🎙️ Voice & Audio Synced"
                video_mb = 0
            else:
                status = "📝 Script Draft"
                video_mb = 0

            projects.append({
                "date": date_str,
                "channel": channel.capitalize(),
                "topic": topic,
                "title": title,
                "words": word_count,
                "duration_sec": dur,
                "duration_min": f"{dur/60:.1f} min" if dur > 0 else "N/A",
                "status": status,
                "video_size_mb": video_mb,
                "folder": entry,
                "path": p_dir
            })

    # Sort descending by date
    projects.sort(key=lambda x: (x["date"], x["channel"]), reverse=True)
    return projects


def write_csv(projects: list):
    """Writes production records to clean CSV sheet."""
    fieldnames = ["Date", "Channel", "Topic", "Selected Title", "Word Count", "Audio Duration", "Status", "Video Size (MB)", "Folder Path"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in projects:
            writer.writerow({
                "Date": p["date"],
                "Channel": p["channel"],
                "Topic": p["topic"],
                "Selected Title": p["title"],
                "Word Count": p["words"],
                "Audio Duration": p["duration_min"],
                "Status": p["status"],
                "Video Size (MB)": p["video_size_mb"],
                "Folder Path": p["path"]
            })
    print(f"✅ Generated production CSV sheet -> {CSV_PATH}")


def write_markdown(projects: list):
    """Writes human-readable production history markdown table with summary metrics."""
    total_videos = len(projects)
    ready_count = sum(1 for p in projects if "Ready" in p["status"])
    ch_counts = {}
    for p in projects:
        ch_counts[p["channel"]] = ch_counts.get(p["channel"], 0) + 1

    lines = []
    lines.append("# 📊 Video Production History & Channel Tracker")
    lines.append(f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    lines.append("### 📈 Production Summary")
    lines.append(f"- **Total Projects Managed:** `{total_videos}`")
    lines.append(f"- **Rendered & Ready to Upload:** `{ready_count}`")
    ch_summary = " | ".join([f"**{ch}:** {cnt}" for ch, cnt in sorted(ch_counts.items())])
    lines.append(f"- **Channel Breakdown:** {ch_summary}\n")

    lines.append("---")
    lines.append("### 🎬 Production Ledger")
    lines.append("| Date | Channel | Selected Title | Runtime | Words | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    for p in projects:
        lines.append(f"| {p['date']} | **{p['channel']}** | {p['title']} | {p['duration_min']} | {p['words']} | {p['status']} |")

    lines.append("\n---\n*Tracked automatically by `production_history_tracker.py`. Synced to GitHub repository.*")

    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Generated production Markdown tracker -> {MD_PATH}")


def git_commit_and_push(commit_msg: str = None) -> bool:
    """Stages tracking sheets and pushes updates to GitHub origin/main."""
    if not commit_msg:
        commit_msg = f"chore(tracker): update video production history [{datetime.now().strftime('%Y-%m-%d')}]"

    print("\n[Git Sync] Staging production history files...")
    subprocess.run(["git", "-C", AGENT_DIR, "add", CSV_PATH, MD_PATH, "opponent_playbook.json"], check=False)
    
    # Check if there are changes to commit
    diff = subprocess.run(["git", "-C", AGENT_DIR, "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        print("[Git Sync] No new changes to commit. Everything up to date.")
        return True

    res = subprocess.run(["git", "-C", AGENT_DIR, "commit", "-m", commit_msg], capture_output=True, text=True, check=False)
    print(f"[Git Commit]: {res.stdout.strip() if res.stdout else res.stderr.strip()}")

    print("[Git Sync] Pushing to GitHub origin main...")
    push_res = subprocess.run(["git", "-C", AGENT_DIR, "push", "origin", "main"], capture_output=True, text=True, check=False)
    if push_res.returncode == 0:
        print("🎉 [Git Sync] Successfully pushed production history to GitHub!")
        return True
    else:
        print(f"⚠️ [Git Sync Warning] Push failed: {push_res.stderr.strip()}")
        return False


def update_and_sync(push_to_git: bool = False):
    """Main execution: Scans, writes CSV/MD, and optionally pushes to git."""
    print("=" * 60)
    print("  SCANNING CHANNELS FOR PRODUCTION HISTORY")
    print("=" * 60)
    projects = scan_all_projects()
    print(f"Found {len(projects)} projects across History, Money, and Science.")
    write_csv(projects)
    write_markdown(projects)
    
    if push_to_git:
        git_commit_and_push()

    return projects


if __name__ == "__main__":
    push_flag = "--push" in sys.argv
    update_and_sync(push_to_git=push_flag)
