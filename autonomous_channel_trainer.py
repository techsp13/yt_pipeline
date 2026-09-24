# -*- coding: utf-8 -*-
"""
autonomous_channel_trainer.py
=============================
Broad-Spectrum Autonomous Competitor Training Engine.

Explores across 25+ top-tier creator channels in:
- History: Stefan Milo, Voices of the Past, History Time, Dan Carlin, Kings and Generals
- Money: Fern, How Money Works, ColdFusion, Economics Explained, Patrick Boyle, Wall Street Millennial
- Science: Veritasium, Be Smart, TierZoo, MinuteEarth, Real Science, Journey to the Microcosmos

Fetches transcripts, deconstructs narrative architecture, and expands opponent_playbook.json.
"""

import os
import sys
import time
import json
import yt_dlp
from opponent_learner import learn_from_video, _load_playbook

# Force UTF-8 on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

RADAR_CHANNELS = {
    "history": [
        "Stefan Milo Neanderthal",
        "Voices of the Past ancient eyewitness",
        "History Time ancient civilization mystery",
        "Dan Carlin epic history documentary",
        "Tasting History ancient survival food"
    ],
    "money": [
        "Fern documentary economics",
        "How Money Works economic trap",
        "ColdFusion corporate empire rise",
        "Economics Explained wealth inequality",
        "Wall Street Millennial corporate strategy",
        "Patrick Boyle financial scandal"
    ],
    "science": [
        "Veritasium scientific paradox",
        "Be Smart why do humans evolution",
        "TierZoo human evolution build",
        "MinuteEarth bodily biology quirk",
        "Real Science evolutionary mystery",
        "Journey to the Microcosmos cellular life"
    ]
}


def search_and_train(limit_per_category: int = 2):
    """Searches YouTube across our broad channel radar and ingests new winning video DNA."""
    print("=" * 65)
    print("  AUTONOMOUS BROAD-SPECTRUM COMPETITOR TRAINING ENGINE")
    print("=" * 65)
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'no_warnings': True
    }
    
    total_learned = 0
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for profile, search_queries in RADAR_CHANNELS.items():
            print(f"\n🔍 [Scanning {profile.upper()} Radar] ({len(search_queries)} potential sources)...")
            count_for_cat = 0
            
            for query in search_queries:
                if count_for_cat >= limit_per_category:
                    break
                    
                search_term = f"ytsearch1:{query}"
                try:
                    res = ydl.extract_info(search_term, download=False)
                    entries = res.get('entries', [])
                    if not entries:
                        continue
                        
                    entry = entries[0]
                    vid_id = entry.get('id')
                    title = entry.get('title', 'Unknown')
                    channel = entry.get('uploader', 'Unknown Creator')
                    
                    print(f"  Target: '{title}' by {channel} (ID: {vid_id})")
                    analysis = learn_from_video(vid_id, profile)
                    
                    if "error" not in analysis:
                        count_for_cat += 1
                        total_learned += 1
                        time.sleep(1.0)
                    else:
                        print(f"    Skipping: {analysis.get('error')}")
                except Exception as e:
                    print(f"    Search failed for '{query}': {e}")
                    
    print("\n" + "=" * 65)
    print(f"  TRAINING RUN COMPLETE: Ingested {total_learned} new competitor masterclasses!")
    print("=" * 65)
    
    # Print updated summary
    pb = _load_playbook()
    for cat in ["history", "money", "science"]:
        v_count = len(pb.get(cat, {}).get("analyzed_videos", []))
        wpm = pb.get(cat, {}).get("avg_wpm", 150)
        s_count = len(pb.get(cat, {}).get("sensory_bank", []))
        h_count = len(pb.get(cat, {}).get("hook_bank", []))
        print(f"• **{cat.capitalize()} Channel Brain:** {v_count} Analyzed Videos | {h_count} Stored Hooks | {s_count} Sensory Words | Avg Pacing: {wpm} WPM")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    search_and_train(limit_per_category=limit)
