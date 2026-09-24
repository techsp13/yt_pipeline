# -*- coding: utf-8 -*-
"""
competitor_intelligence.py
===========================
100% Free, Automated YouTube Video & Channel Teardown Engine.

Analyzes any YouTube video URL or ID:
1. Fetches full timed transcript + metadata (via youtube-transcript-api + yt-dlp, zero paid API keys).
2. Deconstructs the Narrative DNA:
   - The Opening Hook (0:00 - 0:45) & Curiosity Gap
   - Cadence & Rhythm (Sentence length variance, WPM pacing curve)
   - Retention Anchors (Open loops, cognitive dissonance, transition points)
   - Sensory Grounding Score (Concrete physical nouns vs abstract fluff)
   - Banned AI Vocabulary Scan (Verifies human writing authenticity)
3. Outputs an actionable blueprint ready to feed directly into creative_assistant.py.
"""

import os
import sys
import re
import json
import statistics
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

# Force UTF-8 encoding on standard output for Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Banned AI vocabulary that marks lazy AI generated scripts
BANNED_AI_WORDS = [
    "delve", "delving", "testament", "beacon", "tapestry", "realm", "pivotal",
    "furthermore", "moreover", "in conclusion", "it is important to remember",
    "fascinating", "shed light", "embark", "embarks", "plethora", "myriad",
    "at the end of the day", "vital role", "crucial role", "unwavering",
    "nestled", "whispers of", "echoes of", "journey through", "deep dive"
]

CONCRETE_SENSORY_TRIGGERS = [
    "cold", "shiver", "freeze", "frost", "ice", "blood", "sweat", "bone",
    "teeth", "skin", "dark", "smoke", "fire", "ember", "limestone", "stone",
    "dollar", "cash", "contract", "door", "bed", "hand", "fingers", "clock",
    "hunger", "starve", "raw", "iron", "copper", "dirt", "ash", "heartbeat"
]


def extract_video_id(url_or_id: str) -> str:
    """Extracts standard 11-char YouTube video ID from various URL formats."""
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    parsed = urlparse(url_or_id)
    if "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/").split("?")[0]
    elif "youtube.com" in parsed.netloc:
        if "/shorts/" in parsed.path:
            return parsed.path.split("/shorts/")[1].split("?")[0]
        qs = parse_qs(parsed.query)
        if "v" in qs:
            return qs["v"][0]
        if parsed.path.startswith("/live/"):
            return parsed.path.split("/live/")[1].split("?")[0]
    
    # Regex fallback
    m = re.search(r'([A-Za-z0-9_-]{11})', url_or_id)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract a valid YouTube video ID from '{url_or_id}'")


def fetch_video_metadata(video_id: str) -> dict:
    """Fetches high-level metadata (title, channel, views, duration) via yt-dlp without API key."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'skip_download': True,
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "id": video_id,
                "title": info.get("title", "Unknown Title"),
                "channel": info.get("uploader", "Unknown Channel"),
                "duration": info.get("duration", 0),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "upload_date": info.get("upload_date", ""),
                "description": info.get("description", "")[:500]
            }
    except Exception as e:
        return {
            "id": video_id,
            "title": f"Video {video_id}",
            "channel": "YouTube Creator",
            "duration": 0,
            "view_count": 0,
            "error": str(e)
        }


def _get_item_attr(item, attr, default=None):
    if hasattr(item, attr):
        return getattr(item, attr)
    if isinstance(item, dict):
        return item.get(attr, default)
    return default


def fetch_transcript(video_id: str) -> list:
    """Fetches clean timed transcript segments using youtube-transcript-api."""
    try:
        api = YouTubeTranscriptApi()
        raw_list = api.fetch(video_id)
        # Normalize into clean dict format
        clean_entries = []
        for r in raw_list:
            clean_entries.append({
                'text': _get_item_attr(r, 'text', ''),
                'start': float(_get_item_attr(r, 'start', 0.0)),
                'duration': float(_get_item_attr(r, 'duration', 0.0))
            })
        return clean_entries
    except Exception as e:
        print(f"[Transcript API Warning]: {e}. Attempting yt-dlp subtitle fallback...")
        return _fetch_transcript_via_ytdlp(video_id)


def _fetch_transcript_via_ytdlp(video_id: str) -> list:
    """Fallback transcript extractor via yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en.*', 'en'],
        'quiet': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subtitles = info.get('subtitles', {}) or info.get('automatic_captions', {})
            for lang, sub_formats in subtitles.items():
                if lang.startswith('en'):
                    for fmt in sub_formats:
                        if fmt.get('ext') == 'json3':
                            import requests
                            r = requests.get(fmt['url'], timeout=10)
                            if r.status_code == 200:
                                data = r.json()
                                entries = []
                                for event in data.get('events', []):
                                    if 'segs' in event:
                                        text = "".join(s.get('utf8', '') for s in event['segs']).strip()
                                        start = event.get('tStartMs', 0) / 1000.0
                                        dur = event.get('dDurationMs', 0) / 1000.0
                                        if text and text != '\n':
                                            entries.append({'text': text, 'start': start, 'duration': dur})
                                return entries
    except Exception as ex:
        print(f"[yt-dlp fallback error]: {ex}")
    return []


