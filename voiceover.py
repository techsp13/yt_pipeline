import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Cartesia Credentials & Config
# NOTE: API keys are loaded ONLY from the environment (.env) — never commit credentials to source.
# Multiple keys can be supplied as a comma-separated CARTESIA_API_KEY for rotation.
KNOWN_CARTESIA_KEYS = []
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
DEFAULT_VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "79f8b5fb-2cc8-479a-80df-29f7a7cf1a3e")
DEFAULT_REFERENCE = os.path.join(os.path.dirname(__file__), "reference_voice.wav")


def get_all_cartesia_keys():
    """Returns deduplicated list of all available Cartesia API keys for rotation."""
    keys = []
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as ef:
            for line in ef:
                if line.strip().startswith("CARTESIA_API_KEY="):
                    val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    if val and val not in keys:
                        keys.append(val)
    for k in KNOWN_CARTESIA_KEYS:
        if k not in keys:
            keys.append(k)
    env_k = os.getenv("CARTESIA_API_KEY")
    if env_k and env_k not in keys:
        keys.append(env_k)
    return [k for k in keys if k.startswith("sk_car_")]


def notify_key_expired(error_msg):
    """Sends immediate alert to Telegram if Cartesia API key is expired or out of credits."""
    try:
        import telegram_bot
        telegram_bot.send_message(
            f"🚨 *CARTESIA API KEY EXPIRED / OUT OF CREDITS!*\n\n"
            f"The active key has run out of credits or expired.\n"
            f"*Error Details:* `{error_msg[:200]}`\n\n"
            f"👉 Please reply with your new Cartesia API key to continue!"
        )
    except Exception as e:
        print(f"[Cartesia Alert Error]: {e}")


def clone_voice_cartesia(reference_wav=DEFAULT_REFERENCE, api_key=None):
    """
    Auto-clones a voice from reference WAV audio file on Cartesia AI.
    Returns the newly minted voice ID string, or None if cloning fails.
    """
    key = api_key or os.getenv("CARTESIA_API_KEY", CARTESIA_API_KEY)
    if not os.path.exists(reference_wav):
        print(f"[Cartesia Auto-Clone Error] Reference audio file not found: {reference_wav}")
        return None

    url = "https://api.cartesia.ai/voices/clone/file"
    headers = {
        "Cartesia-Version": "2026-03-01",
        "X-API-Key": key
    }
    try:
        print(f"[Cartesia Auto-Clone] Cloning reference audio from {reference_wav}...")
        with open(reference_wav, "rb") as f:
            files = {"clip": (os.path.basename(reference_wav), f, "audio/wav")}
            data = {"name": "Auto-Cloned Narrator Voice", "description": "Auto-cloned narrator voice"}
            res = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            if res.status_code in [200, 201]:
                vid = res.json().get("id")
                if vid:
                    print(f"[Cartesia Auto-Clone SUCCESS] Minted new Voice ID: {vid}")
                    # Update .env
                    env_file = os.path.join(os.path.dirname(__file__), ".env")
                    env_lines = []
                    if os.path.exists(env_file):
                        with open(env_file, "r", encoding="utf-8") as ef:
                            env_lines = ef.readlines()
                    new_lines = []
                    updated = False
                    for line in env_lines:
                        if line.strip().startswith("CARTESIA_VOICE_ID="):
                            new_lines.append(f"CARTESIA_VOICE_ID={vid}\n")
                            updated = True
                        else:
                            new_lines.append(line)
                    if not updated:
                        new_lines.append(f"\nCARTESIA_VOICE_ID={vid}\n")
                    with open(env_file, "w", encoding="utf-8") as ef:
                        ef.writelines(new_lines)
                    os.environ["CARTESIA_VOICE_ID"] = vid
                    global DEFAULT_VOICE_ID
                    DEFAULT_VOICE_ID = vid
                    return vid
            print(f"[Cartesia Auto-Clone Error] HTTP {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Cartesia Auto-Clone Exception]: {e}")
    return None


import re

