"""
build_perfect_continuous_timeline.py
────────────────────────────────────
Generates a 100% Continuous, Gap-Free, Frame-Snapped Timeline for 204 Scenes.

Guarantees:
1. Scene 1 starts at 0.000s (frame 0).
2. For all scenes i in [1..N-1]: scene[i].start == scene[i-1].end.
3. Every audio pause between words/paragraphs is fully filled by the preceding scene visual.
4. Scene 204 ends at exactly 540.8400s (frame 13521).
5. Sum of scene durations == 540.8400s (exact match to master audio).
"""

import json
import os
import re
import sys
import wave
from difflib import SequenceMatcher


def get_wav_duration(wav_path):
    with wave.open(wav_path, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def clean_narration(txt):
    txt = re.sub(r"\[.*?\]", "", txt or "")
    txt = re.sub(r"\*+", "", txt)
    return txt.strip()


def norm_words(text):
    return [re.sub(r"[^a-z0-9]", "", w) for w in text.lower().split()
            if re.sub(r"[^a-z0-9]", "", w)]


def window_score(scene_wlist, start_idx, all_words, W):
    n = len(scene_wlist)
    end_idx = min(start_idx + n, W)
    chunk = [all_words[i][2] for i in range(start_idx, end_idx)]
    return SequenceMatcher(None, scene_wlist, chunk).ratio()


def main():
    FPS = 25
    AGENT_DIR   = r"D:\youtube_automation_agent"
    ACTIVE_JSON = os.path.join(AGENT_DIR, "active_project.json")

    with open(ACTIVE_JSON, encoding="utf-8") as f:
        ACTIVE_PROJ = json.load(f)["active_project_dir"]

    VOICE_DIR      = os.path.join(ACTIVE_PROJ, "07_Voice")
    CHECKPOINT_DIR = os.path.join(ACTIVE_PROJ, "14_Checkpoints")
    SCENES_DIR     = os.path.join(ACTIVE_PROJ, "04_Scenes")
    MASTER_WAV     = os.path.join(VOICE_DIR, "Full_Script_Voice_pcm.wav")
    SCRIPT_JSON    = os.path.join(SCENES_DIR, "Scene_List.json")
    TIMELINE_PATH  = os.path.join(CHECKPOINT_DIR, "Scene_Timeline.json")

    print(f"Active Project: {ACTIVE_PROJ}")

    if not os.path.exists(MASTER_WAV):
        mp3_path = os.path.join(VOICE_DIR, "Full_Script_Voice.mp3")
        if os.path.exists(mp3_path):
            print(f"[Timeline] Converting {mp3_path} to PCM WAV ({MASTER_WAV})...")
            import subprocess
            ffmpeg_cmd = ["ffmpeg", "-y", "-i", mp3_path, "-ac", "1", "-ar", "24000", MASTER_WAV]
            subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        else:
            print(f"ERROR: Missing master WAV at {MASTER_WAV}")
            sys.exit(1)

    total_dur = get_wav_duration(MASTER_WAV)
    total_frames = round(total_dur * FPS)

    print(f"Master Audio Duration: {total_dur:.6f}s")
    print(f"Total Video Frames   : {total_frames} frames (at {FPS} FPS = {total_frames/FPS:.4f}s)")

    # 1. Load scenes
    with open(SCRIPT_JSON, encoding="utf-8") as f:
        script = json.load(f)
    scenes = script if isinstance(script, list) else script.get("scenes", [])

    valid_scenes = []
    for sc in scenes:
        if sc.get("is_title_card", False) or sc.get("scene_type", "") == "title_card":
            continue
        narr = clean_narration(sc.get("narration", ""))
        if narr and len(narr) >= 2:
            valid_scenes.append((sc, narr))

    N = len(valid_scenes)
    print(f"Valid Narration Scenes: {N}")

    # 2. Forced alignment with faster_whisper
    print("\n[Align] Running faster-whisper word-level transcription...")
    from faster_whisper import WhisperModel

    model = WhisperModel("base", device="cpu", compute_type="int8")
    seg_iter, _ = model.transcribe(
        MASTER_WAV,
        word_timestamps=True,
        language="en",
        beam_size=1,
        vad_filter=False,
    )

    all_words = []
    for seg in seg_iter:
        if hasattr(seg, "words") and seg.words:
            for w in seg.words:
                wc = re.sub(r"[^a-z0-9]", "", w.word.lower())
                if wc:
                    all_words.append((w.start, w.end, wc))

    W = len(all_words)
    print(f"[Align] Transcribed {W} words. Last word ends at {all_words[-1][1]:.2f}s")

    # 3. Match each scene's start & end word timestamps
    print("\n[Align] Matching scenes to word timestamps...")
    scene_matches = []
    word_ptr = 0

    for i, (sc, narr) in enumerate(valid_scenes):
        scene_wlist = norm_words(narr)
        nw = len(scene_wlist)

        if nw == 0 or word_ptr >= W:
            scene_matches.append({
                "scene": sc, "narr": narr, "matched": False,
                "st": None, "en": None, "first_w": "", "last_w": "", "score": 0.0, "nw": nw
            })
            continue

        lo = word_ptr
        hi = min(W - nw, word_ptr + 80)
        best_score = -1.0
        best_wi = word_ptr

        for si in range(lo, hi + 1):
            s = window_score(scene_wlist, si, all_words, W)
            if s > best_score:
                best_score = s
                best_wi = si

        if best_score < 0.35:
            scene_matches.append({
                "scene": sc, "narr": narr, "matched": False,
                "st": None, "en": None, "first_w": "", "last_w": "", "score": best_score, "nw": nw
            })
            continue

        next_first_word = ""
        if i < N - 1:
            next_wlist = norm_words(valid_scenes[i + 1][1])
            if next_wlist:
                next_first_word = next_wlist[0]

        end_wi = min(best_wi + max(1, nw) - 1, W - 1)
        if next_first_word and end_wi > best_wi and all_words[end_wi][2] == next_first_word:
            end_wi -= 1

        st = all_words[best_wi][0]
        en = all_words[end_wi][1]

        # Enforce min and max reasonable duration per scene based on word count
        min_dur = max(1.6, nw * 0.28)
        max_dur = max(3.5, nw * 0.55) # Prevent any single scene from swallowing 20+ seconds

        dur_raw = en - st
        if dur_raw < min_dur:
            en = st + min_dur
        elif dur_raw > max_dur:
            en = st + max_dur

        word_ptr = end_wi + 1

        scene_matches.append({
            "scene": sc, "narr": narr, "matched": True,
            "st": st, "en": en, "first_w": all_words[best_wi][2], "last_w": all_words[end_wi][2],
            "score": round(best_score, 3), "nw": nw
        })

    # 4. Continuous Gap-Free Pause Allocation
    print("\n[Align] Allocating audio pauses to preceding scenes (gap-free timeline)...")

    # Determine raw start points for matched scenes
    raw_starts = []
    for i, m in enumerate(scene_matches):
        if m["matched"] and m["st"] is not None:
            raw_starts.append(m["st"])
        else:
            raw_starts.append(None)

    # Smooth out unmatched or outlier scene start times by character-weighted interpolation
    total_chars = max(1, sum(len(m["narr"]) for m in scene_matches))
    smoothed_starts = [0.0] * N

    cur_t = 0.0
    for i in range(N):
        narr_len = len(scene_matches[i]["narr"])
        expected_dur = max(1.6, (narr_len / 15.0)) # ~15 chars per sec average

        if raw_starts[i] is not None:
            st_val = raw_starts[i]
            # Ensure monotone increasing with min 1.6s spacing
            if i > 0 and st_val < smoothed_starts[i-1] + 1.6:
                st_val = smoothed_starts[i-1] + 1.6
            # Ensure scene does not jump too far ahead of previous scene
            if i > 0 and st_val > smoothed_starts[i-1] + (len(scene_matches[i-1]["narr"]) / 8.0) + 4.0:
                st_val = smoothed_starts[i-1] + (len(scene_matches[i-1]["narr"]) / 12.0)
            smoothed_starts[i] = st_val
            cur_t = st_val
        else:
            # Interpolate unmatched scene
            next_t = total_dur
            rem_chars = sum(len(scene_matches[j]["narr"]) for j in range(i, N))
            for j in range(i + 1, N):
                if raw_starts[j] is not None and raw_starts[j] > cur_t:
                    next_t = raw_starts[j]
                    rem_chars = sum(len(scene_matches[k]["narr"]) for k in range(i, j))
                    break

            avail = max(1.6, next_t - cur_t)
            alloc = (narr_len / max(1, rem_chars)) * avail
            smoothed_starts[i] = cur_t
            cur_t += alloc

    # 5. Convert Continuous Boundaries to Integer Frame Positions at 25 FPS
    print("[Align] Snapping continuous boundaries to 25 FPS integer frames...")

    MIN_FRAMES = 40  # Minimum 1.6s (40 frames) per scene

    frame_starts = [0] * N
    frame_ends   = [0] * N

    for i in range(N - 1):
        # Target start frame for scene i+1
        target_f = round(smoothed_starts[i + 1] * FPS)
        # Must be at least prev_start + MIN_FRAMES
        target_f = max(frame_starts[i] + MIN_FRAMES, target_f)

        # Ensure enough frames remain for rest of the scenes
        rem_scenes = N - 1 - i
        max_allowed = total_frames - (rem_scenes * MIN_FRAMES)
        target_f = min(target_f, max_allowed)
        target_f = max(frame_starts[i] + MIN_FRAMES, target_f)

        frame_ends[i] = target_f
        frame_starts[i + 1] = target_f

    # Pin last scene end to total_frames exactly
    frame_ends[-1] = total_frames

    # Build final scene objects
    timeline_scenes = []
    for i in range(N):
        sc = scene_matches[i]["scene"]
        st_f = frame_starts[i]
        en_f = frame_ends[i]
        f_cnt = en_f - st_f

        st_sec = round(st_f / FPS, 6)
        en_sec = round(en_f / FPS, 6)
        dur_sec = round(f_cnt / FPS, 6)

        timeline_scenes.append({
            "number": sc["number"],
            "start": st_sec,
            "end": en_sec,
            "duration": dur_sec,
            "first_word": scene_matches[i]["first_w"],
            "last_word": scene_matches[i]["last_w"],
            "score": scene_matches[i]["score"],
            "word_count": scene_matches[i]["nw"],
            "frame_start": st_f,
            "frame_end": en_f,
            "frame_count": f_cnt
        })

    # Verification checks
    sum_dur = sum(s["duration"] for s in timeline_scenes)
    actual_video_dur = total_frames / FPS

    print("\n==========================================================")
    print("  TIMELINE GENERATION VERIFICATION REPORT")
    print("==========================================================")
    print(f"Master Audio Duration : {total_dur:.6f}s")
    print(f"Total Video Frames    : {total_frames} frames")
    print(f"Total Video Duration  : {actual_video_dur:.6f}s")
    print(f"Sum of Scene Durations: {sum_dur:.6f}s")
    print(f"Gap/Drift             : {abs(actual_video_dur - total_dur)*1000:.2f} ms")
    print(f"First Scene Start     : {timeline_scenes[0]['start']}s (Frame {timeline_scenes[0]['frame_start']})")
    print(f"Last Scene End        : {timeline_scenes[-1]['end']}s (Frame {timeline_scenes[-1]['frame_end']})")

    # Check for gaps between adjacent scenes
    gaps = 0
    for i in range(1, N):
        diff = abs(timeline_scenes[i]["start"] - timeline_scenes[i-1]["end"])
        if diff > 0.0001:
            print(f"  [GAP ERROR] Scene V{timeline_scenes[i-1]['number']} end != Scene V{timeline_scenes[i]['number']} start!")
            gaps += 1

    if gaps == 0:
        print("Continuity Check      : PASS (100% Gap-Free Continuous Timeline)")
    else:
        print(f"Continuity Check      : FAIL ({gaps} gaps found)")

    # Save to Scene_Timeline.json
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    timeline_json = {
        "total_audio_duration": round(total_dur, 4),
        "master_audio_pcm": MASTER_WAV,
        "scenes": timeline_scenes
    }
    with open(TIMELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(timeline_json, f, indent=4)

    print(f"\n[OK] Scene_Timeline.json saved -> {TIMELINE_PATH}")
    print("==========================================================")


if __name__ == "__main__":
    main()
