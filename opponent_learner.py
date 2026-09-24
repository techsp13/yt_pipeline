# -*- coding: utf-8 -*-
"""
opponent_learner.py
===================
Opponent Channel Intelligence & Continuous Learning Engine.

Learns directly from competitor channels:
1. Ingests video URLs or channel handles from top creators (Kurzgesagt, MagnatesMedia, Moon, Ink Explainer).
2. Extracts their winning Hook architectures, Open Loop formulas, Pacing benchmarks, and Sensory Noun Banks.
3. Saves the distilled patterns into a persistent 'opponent_playbook.json'.
4. Injects real proven competitor DNA directly into creative_assistant.py so future scripts mimic the exact retention mechanisms of multi-million view videos.
"""

import os
import sys
import json
from competitor_intelligence import extract_video_id, fetch_video_metadata, fetch_transcript, analyze_transcript

AGENT_DIR = r"D:\youtube_automation_agent"
PLAYBOOK_FILE = os.path.join(AGENT_DIR, "opponent_playbook.json")


def _load_playbook() -> dict:
    if os.path.exists(PLAYBOOK_FILE):
        try:
            with open(PLAYBOOK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "history": {"analyzed_videos": [], "hook_bank": [], "avg_wpm": 150, "sensory_bank": []},
        "money": {"analyzed_videos": [], "hook_bank": [], "avg_wpm": 155, "sensory_bank": []},
        "science": {"analyzed_videos": [], "hook_bank": [], "avg_wpm": 150, "sensory_bank": []}
    }


def _save_playbook(data: dict):
    with open(PLAYBOOK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def learn_from_video(url_or_id: str, profile: str = "history") -> dict:
    """
    Dissects a competitor video and permanently incorporates its winning DNA
    into our channel profile playbook.
    """
    video_id = extract_video_id(url_or_id)
    print(f"\n[Opponent Learner] Ingesting competitor video: {video_id} for channel '{profile}'...")
    
    meta = fetch_video_metadata(video_id)
    transcript = fetch_transcript(video_id)
    if not transcript:
        print(f"❌ Failed to extract transcript for {video_id}")
        return {"error": "Transcript unavailable"}

    analysis = analyze_transcript(transcript, meta)
    if "error" in analysis:
        return analysis

    playbook = _load_playbook()
    if profile not in playbook:
        playbook[profile] = {"analyzed_videos": [], "hook_bank": [], "avg_wpm": 150, "sensory_bank": []}

    target_profile = playbook[profile]
    
    # Check if already learned
    existing_ids = [v.get("id") for v in target_profile.get("analyzed_videos", [])]
    if video_id in existing_ids:
        print(f"  [Info] Video {video_id} is already in the {profile} playbook.")
        return analysis

    # Extract Hook
    hook_text = analysis["hook"]["text"]
    if len(hook_text.split()) > 20:
        target_profile["hook_bank"].append({
            "title": meta.get("title"),
            "channel": meta.get("channel"),
            "hook_excerpt": hook_text[:300],
            "views": meta.get("view_count", 0)
        })

    # Update WPM average
    new_wpm = analysis["speaking_wpm"]
    current_videos_count = len(target_profile.get("analyzed_videos", []))
    prev_wpm = target_profile.get("avg_wpm", 150)
    target_profile["avg_wpm"] = round((prev_wpm * current_videos_count + new_wpm) / (current_videos_count + 1), 1)

    # Add sensory vocabulary
    sensory_words = [k for k, _ in analysis["authenticity_and_style"].get("top_sensory_words", [])]
    for sw in sensory_words:
        if sw not in target_profile.get("sensory_bank", []):
            target_profile["sensory_bank"].append(sw)

    # Save summary of analyzed video
    target_profile["analyzed_videos"].append({
        "id": video_id,
        "title": meta.get("title"),
        "channel": meta.get("channel"),
        "views": meta.get("view_count", 0),
        "rhythm_score": analysis["cadence_and_rhythm"]["rhythm_variety_score"],
        "sentence_avg": analysis["cadence_and_rhythm"]["avg_words_per_sentence"]
    })

    _save_playbook(playbook)
    print(f"✅ Successfully learned from: '{meta.get('title')}' by {meta.get('channel')}")
    print(f"  Updated Playbook: {len(target_profile['analyzed_videos'])} videos analyzed for profile '{profile}'.")
    return analysis


def get_competitor_guidance_for_prompt(profile: str) -> str:
    """
    Returns an engineered prompt block summarizing all learned opponent patterns
    to inject directly into creative_assistant.py write_script().
    """
    playbook = _load_playbook()
    data = playbook.get(profile, {})
    hooks = data.get("hook_bank", [])
    if not hooks:
        return ""

    guidance = []
    guidance.append("\n    PROVEN OPPONENT CHANNEL RETENTION DNA (LEARNED BENCHMARKS):")
    guidance.append(f"    - Target Speaking Velocity: ~{data.get('avg_wpm', 150)} Words Per Minute.")
    
    # Include up to 2 real winning hook examples
    guidance.append("    - Winning Competitor Hook Archetypes (Study their opening sentence structure):")
    for i, h in enumerate(hooks[-2:], 1):
        guidance.append(f'      * Reference #{i} ({h.get("channel")}, {h.get("views", 0):,} views): "{h.get("hook_excerpt")}..."')

    if data.get("sensory_bank"):
        sensory_str = ", ".join(data.get("sensory_bank", [])[:10])
        guidance.append(f"    - High-Retention Physical Sensory Anchors (use frequently): {sensory_str}.")

    return "\n".join(guidance)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        vid = sys.argv[1]
        prof = sys.argv[2] if len(sys.argv) > 2 else "history"
        learn_from_video(vid, prof)
    else:
        print("Usage: python opponent_learner.py <youtube_url_or_id> [channel_profile]")