def analyze_transcript(transcript: list, meta: dict) -> dict:
    """
    Performs deep narrative & retention teardown on the transcript:
    - Hook breakdown (first 45s)
    - Sentence cadence & Gary Provost rhythm score
    - Speaking rate (WPM)
    - Sensory grounding vs AI fluff
    - Retention triggers
    """
    if not transcript:
        return {"error": "No transcript available for analysis"}

    total_duration = meta.get("duration", 0)
    if total_duration == 0 and transcript:
        last = transcript[-1]
        total_duration = last.get("start", 0) + last.get("duration", 0)

    # 1. Combine segments into continuous text with time markers
    full_text = " ".join([re.sub(r'\s+', ' ', item['text']) for item in transcript]).strip()
    words = full_text.split()
    total_words = len(words)
    wpm = (total_words / (total_duration / 60.0)) if total_duration > 0 else 0

    # 2. Extract Hook (0:00 to 0:45)
    hook_segments = [item['text'] for item in transcript if item.get('start', 0) <= 45.0]
    hook_text = " ".join(hook_segments).strip()
    hook_words = len(hook_text.split())

    # 3. Sentence Structure & Rhythm (Gary Provost Cadence Analysis)
    # Split text by punctuation (. ! ?)
    raw_sentences = re.split(r'[.!?]+', full_text)
    clean_sentences = [s.strip() for s in raw_sentences if len(s.strip().split()) > 1]
    
    sentence_lengths = [len(s.split()) for s in clean_sentences]
    avg_sentence_len = statistics.mean(sentence_lengths) if sentence_lengths else 0
    std_sentence_len = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0

    # Short (<6), Medium (7-18), Long (>19)
    short_s = sum(1 for l in sentence_lengths if l <= 6)
    med_s = sum(1 for l in sentence_lengths if 7 <= l <= 18)
    long_s = sum(1 for l in sentence_lengths if l >= 19)
    total_s = max(1, len(sentence_lengths))

    # Gary Provost Rhythm Score (0 to 100):
    rhythm_score = min(100, int((std_sentence_len / 7.0) * 100))

    # 4. Banned AI Words Scan
    lower_full = full_text.lower()
    found_ai_words = {}
    for bw in BANNED_AI_WORDS:
        count = len(re.findall(r'\b' + re.escape(bw) + r'\b', lower_full))
        if count > 0:
            found_ai_words[bw] = count

    # 5. Sensory Concrete Nouns Scan
    found_sensory_words = {}
    for sw in CONCRETE_SENSORY_TRIGGERS:
        count = len(re.findall(r'\b' + re.escape(sw) + r'\b', lower_full))
        if count > 0:
            found_sensory_words[sw] = count

    sensory_density = sum(found_sensory_words.values()) / max(1, (total_words / 100.0))  # per 100 words

    # 6. Retention & Open Loop Triggers
    turn_words = ["but", "however", "yet", "until", "suddenly", "instead", "except"]
    turn_count = sum(len(re.findall(r'\b' + re.escape(tw) + r'\b', lower_full)) for tw in turn_words)
    turns_per_min = turn_count / max(0.5, (total_duration / 60.0))

    # Question count (curiosity hooks)
    question_count = full_text.count("?")

    return {
        "metadata": meta,
        "total_words": total_words,
        "duration_seconds": round(total_duration, 1),
        "speaking_wpm": round(wpm, 1),
        "hook": {
            "text": hook_text,
            "word_count": hook_words,
            "duration_analyzed": 45.0
        },
        "cadence_and_rhythm": {
            "total_sentences": total_s,
            "avg_words_per_sentence": round(avg_sentence_len, 1),
            "sentence_length_std_dev": round(std_sentence_len, 2),
            "short_sentences_pct": round(short_s / total_s * 100, 1),
            "medium_sentences_pct": round(med_s / total_s * 100, 1),
            "long_sentences_pct": round(long_s / total_s * 100, 1),
            "rhythm_variety_score": rhythm_score
        },
        "authenticity_and_style": {
            "banned_ai_words_found": found_ai_words,
            "is_likely_ai": len(found_ai_words) > 4 or std_sentence_len < 3.2,
            "sensory_words_count": sum(found_sensory_words.values()),
            "sensory_density_per_100w": round(sensory_density, 2),
            "top_sensory_words": sorted(found_sensory_words.items(), key=lambda x: x[1], reverse=True)[:8]
        },
        "retention_mechanics": {
            "curiosity_questions": question_count,
            "tension_turns_per_minute": round(turns_per_min, 2)
        }
    }


