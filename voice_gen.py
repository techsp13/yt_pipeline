import asyncio
import os
import edge_tts

# ─── Available voices with emotion/style feel ──────────────────────────────
# These are Microsoft Neural voices — very natural, human sounding, 100% free
VOICES = {
    # English — Storytelling / Documentary feel
    "narrator_male":    "en-US-AndrewNeural",       # Deep, warm, confident male
    "narrator_female":  "en-US-JennyNeural",         # Clear, friendly female
    "dramatic_male":    "en-US-GuyNeural",           # Expressive, dramatic male
    "excited_female":   "en-US-AriaNeural",          # Bright, energetic female
    "calm_male":        "en-US-ChristopherNeural",   # Calm, authoritative
    "young_male":       "en-US-EricNeural",          # Young, casual narrator
    "storyteller":      "en-GB-RyanNeural",          # British, warm storyteller
    # Hindi — for Indian content
    "hindi_male":       "hi-IN-MadhurNeural",
    "hindi_female":     "hi-IN-SwaraNeural",
}

# ─── SSML emotion templates ────────────────────────────────────────────────
# SSML (Speech Synthesis Markup Language) lets us control rate, pitch, volume
# to simulate different emotional tones even without explicit style support

def build_ssml(text: str, voice: str, emotion: str = "neutral") -> str:
    """
    Builds SSML markup that adjusts rate, pitch, and emphasis
    to simulate emotional narration styles.
    """
    emotion_map = {
        # (rate, pitch, volume)
        "neutral":   ("medium",  "medium", "medium"),
        "excited":   ("+15%",    "+10%",   "+5%"),
        "sad":       ("-20%",    "-8%",    "-5%"),
        "dramatic":  ("-10%",    "-4%",    "+8%"),
        "curious":   ("+5%",     "+5%",    "medium"),
        "serious":   ("-5%",     "-2%",    "+3%"),
        "warm":      ("-8%",     "medium", "medium"),
    }

    rate, pitch, volume = emotion_map.get(emotion, emotion_map["neutral"])

    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'
    xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
    <voice name='{voice}'>
        <prosody rate='{rate}' pitch='{pitch}' volume='{volume}'>
            {text}
        </prosody>
    </voice>
</speak>"""
    return ssml


async def generate_voice_async(
    text: str,
    output_path: str,
    voice_key: str = "narrator_male",
    emotion: str = "neutral"
):
    """
    Generates speech using Microsoft Edge Neural TTS.
    - voice_key: one of VOICES dict keys
    - emotion: neutral | excited | sad | dramatic | curious | serious | warm
    """
    voice = VOICES.get(voice_key, VOICES["narrator_male"])
    ssml  = build_ssml(text, voice, emotion)

    print(f"Generating voice: {voice_key} ({voice}), emotion: {emotion}")
    print(f"Text: \"{text}\"")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    communicate = edge_tts.Communicate(text=ssml, voice=voice)
    await communicate.save(output_path)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Saved to: {output_path} ({size_kb:.1f} KB)")


def generate_voice(
    text: str,
    output_path: str,
    voice_key: str = "narrator_male",
    emotion: str = "neutral"
):
    """Synchronous wrapper for generate_voice_async."""
    asyncio.run(generate_voice_async(text, output_path, voice_key, emotion))


# ─── Test: generate 3 emotions of the same line ───────────────────────────
if __name__ == "__main__":
    os.makedirs(r"C:\Users\ASUS\kokoro\voice_test", exist_ok=True)

    test_cases = [
        {
            "text": "Are we actually aliens on our own planet? The answer might surprise you.",
            "voice_key": "narrator_male",
            "emotion": "dramatic",
            "output": r"C:\Users\ASUS\kokoro\voice_test\dramatic.mp3"
        },
        {
            "text": "Around one million years ago, our ancestors learned to sit around campfires.",
            "voice_key": "storyteller",
            "emotion": "warm",
            "output": r"C:\Users\ASUS\kokoro\voice_test\warm.mp3"
        },
        {
            "text": "Our jaws shrank, our teeth got smaller, and our digestive system became tiny.",
            "voice_key": "calm_male",
            "emotion": "serious",
            "output": r"C:\Users\ASUS\kokoro\voice_test\serious.mp3"
        },
    ]

    for case in test_cases:
        generate_voice(
            text=case["text"],
            output_path=case["output"],
            voice_key=case["voice_key"],
            emotion=case["emotion"]
        )
        print()

    print("All voice samples generated!")
    print(f"Listen to them at: C:\\Users\\ASUS\\kokoro\\voice_test\\")