def clean_tts_transcript(text):
    if not text:
        return ""
    text = re.sub(r"(?i)\bACT\s*\d+[^:\n]*[:\s\-]*(?:[^\n]*)", "", text)
    text = re.sub(r"(?i)\bSCENE\s*\d+[^:\n]*[:\s\-]*(?:[^\n]*)", "", text)
    text = re.sub(r"(?i)\bNARRATOR\b\s*[:\s]*", "", text)
    text = re.sub(r"(?i)\bFACT-CHECK NOTE\b[^\n]*", "", text)
    text = re.sub(r"(?i)\bVisual\b\s*[:\s]*", "", text)
    text = re.sub(r"^#+\s+[^\n]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[\(\[\{](?:Visual|Narrator|Scene|Note|Camera|Animation)[^\)\]\}]*[\)\]\}]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\([^\)]*\)", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    meta_pattern = r"\b(stick\s*figures?|stickfigures?|doodles?|illustrations?|on-screen|on screen|narrators?|animations?|drawings?|act\s*\d+|scene\s*\d+)\b"
    text = re.sub(meta_pattern, "", text, flags=re.IGNORECASE)
    text = text.replace('"', '').replace('*', '').strip()
    text = re.sub(r"\s+", " ", text)
    return text



def generate_speech_cartesia(text, output_path, voice_id=DEFAULT_VOICE_ID, api_key=None, retry_clone_on_missing=True):
    """
    Generates high-speed, high-quality audio using Cartesia AI API with automatic key rotation.
    """
    text = clean_tts_transcript(text)
    if not text or len(text) < 2:
        return False  # Empty narration → no audio; do not speak placeholder text

    keys_to_try = [api_key] if api_key else get_all_cartesia_keys()
    if not keys_to_try:
        print("[Cartesia TTS] ERROR: No CARTESIA_API_KEY configured!")
        notify_key_expired("No API key configured")
        return False

    last_error = ""

    for idx, key in enumerate(keys_to_try, 1):
        target_vid = voice_id or os.getenv("CARTESIA_VOICE_ID", DEFAULT_VOICE_ID)
        url = "https://api.cartesia.ai/tts/bytes"
        container_format = "mp3" if output_path.endswith(".mp3") else "wav"
        
        headers = {
            "Cartesia-Version": "2026-03-01",
            "X-API-Key": key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model_id": "sonic-3.5",
            "transcript": text,
            "language": "en",
            "voice": {
                "mode": "id",
                "id": target_vid
            },
            "output_format": {
                "container": container_format,
                "sample_rate": 44100
            },
            "generation_config": {
                "speed": 1.0,
                "volume": 1.0,
                "emotion": "curious"   # consistent narrator tone across all scenes
            }
        }
        
        if container_format == "mp3":
            payload["output_format"]["bit_rate"] = 128000
        else:
            payload["output_format"]["encoding"] = "pcm_s16le"

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(res.content)
                size_kb = os.path.getsize(output_path) / 1024
                print(f"[Cartesia TTS] Saved using Key #{idx}: {output_path} ({size_kb:.1f} KB)")
                return True

            # Check if Voice ID is missing or invalid in this new account (400/404)
            if retry_clone_on_missing and res.status_code in [400, 404] and any(kw in res.text.lower() for kw in ["voice", "not found", "invalid"]):
                print(f"[Cartesia TTS] Voice ID '{target_vid}' not found in Key #{idx}. Auto-cloning voice...")
                new_vid = clone_voice_cartesia(api_key=key)
                if new_vid:
                    return generate_speech_cartesia(text, output_path, voice_id=new_vid, api_key=key, retry_clone_on_missing=False)

            # Check if key is expired, unauthorized, or quota exceeded -> Rotate key!
            if res.status_code in [401, 402, 403, 429]:
                last_error = f"Key #{idx} ({key[:10]}...) HTTP {res.status_code}: {res.text[:150]}"
                print(f"⚠️ [Cartesia Key #{idx} Expired/Quota Limit]: {last_error}")
                if idx < len(keys_to_try):
                    print(f"🔄 Rotating to next Cartesia key ({idx+1}/{len(keys_to_try)})...")
                continue

            # Fallback to sonic-2 model if sonic-3.5 returned temporary error
            print(f"[Cartesia TTS] Warning: Key #{idx} sonic-3.5 returned {res.status_code}. Retrying sonic-2...")
            headers["Cartesia-Version"] = "2024-06-10"
            payload["model_id"] = "sonic-2"
            res2 = requests.post(url, headers=headers, json=payload, timeout=20)
            if res2.status_code == 200:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(res2.content)
                size_kb = os.path.getsize(output_path) / 1024
                print(f"[Cartesia TTS] Saved using Key #{idx}: {output_path} ({size_kb:.1f} KB)")
                return True
            elif res2.status_code in [401, 402, 403, 429]:
                last_error = f"Key #{idx} HTTP {res2.status_code}: {res2.text[:150]}"
                print(f"⚠️ [Cartesia Key #{idx} Expired/Quota Limit]: {last_error}")
                if idx < len(keys_to_try):
                    print(f"🔄 Rotating to next Cartesia key ({idx+1}/{len(keys_to_try)})...")
                continue

        except Exception as e:
            print(f"[Cartesia TTS] Exception with Key #{idx}: {e}")
            last_error = str(e)
            continue

    # If all keys failed, notify Telegram
    print("🚨 [Cartesia TTS] ALL keys in rotation pool expired or failed!")
    notify_key_expired(last_error or "All Cartesia keys in rotation pool exhausted")
    return False



def generate_speech(text, output_path, voice_id=DEFAULT_VOICE_ID, reference_wav=DEFAULT_REFERENCE, **kwargs):
    """
    Main voice generation entry point for the YouTube automation pipeline.
    Primary & Exclusive: Cartesia AI (Voice ID: d5495ba1-91c4-4581-a0d1-9ed3178e9b8c)
    """
    print(f"[VoiceGen] Generating: \"{text[:50]}...\"" if len(text) > 50 else f"[VoiceGen] Generating: \"{text}\"")
    return generate_speech_cartesia(text, output_path, voice_id=voice_id)