def format_report_markdown(analysis: dict) -> str:
    """Formats analysis into a clean, human-readable blueprint report."""
    if "error" in analysis:
        return f"# Error Analyzing Video\n{analysis['error']}"

    m = analysis["metadata"]
    c = analysis["cadence_and_rhythm"]
    a = analysis["authenticity_and_style"]
    r = analysis["retention_mechanics"]
    h = analysis["hook"]

    report = []
    report.append(f"# 🎬 Narrative & Retention Teardown: {m.get('title')}")
    report.append(f"**Channel:** {m.get('channel')} | **Views:** {m.get('view_count'):,} | **Duration:** {analysis['duration_seconds']}s (~{analysis['duration_seconds']/60:.1f} min)")
    report.append(f"**Speaking Velocity:** {analysis['speaking_wpm']} Words/Minute | **Total Words:** {analysis['total_words']}\n")

    report.append("---")
    report.append("### 🪝 1. The Opening Hook Architecture (First 45s)")
    report.append(f"> \"{h['text'][:350]}...\"\n")
    report.append(f"* **Hook Word Count:** {h['word_count']} words")
    report.append(f"* **Pacing in Hook:** {round(h['word_count'] / 0.75, 1)} WPM")

    report.append("\n---")
    report.append("### 🎵 2. Rhythm & Sentence Cadence (The Music of Human Speech)")
    report.append(f"* **Rhythm Variety Score:** `{c['rhythm_variety_score']}/100` " + ("🔥 (Master Human Cadence)" if c['rhythm_variety_score'] >= 70 else "⚠️ (Monotonous AI Pattern)"))
    report.append(f"* **Average Sentence Length:** {c['avg_words_per_sentence']} words (Std Dev: ±{c['sentence_length_std_dev']})")
    report.append(f"* **Short Punchy Sentences (≤ 6 words):** {c['short_sentences_pct']}% (Creates dramatic impacts)")
    report.append(f"* **Medium Flowing Sentences (7–18 words):** {c['medium_sentences_pct']}% (Builds thought)")
    report.append(f"* **Long Crescendo Waves (≥ 19 words):** {c['long_sentences_pct']}% (Draws viewer in)")

    report.append("\n---")
    report.append("### 🧠 3. Authenticity vs. AI Fluff")
    report.append(f"* **Banned AI Vocabulary:** {len(a['banned_ai_words_found'])} detected " + ("✅ 100% Clean Human Tone" if not a['banned_ai_words_found'] else f"❌ Contains: {list(a['banned_ai_words_found'].keys())}"))
    report.append(f"* **Sensory Concrete Density:** `{a['sensory_density_per_100w']}` physical words per 100 words")
    top_sensory = ", ".join([f"{k} ({v})" for k, v in a['top_sensory_words']])
    report.append(f"* **Primary Sensory Anchors:** {top_sensory or 'None'}")

    report.append("\n---")
    report.append("### 📈 4. Retention & Attention Anchors")
    report.append(f"* **Curiosity Questions Posed:** {r['curiosity_questions']}")
    report.append(f"* **Plot Twists / Conflict Turns:** `{r['tension_turns_per_minute']}` turns per minute (Pacing friction)")

    report.append("\n---")
    report.append("### 💡 Actionable Formula for Our Pipeline:")
    report.append(f"1. **Match Hook WPM:** Start with a rapid, sensory cold open at ~{round(h['word_count'] / 0.75, 1)} WPM.")
    report.append(f"2. **Maintain Sentence Diversity:** Target {c['short_sentences_pct']}% short punches, {c['medium_sentences_pct']}% medium, and {c['long_sentences_pct']}% long waves.")
    report.append("3. **Concrete Noun Mandate:** Ground every argument in physical objects (smoke, glass, coins, skin) rather than academic concepts.")

    return "\n".join(report)


def run_teardown(url_or_id: str, save_report_path: str = None) -> dict:
    """Main execution function for CLI or automated pipeline import."""
    video_id = extract_video_id(url_or_id)
    print(f"\n[Competitor Intelligence] Fetching metadata for Video ID: {video_id}...")
    meta = fetch_video_metadata(video_id)
    print(f"  Title: {meta.get('title')}")
    print(f"  Channel: {meta.get('channel')}")
    
    print("[Competitor Intelligence] Fetching transcript (100% free)...")
    transcript = fetch_transcript(video_id)
    if not transcript:
        print("❌ Could not retrieve transcript for this video.")
        return {"error": "Transcript extraction failed"}

    print(f"  Retrieved {len(transcript)} transcript segments.")
    print("[Competitor Intelligence] Running Narrative & Retention Teardown...")
    analysis = analyze_transcript(transcript, meta)
    
    markdown = format_report_markdown(analysis)
    print("\n" + "=" * 65)
    print(markdown)
    print("=" * 65)

    if save_report_path:
        os.makedirs(os.path.dirname(save_report_path), exist_ok=True)
        with open(save_report_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"\n[Report Saved] -> {save_report_path}")

    return analysis


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "QW_jlUn4gA8"
    run_teardown(target)
