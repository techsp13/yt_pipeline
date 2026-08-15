import os
import re
import sys
import subprocess

proj_dir = r"D:\youtube_automation_agent\channels\science\NASAs_Twin_Study_2026-07-25_230010"
breakdown_path = os.path.join(proj_dir, "04_Scenes", "Scene_Breakdown.md")

# 1. Read breakdown file
with open(breakdown_path, "r", encoding="utf-8") as f:
    content = f.read()

# 2. Update V228 narration
target = '**Narration:** "question:"'
replacement = '**Narration:** "question that lies at the heart of human spaceflight."'

if target in content:
    content = content.replace(target, replacement)
    with open(breakdown_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("[SUCCESS] Updated Scene V228 Narration in Scene_Breakdown.md!")
else:
    print("[INFO] Target narration already updated.")

# 3. Regenerate Scene_228_Voice.mp3 using voiceover module
audio_path = os.path.join(proj_dir, "07_Voice", "Scene_228_Voice.mp3")
if os.path.exists(audio_path):
    try:
        os.remove(audio_path)
    except Exception:
        pass

print("[TTS] Regenerating Scene 228 Voiceover in reference voice...")
import voiceover
voiceover.generate_speech("question that lies at the heart of human spaceflight.", audio_path)
print("[SUCCESS] Voiceover generated:", audio_path)
