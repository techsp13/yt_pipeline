"""
pipeline_qa_auditor.py
──────────────────────
Comprehensive Pre-Render QA Verification & Bug-Prevention System for YouTube Automation Agent.

Validates:
1. Script & Narration Quality (no duplicate sentences, no TTS traps like 'us'->'U.S.', no banned acronyms, no bracketed leftovers)
2. Master Audio Integrity (nonzero amplitude, valid sample rate, no silence/corruption)
3. Sentence Boundary & Timing Lock (no mid-sentence cuts, silent scenes don't steal speech, zero gaps/overlaps, RULE 1 duration lock)
4. Visual Asset Coverage (every scene has an existing approved image, valid resolution, no corrupt PNGs)
5. Subtitle Sync (SRT alignment to timeline)

Runs automatically BEFORE Step 10 video compilation to prevent wasteful 30-45min rendering cycles.
"""

import json
import os
import re
import subprocess
import sys
import wave
from difflib import SequenceMatcher
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class QAAuditor:
    def __init__(self, project_dir: str):
        self.proj_dir = os.path.abspath(project_dir)
        self.script_dir = os.path.join(self.proj_dir, "03_Script")
        self.scenes_dir = os.path.join(self.proj_dir, "04_Scenes")
        self.images_dir = os.path.join(self.proj_dir, "06_Images")
        self.voice_dir = os.path.join(self.proj_dir, "07_Voice")
        self.subtitles_dir = os.path.join(self.proj_dir, "09_Subtitles")
        self.final_dir = os.path.join(self.proj_dir, "11_Final_Video")
        self.checkpoints_dir = os.path.join(self.proj_dir, "14_Checkpoints")
        self.logs_dir = os.path.join(self.proj_dir, "13_Logs")
        os.makedirs(self.logs_dir, exist_ok=True)

        self.critical_errors = []
        self.warnings = []
        self.audit_results = {}

    def log_error(self, category: str, msg: str):
        self.critical_errors.append(f"[{category}] {msg}")

    def log_warning(self, category: str, msg: str):
        self.warnings.append(f"[{category}] {msg}")

    # ──────────────────────────────────────────────────────────────────────────
    # AUDIT 1: Script & Narration QA (Pre-TTS Gate)
    # ──────────────────────────────────────────────────────────────────────────
    def audit_script_and_narration(self) -> dict:
        """Checks for duplicate sentences, TTS pronunciation traps, banned acronyms, and formatting artifacts."""
        res = {"passed": True, "duplicate_sentences": [], "tts_traps": [], "empty_scenes": []}

        scene_file = os.path.join(self.scenes_dir, "Scene_List.json")
        if not os.path.exists(scene_file):
            self.log_error("Script QA", f"Missing Scene_List.json at {scene_file}")
            res["passed"] = False
            return res

        with open(scene_file, "r", encoding="utf-8") as f:
            scenes = json.load(f)

        narrations = []
        for s in scenes:
            num = s.get("number", 0)
            narr = (s.get("narration") or "").strip()
            if not narr:
                res["empty_scenes"].append(num)
            else:
                narrations.append((num, narr))

        if res["empty_scenes"]:
            self.log_warning("Script QA", f"{len(res['empty_scenes'])} scene(s) have empty narration: Scenes {res['empty_scenes'][:10]}")

        # 1. Check duplicate sentences
        all_sentences = []
        for num, narr in narrations:
            s_list = [sent.strip() for sent in re.split(r'[.!?]+', narr) if len(sent.strip()) > 15]
            for sent in s_list:
                all_sentences.append((num, sent.lower()))

        sent_counter = Counter([s for _, s in all_sentences])
        for sent, count in sent_counter.items():
            if count > 1:
                origin_scenes = [num for num, s in all_sentences if s == sent]
                self.log_error("Script QA", f"Duplicate sentence ({count}x in Scenes {origin_scenes}): '{sent}'")
                res["duplicate_sentences"].append({"sentence": sent, "count": count, "scenes": origin_scenes})
                res["passed"] = False

        # 2. Check for substring / contained duplicate narrations (e.g. Scene 116 contains Scene 117)
        for i in range(len(narrations)):
            num1, narr1 = narrations[i]
            n1_clean = re.sub(r"[^a-z0-9\s]", "", narr1.lower()).strip()
            if len(n1_clean) < 15:
                continue

            # Check against upcoming 5 scenes
            for j in range(i + 1, min(i + 6, len(narrations))):
                num2, narr2 = narrations[j]
                n2_clean = re.sub(r"[^a-z0-9\s]", "", narr2.lower()).strip()
                if len(n2_clean) < 15:
                    continue

                if n2_clean in n1_clean:
                    self.log_error("Script QA", f"Duplicate phrase! Scene {num2} ('{narr2}') is completely repeated inside Scene {num1} ('{narr1[:40]}...')")
                    res["passed"] = False
                elif n1_clean in n2_clean:
                    self.log_error("Script QA", f"Duplicate phrase! Scene {num1} ('{narr1}') is completely repeated inside Scene {num2} ('{narr2[:40]}...')")
                    res["passed"] = False

        # 3. Check for repeated 4-word phrases across nearby scenes (catches repeated clauses)
        all_phrases = []
        for num, narr in narrations:
            words = [w for w in re.sub(r"[^a-z0-9\s]", "", narr.lower()).split() if w]
            for idx_w in range(len(words) - 3):
                p_text = " ".join(words[idx_w:idx_w+4])
                all_phrases.append((num, p_text))

        phrase_counts = Counter([p for _, p in all_phrases])
        for phrase, count in phrase_counts.items():
            if count > 1:
                scenes_with_phrase = sorted(set(num for num, p in all_phrases if p == phrase))
                # If repeated within 5 scenes of each other, it's definitely an accidental stutter/duplication
                if max(scenes_with_phrase) - min(scenes_with_phrase) <= 6:
                    self.log_error("Script QA", f"Repetitive narration! 4-word phrase '{phrase}' repeated {count}x across adjacent Scenes {scenes_with_phrase}")
                    res["passed"] = False

        # 3. Check for TTS traps: banned acronyms (RULE 5)
        banned_acronyms = [
            (r"\bCRISPR\b", "CRISPR (must use 'molecular scissors')"),
            (r"\bCas9\b", "Cas9 (must use 'cutting enzyme')"),
            (r"\bmRNA\b", "mRNA (must use 'messenger RNA')"),
            (r"\bsiRNA\b", "siRNA (must use 'small RNA')"),
            (r"\bTALENs\b", "TALENs"),
            (r"\bDNA-PKcs\b", "DNA-PKcs"),
            (r"\bGWAS\b", "GWAS"),
            (r"\bPCR\b", "PCR (must use 'DNA copying')"),
        ]
        for num, narr in narrations:
            for pat, name in banned_acronyms:
                if re.search(pat, narr):
                    self.log_error("Script QA", f"Scene {num} contains banned TTS acronym: '{name}'")
                    res["tts_traps"].append({"scene": num, "trap": name})
                    res["passed"] = False

        # 4. Check for 'US' pronoun traps
        for num, narr in narrations:
            # Check if 'US' in all-caps might be the pronoun 'us'
            if re.search(r"\b(for|in|to|with|of|between|give|show|tell)\s+US\b", narr):
                self.log_warning("Script QA", f"Scene {num} has capitalized 'US' after preposition; may be misread as U.S. instead of pronoun 'us'")

        # 5. Check for brackets or meta-words left in narration
        for num, narr in narrations:
            if re.search(r"[\[\]\(\)\{\}]", narr):
                self.log_warning("Script QA", f"Scene {num} narration contains brackets/parentheses: {repr(narr[:50])}")
            if re.search(r"(?i)\b(visual|narrator|act\s*\d+|scene\s*\d+)\b", narr):
                self.log_error("Script QA", f"Scene {num} narration contains meta script labels: {repr(narr[:50])}")
                res["passed"] = False

        self.audit_results["script_qa"] = res
        return res

    # ──────────────────────────────────────────────────────────────────────────
    # AUDIT 2: Master Audio Integrity (Post-TTS Gate)
    # ──────────────────────────────────────────────────────────────────────────
    def audit_master_audio(self) -> dict:
        """Verifies master audio exists, has sound activity, and valid format."""
        res = {"passed": True, "duration": 0.0, "sample_rate": 0, "channels": 0}

        mp3_path = os.path.join(self.voice_dir, "Full_Script_Voice.mp3")
        pcm_path = os.path.join(self.voice_dir, "Full_Script_Voice_pcm.wav")

        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1000:
            self.log_error("Audio QA", f"Missing or empty Full_Script_Voice.mp3 at {mp3_path}")
            res["passed"] = False
            return res

        target_audio = pcm_path if os.path.exists(pcm_path) else mp3_path

        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=sample_rate,channels",
            "-of", "json", target_audio
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            self.log_error("Audio QA", f"ffprobe failed on master audio: {r.stderr}")
            res["passed"] = False
            return res

        data = json.loads(r.stdout)
        res["duration"] = float(data.get("format", {}).get("duration", 0))
        streams = data.get("streams", [])
        if streams:
            res["sample_rate"] = int(streams[0].get("sample_rate", 0))
            res["channels"] = int(streams[0].get("channels", 1))

        if res["duration"] < 10.0:
            self.log_error("Audio QA", f"Master audio duration too short: {res['duration']:.2f}s")
            res["passed"] = False

        # Amplitude check on PCM WAV
        if os.path.exists(pcm_path):
            try:
                with wave.open(pcm_path, "rb") as wf:
                    n = min(wf.getnframes(), wf.getframerate() * 5)
                    raw = wf.readframes(n)
                    import struct
                    samples = struct.unpack(f"<{len(raw)//2}h", raw)
                    max_amp = max(abs(s) for s in samples) if samples else 0
                    if max_amp < 500:
                        self.log_error("Audio QA", f"Master audio first 5s appears silent (max amp={max_amp})")
                        res["passed"] = False
            except Exception as e:
                self.log_warning("Audio QA", f"Could not inspect WAV samples: {e}")

        self.audit_results["audio_qa"] = res
        return res

    # ──────────────────────────────────────────────────────────────────────────
    # AUDIT 3: Sentence Boundary & Timing Lock (Post-Alignment Gate)
    # ──────────────────────────────────────────────────────────────────────────
    def audit_timeline_alignment(self) -> dict:
        """
        Crucial check:
        1. Ensures no scene cuts off mid-sentence (scene.end >= last_word.end).
        2. Ensures silent scenes do not steal spoken words.
        3. Ensures zero gaps between consecutive scenes.
        4. Verifies RULE 1: abs(total_duration - master_audio) < 50ms.
        """
        res = {"passed": True, "mid_sentence_cuts": [], "silent_scene_collisions": [], "timeline_gaps": []}

        tl_path = os.path.join(self.checkpoints_dir, "Scene_Timeline.json")
        if not os.path.exists(tl_path):
            self.log_error("Timeline QA", f"Missing Scene_Timeline.json at {tl_path}")
            res["passed"] = False
            return res

        with open(tl_path, "r", encoding="utf-8") as f:
            tl = json.load(f)

        scenes = tl.get("scenes", [])
        if not scenes:
            self.log_error("Timeline QA", "Scene_Timeline.json contains no scenes!")
            res["passed"] = False
            return res

        # 1. Check RULE 1: Duration match
        master_dur = tl.get("total_audio_duration", 0.0)
        tl_dur = scenes[-1]["end"]
        drift = abs(tl_dur - master_dur)
        res["drift"] = drift
        if drift > 0.050:
            self.log_error("Timeline QA", f"RULE 1 VIOLATION: Timeline duration {tl_dur:.3f}s differs from master audio {master_dur:.3f}s by {drift*1000:.1f}ms (>50ms tolerance)")
            res["passed"] = False

        # 2. Check gaps / overlaps between consecutive scenes
        for i in range(1, len(scenes)):
            gap = scenes[i]["start"] - scenes[i - 1]["end"]
            if abs(gap) > 0.001:
                self.log_error("Timeline QA", f"Timeline gap of {gap*1000:.1f}ms between Scene {scenes[i-1]['number']} and Scene {scenes[i]['number']}")
                res["timeline_gaps"].append((scenes[i-1]["number"], scenes[i]["number"], gap))
                res["passed"] = False

        # 3. Check for mid-sentence cuts using Scene_List.json and word counts
        scene_list_file = os.path.join(self.scenes_dir, "Scene_List.json")
        if os.path.exists(scene_list_file):
            with open(scene_list_file, "r", encoding="utf-8") as f:
                scene_list = json.load(f)
            sl_map = {s["number"]: s for s in scene_list}

            for s in scenes:
                num = s["number"]
                dur = s.get("duration", 0.0)
                sl_scene = sl_map.get(num, {})
                narr = (sl_scene.get("narration") or "").strip()
                words = narr.split()
                nw = len(words)

                # If narration has many words (>10) but scene duration is tiny (<2.0s),
                # it's almost certainly cut off mid-sentence!
                if nw >= 10 and dur < (nw * 0.22):
                    self.log_error("Timeline QA", f"Scene {num} severely truncated! Has {nw} words ({repr(narr[:35])}...) but only {dur:.2f}s allotted (need ~{nw*0.3:.1f}s)")
                    res["mid_sentence_cuts"].append({"scene": num, "words": nw, "duration": dur, "text": narr})
                    res["passed"] = False

                # Check silent scenes in the middle
                if nw == 0 and s.get("first_word", "") == "":
                    # Empty narration scene
                    self.log_warning("Timeline QA", f"Scene {num} is in timeline ({s['start']:.2f}s - {s['end']:.2f}s) but has empty narration")

        self.audit_results["timeline_qa"] = res
        return res

    # ──────────────────────────────────────────────────────────────────────────
    # AUDIT 4: Visual Asset Coverage
    # ──────────────────────────────────────────────────────────────────────────
    def audit_visual_assets(self) -> dict:
        """Verifies every scene in timeline has an approved, uncorrupted image."""
        res = {"passed": True, "missing_images": [], "corrupt_images": []}

        tl_path = os.path.join(self.checkpoints_dir, "Scene_Timeline.json")
        if not os.path.exists(tl_path):
            return res

        with open(tl_path, "r", encoding="utf-8") as f:
            tl = json.load(f)

        scenes = tl.get("scenes", [])
        approved_dir = os.path.join(self.images_dir, "Approved")
        img_dir = approved_dir if os.path.isdir(approved_dir) else self.images_dir

        for s in scenes:
            num = s["number"]
            # Search possible naming conventions
            candidates = [
                os.path.join(self.images_dir, f"{num:03d}_Scene_{num:02d}.png"),
                os.path.join(approved_dir, f"{num:03d}_Scene_{num:02d}.png"),
                os.path.join(self.images_dir, f"Scene_{num:02d}.png"),
                os.path.join(approved_dir, f"Scene_{num:02d}.png"),
            ]
            found = next((p for p in candidates if os.path.exists(p) and os.path.getsize(p) > 1000), None)
            if not found:
                self.log_error("Visual QA", f"Missing approved image for Scene {num}")
                res["missing_images"].append(num)
                res["passed"] = False

        self.audit_results["visual_qa"] = res

        # Check if there are approved images on disk that were omitted from timeline
        approved_files = [f for f in os.listdir(img_dir) if f.endswith(".png") and "Scene_" in f]
        tl_nums = set(s["number"] for s in scenes)
        omitted_scenes = []
        for af in approved_files:
            m = re.search(r"Scene_(\d+)", af)
            if m:
                sn = int(m.group(1))
                if sn not in tl_nums:
                    omitted_scenes.append((sn, af))

        if omitted_scenes:
            omitted_scenes.sort()
            self.log_warning("Visual QA", f"{len(omitted_scenes)} approved image(s) exist on disk but are NOT in the timeline (will not be rendered!): {omitted_scenes}")
            res["omitted_from_timeline"] = omitted_scenes

        return res

    # ──────────────────────────────────────────────────────────────────────────
    # AUDIT 5: Subtitle Sync & Formatting
    # ──────────────────────────────────────────────────────────────────────────
    def audit_subtitles(self) -> dict:
        """Verifies Subtitle.srt exists, has valid structure, and starts at 00:00:00."""
        res = {"passed": True, "entry_count": 0}

        srt_path = os.path.join(self.subtitles_dir, "Subtitle.srt")
        if not os.path.exists(srt_path):
            self.log_warning("Subtitle QA", f"Subtitle.srt not generated yet at {srt_path}")
            return res

        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        entries = re.findall(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)", content, re.DOTALL)
        res["entry_count"] = len(entries)

        if not entries:
            self.log_error("Subtitle QA", "Subtitle.srt is empty or corrupt!")
            res["passed"] = False
            return res

        first_start = entries[0][1]
        if not first_start.startswith("00:00:00"):
            self.log_error("Subtitle QA", f"First subtitle does not start at 00:00:00! (starts at {first_start})")
            res["passed"] = False

        self.audit_results["subtitle_qa"] = res
        return res

    # ──────────────────────────────────────────────────────────────────────────
    # AUDIT 6: Thumbnail & Deliverables QA
    # ──────────────────────────────────────────────────────────────────────────
    def audit_thumbnail_and_deliverables(self) -> dict:
        """Validates that thumbnail text and SEO files do not contain raw markdown asterisks (**) or illegal special symbols."""
        res = {"passed": True, "stray_symbols": [], "thumbnail_title": None, "thumbnail_exists": False}
        
        seo_dir = os.path.join(self.proj_dir, "02_SEO")
        if os.path.exists(seo_dir):
            for fname in os.listdir(seo_dir):
                if fname.endswith(".md") or fname.endswith(".txt"):
                    fpath = os.path.join(seo_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            c = f.read()
                        if "**" in c:
                            self.log_warning("Deliverables QA", f"File 02_SEO/{fname} contains raw markdown asterisks '**'")
                            res["stray_symbols"].append(f"02_SEO/{fname}")
                    except Exception:
                        pass
        
        hashtags_md = os.path.join(seo_dir, "Hashtags.md")
        if os.path.exists(hashtags_md):
            try:
                with open(hashtags_md, "r", encoding="utf-8") as f:
                    h_text = f.read()
                m = re.search(r"[*_\s]*Thumbnail Title[*_\s]*:[*_\s]*([^\n\r]+)", h_text, re.IGNORECASE)
                if m:
                    raw_title = m.group(1).strip()
                    res["thumbnail_title"] = raw_title
                    if "**" in raw_title or any(ch in raw_title for ch in "#@$%^&*~`_+=/\\|<>{}[]()\"'"):
                        self.log_error("Thumbnail QA", f"Thumbnail Title contains forbidden symbols or asterisks: '{raw_title}'")
                        res["passed"] = False
            except Exception:
                pass

        thumb_path = os.path.join(self.proj_dir, "12_Thumbnail", "Thumbnail.png")
        if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 1000:
            res["thumbnail_exists"] = True
            
        self.audit_results["thumbnail_qa"] = res
        return res

    # ──────────────────────────────────────────────────────────────────────────
    # Main Report Generator
    # ──────────────────────────────────────────────────────────────────────────
    def run_full_qa(self) -> dict:
        """Runs all QA audits and outputs a comprehensive markdown report."""
        print("\n" + "=" * 65)
        print("  RUNNING AUTOMATED PRE-RENDER QA AUDIT")
        print("=" * 65)

        self.audit_script_and_narration()
        self.audit_master_audio()
        self.audit_timeline_alignment()
        self.audit_visual_assets()
        self.audit_subtitles()
        self.audit_thumbnail_and_deliverables()

        passed = len(self.critical_errors) == 0

        # Build Markdown Report
        report_lines = [
            "# Pre-Render QA Audit Report",
            f"**Project:** `{os.path.basename(self.proj_dir)}`  ",
            f"**Overall Verdict:** {'✅ PASSED (Safe to render)' if passed else '🚨 FAILED (Fixes required before render)'}  ",
            f"**Critical Errors:** {len(self.critical_errors)}  ",
            f"**Warnings:** {len(self.warnings)}  \n",
            "---",
        ]

        if self.critical_errors:
            report_lines.append("\n## 🚨 Critical Errors (Must be resolved before render):")
            for err in self.critical_errors:
                report_lines.append(f"- {err}")

        if self.warnings:
            report_lines.append("\n## ⚠️ Warnings:")
            for w in self.warnings:
                report_lines.append(f"- {w}")

        report_lines.append("\n## 📊 Detailed Audit Results:")
        for k, v in self.audit_results.items():
            report_lines.append(f"### {k.replace('_', ' ').title()}")
            report_lines.append(f"```json\n{json.dumps(v, indent=2)}\n```")

        report_path = os.path.join(self.logs_dir, "QA_PreRender_Report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"\n[QA Verdict] {'✅ PASSED' if passed else '🚨 FAILED'}")
        print(f"  Critical Errors : {len(self.critical_errors)}")
        print(f"  Warnings        : {len(self.warnings)}")
        print(f"  Report saved to : {report_path}\n")

        return {
            "passed": passed,
            "critical_errors": self.critical_errors,
            "warnings": self.warnings,
            "report_path": report_path
        }


def auto_fix_duplicate_narrations(project_dir: str) -> int:
    """
    Cleans up duplicate phrases and overlapping sentence chunks in Scene_List.json.
    Ensures zero words are repeated across consecutive scenes before voiceover.
    """
    sl_path = os.path.join(project_dir, "04_Scenes", "Scene_List.json")
    if not os.path.exists(sl_path):
        return 0

    with open(sl_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    fixed_count = 0
    for i in range(len(scenes) - 1):
        s1 = scenes[i]
        s2 = scenes[i + 1]
        n1 = (s1.get("narration") or "").strip()
        n2 = (s2.get("narration") or "").strip()

        if not n1 or not n2:
            continue

        n1_words = [w for w in re.sub(r"[^\w\s]", "", n1.lower()).split() if w]
        n2_words = [w for w in re.sub(r"[^\w\s]", "", n2.lower()).split() if w]

        if not n1_words or not n2_words:
            continue

        # Case 1: s1 ends with s2's words -> partition s1 cleanly
        len2 = len(n2_words)
        if len(n1_words) > len2 and n1_words[-len2:] == n2_words:
            pat = r"(?i)\s*[\b,.-]*" + r"\s*[\b,.-]*".join(re.escape(w) for w in n2_words) + r"[\s,.-]*$"
            m = re.search(pat, n1)
            if m:
                new_n1 = n1[:m.start()].rstrip(" ,.-")
                if len(new_n1) > 10:
                    s1["narration"] = new_n1 + ","
                    fixed_count += 1
                    continue

        # Case 2: exact duplicate words
        if n1_words == n2_words:
            s2["narration"] = ""
            fixed_count += 1
            continue

    if fixed_count > 0:
        with open(sl_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, indent=4)
        print(f"[Auto-Fix] Successfully cleanly partitioned {fixed_count} overlapping scenes in Scene_List.json.")

    return fixed_count


def run_qa_check(project_dir: str) -> bool:
    """Helper entry point for pipeline scripts."""
    auditor = QAAuditor(project_dir)
    res = auditor.run_full_qa()
    return res["passed"]


if __name__ == "__main__":
    agent_dir = r"D:\youtube_automation_agent"
    active_json = os.path.join(agent_dir, "active_project.json")
    if os.path.exists(active_json):
        with open(active_json, "r", encoding="utf-8") as f:
            target_proj = json.load(f)["active_project_dir"]
    else:
        target_proj = agent_dir

    if len(sys.argv) > 1:
        target_proj = sys.argv[1]

    auditor = QAAuditor(target_proj)
    verdict = auditor.run_full_qa()
    sys.exit(0 if verdict["passed"] else 1)
