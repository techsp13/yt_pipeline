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
                line_s = line.strip()
                if line_s.startswith("CARTESIA_API_KEY=") or line_s.startswith("CARTESIA_API_KEYS="):
                    val = line_s.split("=", 1)[1].strip().strip('"').strip("'")
                    for k in val.split(","):
                        k_clean = k.strip()
                        if k_clean and k_clean not in keys:
                            keys.append(k_clean)
    for k in KNOWN_CARTESIA_KEYS:
        if k not in keys:
            keys.append(k)
    env_k = os.getenv("CARTESIA_API_KEY") or os.getenv("CARTESIA_API_KEYS")
    if env_k:
        for k in env_k.split(","):
            k_clean = k.strip()
            if k_clean and k_clean not in keys:
                keys.append(k_clean)
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
from text_humanizer import humanize_text

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
    # Strip any remaining lone unclosed brackets
    text = re.sub(r"[\(\[\{\)\]\}]", "", text)
    meta_pattern = r"\b(stick\s*figures?|stickfigures?|doodles?|illustrations?|on-screen|on screen|narrators?|animations?|drawings?|act\s*\d+|scene\s*\d+)\b"
    text = re.sub(meta_pattern, "", text, flags=re.IGNORECASE)
    text = text.replace('"', '').replace('*', '').strip()
    
    # Apply humanization to convert numbers, currencies, dates, & symbols into natural spoken English
    text = humanize_text(text)
    
    text = re.sub(r"\s+", " ", text)
    return text


def build_continuous_tts_transcript(valid_scenes):
    """
    Reconstructs fluid, unbroken grammatical sentences for Cartesia TTS.
    Eliminates artificial mid-sentence pauses and intonation resets caused by ' ... ' delimiters.
    """
    chunks = []
    for item in valid_scenes:
        if isinstance(item, (list, tuple)):
            n = item[1]
        elif isinstance(item, dict):
            n = item.get("narration")
        else:
            n = str(item)
        n_clean = str(n or "").strip()
        if n_clean:
            chunks.append(n_clean)

    # Join with clean single space (sentences flow continuously with natural punctuation)
    full_text = " ".join(chunks)
    full_text = re.sub(r"\s+", " ", full_text)
    full_text = re.sub(r"\s+([,.:;!?])", r"\1", full_text)
    return full_text.strip()


def split_into_tts_chunks(text, max_words=300):
    """Splits a long narration into natural spoken chunks at sentence boundaries."""
    if len(text.split()) <= max_words:
        return [text]
    
    parts = re.split(r"(?<=[.!?])\s+", text)
    delim = " "

    chunks = []
    cur_chunk = []
    cur_words = 0
    for p in parts:
        p_clean = p.strip()
        if not p_clean:
            continue
        p_w = len(p_clean.split())
        if cur_words + p_w > max_words and cur_chunk:
            chunks.append(delim.join(cur_chunk))
            cur_chunk = [p_clean]
            cur_words = p_w
        else:
            cur_chunk.append(p_clean)
            cur_words += p_w
    if cur_chunk:
        chunks.append(delim.join(cur_chunk))
    return chunks


_EXHAUSTED_KEYS = set()

def _generate_single_chunk_cartesia(text, output_path, voice_id=DEFAULT_VOICE_ID, api_key=None, retry_clone_on_missing=True):
    """
    Generates audio for a single chunk (<350 words) using Cartesia AI API with automatic key rotation.
    """
    if not text or len(text) < 2:
        return False

    all_keys = [api_key] if api_key else get_all_cartesia_keys()
    keys_to_try = [k for k in all_keys if k not in _EXHAUSTED_KEYS]
    if not keys_to_try:
        print("[Cartesia TTS] ERROR: No working CARTESIA_API_KEY configured!")
        notify_key_expired("All Cartesia keys in rotation pool exhausted")
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
            "model_id": os.getenv("CARTESIA_MODEL", "sonic-2"),
            "transcript": text,
            "language": "en",
            "voice": {
                "mode": "id",
                "id": target_vid
            },
            "output_format": {
                "container": container_format,
                "sample_rate": 24000 if container_format == "wav" else 44100
            },
            "generation_config": {
                "speed": 1.0,
                "volume": 1.0,
                "emotion": "curious"
            }
        }
        
        if container_format == "mp3":
            payload["output_format"]["bit_rate"] = 128000
        else:
            payload["output_format"]["encoding"] = "pcm_s16le"

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=180)
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
                    return _generate_single_chunk_cartesia(text, output_path, voice_id=new_vid, api_key=key, retry_clone_on_missing=False)

            # Handle temporary concurrency rate limit (429) -> Backoff & retry
            if res.status_code == 429:
                import time
                time.sleep(1.5)
                continue

            # Check if key is expired, unauthorized, or quota exceeded -> Rotate key!
            if res.status_code in [401, 402, 403]:
                _EXHAUSTED_KEYS.add(key)
                last_error = f"Key #{idx} ({key[:10]}...) HTTP {res.status_code}: {res.text[:150]}"
                print(f"[Cartesia Key #{idx} Quota Limit]: {last_error}")
                if idx < len(keys_to_try):
                    print(f"[Cartesia] Rotating to next key ({idx+1}/{len(keys_to_try)})...")
                continue

            # Fallback to sonic-2 model if temporary error
            print(f"[Cartesia TTS] Warning: Key #{idx} returned {res.status_code}. Retrying...")
            headers["Cartesia-Version"] = "2024-06-10"
            payload["model_id"] = "sonic-2"
            res2 = requests.post(url, headers=headers, json=payload, timeout=180)
            if res2.status_code == 200:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(res2.content)
                size_kb = os.path.getsize(output_path) / 1024
                print(f"[Cartesia TTS] Saved using Key #{idx}: {output_path} ({size_kb:.1f} KB)")
                return True
            elif res2.status_code == 429:
                import time
                time.sleep(1.5)
                continue
            elif res2.status_code in [401, 402, 403]:
                _EXHAUSTED_KEYS.add(key)
                last_error = f"Key #{idx} HTTP {res2.status_code}: {res2.text[:150]}"
                print(f"[Cartesia Key #{idx} Quota Limit]: {last_error}")
                if idx < len(keys_to_try):
                    print(f"[Cartesia] Rotating to next key ({idx+1}/{len(keys_to_try)})...")
                continue

        except Exception as e:
            print(f"[Cartesia TTS] Exception with Key #{idx}: {e}")
            last_error = str(e)
            continue

    print("[Cartesia TTS] ALL keys in rotation pool expired or failed!")
    notify_key_expired(last_error or "All Cartesia keys in rotation pool exhausted")
    return False


def generate_speech_cartesia(text, output_path, voice_id=DEFAULT_VOICE_ID, api_key=None, retry_clone_on_missing=True):
    """
    Main Cartesia voice generator with automatic chunking for long narrations.
    Guarantees 100% voiceover coverage with zero truncation regardless of script length.
    """
    text = clean_tts_transcript(text)
    if not text or len(text) < 2:
        return False

    words = text.split()
    # If text is within Cartesia's safe single-call buffer (<= 350 words), generate directly
    if len(words) <= 350:
        return _generate_single_chunk_cartesia(text, output_path, voice_id=voice_id, api_key=api_key, retry_clone_on_missing=retry_clone_on_missing)

    # For long scripts, split into safe chunks of ~300 words and stitch seamlessly with FFmpeg
    chunks = split_into_tts_chunks(text, max_words=300)
    print(f"[Cartesia TTS] Long script ({len(words)} words) -> Split into {len(chunks)} chunks for 100% complete voiceover.")

    import tempfile, subprocess
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "temp_tts_chunks")
    os.makedirs(temp_dir, exist_ok=True)

    chunk_files = []
    success_all = True
    for c_idx, chunk_text in enumerate(chunks):
        c_path = os.path.join(temp_dir, f"chunk_{c_idx:03d}.wav")
        print(f"  [Chunk {c_idx+1}/{len(chunks)}] Synthesizing {len(chunk_text.split())} words...")
        ok = _generate_single_chunk_cartesia(chunk_text, c_path, voice_id=voice_id, api_key=api_key, retry_clone_on_missing=retry_clone_on_missing)
        if not ok or not os.path.exists(c_path) or os.path.getsize(c_path) < 1000:
            print(f"  [Chunk {c_idx+1}] FAILED!")
            success_all = False
            break
        chunk_files.append(c_path)

    if not success_all or len(chunk_files) != len(chunks):
        print("[Cartesia TTS] Chunked generation failed for one or more chunks.")
        return False

    # Seamless concatenation using FFmpeg concat demuxer
    concat_list_p = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list_p, "w", encoding="utf-8") as f:
        for cf in chunk_files:
            cf_clean = cf.replace("\\", "/")
            f.write(f"file '{cf_clean}'\n")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if output_path.endswith(".mp3"):
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_p, "-c:a", "libmp3lame", "-b:a", "192k", output_path]
    else:
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_p, "-c:a", "pcm_s16le", "-ar", "24000", output_path]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Clean up temp chunk files
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

    final_size_kb = os.path.getsize(output_path) / 1024
    print(f"[Cartesia TTS] Concatenated {len(chunks)} chunks -> {output_path} ({final_size_kb:.1f} KB)")
    return True



def generate_speech(text, output_path, voice_id=DEFAULT_VOICE_ID, reference_wav=DEFAULT_REFERENCE, **kwargs):
    """
    Main voice generation entry point.
    STRICT USER RULE: Cartesia AI ONLY. If credits expire, prompt user for new key.
    """
    print(f"[VoiceGen] Generating: \"{text[:50]}...\"" if len(text) > 50 else f"[VoiceGen] Generating: \"{text}\"")
    return generate_speech_cartesia(text, output_path, voice_id=voice_id)
