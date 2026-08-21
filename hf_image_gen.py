import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Worker Configuration ──────────────────────────────────────────────────────

WORKERS = [
    "https://imageapi.sanketsarvaliya9.workers.dev/",
    "https://imageapi.techsp13.workers.dev/",
    "https://imageapi.sany-3pro.workers.dev/",
    "https://imageapi.sanketpatel794653.workers.dev/",
    "https://imageapi.sanypatel9.workers.dev/",
    "https://imageapi.sanyyt9.workers.dev/",
    "https://imageapi.sporthub9.workers.dev/",
    "https://weathered-waterfall-5b4b.sanketpatel9395.workers.dev/",
    "https://imageapi.crazysp1993.workers.dev/"
]

# Persistent state file — remembers which worker is active across restarts
WORKER_STATE_FILE = os.path.join(os.path.dirname(__file__), "worker_state.json")


def _get_current_utc_date():
    """Returns current UTC date string YYYY-MM-DD."""
    return time.strftime("%Y-%m-%d", time.gmtime())


def _load_worker_state():
    """
    Load persistent worker state from disk.
    Automatically resets exhausted workers if a new calendar day (UTC) has begun.
    """
    today = _get_current_utc_date()
    default_state = {"active_index": 0, "exhausted": [], "last_reset_date": today}

    if os.path.exists(WORKER_STATE_FILE):
        try:
            with open(WORKER_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Auto-reset quota exhaustion if it's a new day (UTC)
            if state.get("last_reset_date") != today:
                print(f"[WorkerState] New day detected ({today}) — auto-resetting all Cloudflare Workers!")
                state = default_state
                _save_worker_state(state)

            return state
        except Exception:
            pass

    return default_state


def _save_worker_state(state):
    """Save worker state to disk with current UTC date."""
    if "last_reset_date" not in state:
        state["last_reset_date"] = _get_current_utc_date()
    try:
        with open(WORKER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"[WorkerState] Warning: could not save state: {e}")


def _mark_worker_exhausted(url):
    """Mark a worker URL as exhausted and advance to the next available one."""
    state = _load_worker_state()
    if url not in state["exhausted"]:
        state["exhausted"].append(url)

    # Advance active_index to the next non-exhausted worker
    for i, w in enumerate(WORKERS):
        if w not in state["exhausted"]:
            state["active_index"] = i
            break
    else:
        # All workers exhausted — reset exhausted list and start over
        print("[WorkerState] All workers exhausted — resetting quota state.")
        state = {"active_index": 0, "exhausted": [], "last_reset_date": _get_current_utc_date()}

    _save_worker_state(state)

    try:
        import telegram_bot
        remaining = [w for w in WORKERS if w not in state["exhausted"]]
        if remaining:
            telegram_bot.send_message(
                f"🔄 *Cloudflare Worker Quota Hit!*\n"
                f"⛔ Exhausted: `{url}`\n"
                f"✅ Now using: `{WORKERS[state['active_index']]}`\n"
                f"📋 Workers remaining: {len(remaining)}/{len(WORKERS)}"
            )
        else:
            telegram_bot.send_message(
                "⚠️ *All Cloudflare Workers exhausted!*\n"
                "Quota state has been reset. Retrying from Worker 1."
            )
    except Exception:
        pass

    return state


def get_active_worker_info():
    """Returns current active worker index and URL for display."""
    state = _load_worker_state()
    idx = state.get("active_index", 0)
    exhausted = state.get("exhausted", [])
    return {
        "active_index": idx,
        "active_url": WORKERS[idx] if idx < len(WORKERS) else WORKERS[0],
        "exhausted_count": len(exhausted),
        "exhausted_urls": exhausted,
        "remaining": [w for w in WORKERS if w not in exhausted]
    }


def reset_worker_state():
    """Manually reset all worker quota exhaustion (e.g., next day reset)."""
    state = {"active_index": 0, "exhausted": []}
    _save_worker_state(state)
    print("[WorkerState] Worker quota state reset — all workers available.")


def _generate_fallback_image(prompt, filename, width, height, tag=""):
    """
    Fallback image generator if all Cloudflare workers are temporarily busy.
    Generates a clean stylized 2D solid background frame so the pipeline never halts.
    """
    try:
        from PIL import Image, ImageDraw
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        img = Image.new("RGB", (width, height), color=(245, 240, 230))
        draw = ImageDraw.Draw(img)
        # Draw clean border
        draw.rectangle([(10, 10), (width - 10, height - 10)], outline=(40, 40, 40), width=4)
        img.save(filename, format="PNG")
        print(f"{tag}[FALLBACK] Created clean placeholder image: {filename}")
        return True
    except Exception as e:
        print(f"{tag}[FALLBACK ERROR] Failed to create placeholder: {e}")
        return False


def _generate_via_gradio_flux(prompt, filename, width, height, tag=""):
    """
    Direct zero-credit FLUX.1-schnell Gradio Space generator.
    Works 100% free with zero API key dependencies, generating native 1024x576 or 576x1024 FLUX illustrations.
    """
    try:
        from gradio_client import Client
        from PIL import Image
        import random
        c = Client("black-forest-labs/FLUX.1-schnell")
        result = c.predict(
            prompt=prompt,
            seed=random.randint(1, 99999999),
            randomize_seed=True,
            width=width,
            height=height,
            num_inference_steps=4,
            api_name="/infer"
        )
        temp_img = result[0] if isinstance(result, (list, tuple)) else result
        if temp_img and os.path.exists(temp_img):
            dirname = os.path.dirname(filename)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            img = Image.open(temp_img).convert("RGB")
            img.save(filename, format="PNG")
            print(f"{tag}[SUCCESS FLUX Space {width}x{height}] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
            return True
    except Exception as e:
        print(f"{tag}[FLUX Space Error]: {e}")
    return False


def _generate_via_hf_client(prompt, filename, width, height, tag=""):
    """
    Direct Hugging Face InferenceClient fallback using FLUX.1-schnell.
    Generates exact 1024x576 (16:9) or 576x1024 (9:16) native FLUX images.
    """
    token = os.getenv("HF_TOKEN")
    if token:
        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=token)
            img = client.text_to_image(prompt, model="black-forest-labs/FLUX.1-schnell", width=width, height=height)
            dirname = os.path.dirname(filename)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            img.save(filename, format="PNG")
            print(f"{tag}[SUCCESS HF FLUX {width}x{height}] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
            return True
        except Exception as e:
            print(f"{tag}[HF FLUX Client Error]: {e}")

    # Seamless failover to zero-credit FLUX Space
    print(f"{tag}[FAILOVER] Switching to FLUX.1-schnell ZeroGPU Space...")
    return _generate_via_gradio_flux(prompt, filename, width, height, tag)


def _generate_image_via_workers(prompt, filename, width, height, label="", start_offset=0):
    """
    Shared image generation logic with persistent worker locking.
    Starts from active_index + start_offset so parallel batch threads use distinct worker keys.
    Uses the active working key until its daily quota limit is hit.
    Rotates immediately on error to avoid unnecessary retry delays.
    """
    tag = f"[{label}] " if label else ""

    state = _load_worker_state()
    active_idx = (state.get("active_index", 0) + start_offset) % len(WORKERS)
    exhausted_urls = set(state.get("exhausted", []))

    # Find candidate worker indices in priority order
    all_indices = list(range(len(WORKERS)))
    candidates = [i for i in (all_indices[active_idx:] + all_indices[:active_idx]) if WORKERS[i] not in exhausted_urls]

    if not candidates:
        print(f"{tag}[WARNING] All Cloudflare Workers hit daily free quota limit. Resetting worker pool...")
        state["exhausted"] = []
        _save_worker_state(state)
        candidates = all_indices

    # Enforce Cloudflare Worker maximum prompt character limit (cap at 1900 chars)
    if prompt and len(prompt) > 1900:
        prompt = prompt[:1900].rsplit(' ', 1)[0]

    headers = {
        "Authorization": "Bearer 987654321",
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}

    # Iterate through candidates; if a key errors, rotate immediately to next key
    for cur_idx in candidates:
        url = WORKERS[cur_idx]
        for attempt in range(1, 2):  # Single solid attempt with generous 25s timeout (prevents phantom neuron drains)
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=25)
                resp_text = (response.text or "").lower()
                is_quota = any(q in resp_text for q in ["quota", "exceeded", "upgrade"])
                is_concurrency = "concurrency" in resp_text

                if response.status_code == 200 and len(response.content) > 3000:
                    dirname = os.path.dirname(filename)
                    if dirname:
                        os.makedirs(dirname, exist_ok=True)

                    # Format image to exact aspect ratio
                    if width < height:  # 9:16 Vertical (Shorts: 576x1024)
                        try:
                            from PIL import Image
                            import io
                            img = Image.open(io.BytesIO(response.content)).convert("RGB")
                            iw, ih = img.size
                            
                            fit_w = width
                            fit_h = int(ih * (width / iw))
                            img_fit = img.resize((fit_w, fit_h), Image.LANCZOS)
                            bg_color = img.getpixel((8, 8))
                            canvas = Image.new("RGB", (width, height), bg_color)
                            paste_y = max(0, (height - fit_h) // 2 - 40)
                            canvas.paste(img_fit, (0, paste_y))
                            canvas.save(filename, format="PNG")
                            print(f"{tag}[SUCCESS 9:16 Vertical {width}x{height}] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
                        except Exception as e:
                            with open(filename, "wb") as f:
                                f.write(response.content)
                            print(f"{tag}[SUCCESS] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
                    elif width > height:  # 16:9 Landscape (Widescreen Full-Bleed 1024x576 - Zero Side Bars!)
                        try:
                            from PIL import Image
                            import io
                            img = Image.open(io.BytesIO(response.content)).convert("RGB")
                            iw, ih = img.size
                            if iw == width and ih == height:
                                img.save(filename, format="PNG")
                            else:
                                # Full-bleed center crop to 1024x576 widescreen (zero side bars!)
                                crop_top = (ih - height) // 2
                                crop_bottom = crop_top + height
                                img_crop = img.crop((0, crop_top, width, crop_bottom))
                                img_crop.save(filename, format="PNG")
                            print(f"{tag}[SUCCESS 16:9 Landscape Full-Bleed {width}x{height}] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
                        except Exception as e:
                            with open(filename, "wb") as f:
                                f.write(response.content)
                            print(f"{tag}[SUCCESS] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
                    else:
                        with open(filename, "wb") as f:
                            f.write(response.content)
                        print(f"{tag}[SUCCESS] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")

                    # Lock active_index onto this working key for future sequential images
                    if start_offset == 0:
                        state["active_index"] = cur_idx
                        _save_worker_state(state)
                    return True

                elif is_quota or response.status_code in [429, 402, 503]:
                    print(f"{tag}[QUOTA EXHAUSTED] Key #{cur_idx+1} hit daily limit ({response.status_code}). Rotating...")
                    if url not in state.setdefault("exhausted", []):
                        state["exhausted"].append(url)
                    _save_worker_state(state)
                    break

                elif is_concurrency:
                    time.sleep(0.5)
                    continue

                else:
                    break

            except Exception:
                break

    # If Cloudflare workers are busy or unavailable, seamlessly failover to HF FLUX.1-schnell
    print(f"{tag}[FAILOVER] Switching to HuggingFace FLUX.1-schnell...")
    return _generate_via_hf_client(prompt, filename, width, height, tag)


# ─── Public API ───────────────────────────────────────────────────────────────

from concurrent.futures import ThreadPoolExecutor

def generate_image_hf(prompt, filename, aspect_ratio="16:9", start_offset=0):
    """
    Generates high-quality 2D doodle images via FLUX.1-schnell Worker API pool.
    - 16:9 Landscape: FLUX with widescreen framing + 0% crop aspect-fitting to 1024x576.
    - 9:16 Vertical (Shorts): FLUX with vertical centered framing + 0% crop aspect-fitting to 576x1024.
    """
    if aspect_ratio == "9:16":
        # Inject centered framing so FLUX places subject strictly in the vertical safe zone
        vertical_prompt = prompt
        if "centered" not in vertical_prompt.lower():
            vertical_prompt += ", single prominent large subject centered in frame with generous padding around edges, 0% clipped edges"
        return _generate_image_via_workers(vertical_prompt, filename, width=576, height=1024, label="9:16 FLUX", start_offset=start_offset)
    else:
        landscape_prompt = prompt
        if "prominent" not in landscape_prompt.lower() and "framed" not in landscape_prompt.lower():
            landscape_prompt += ", single large prominent central subject framed cleanly with generous padding around edges, 0% clipped edges"
        return _generate_image_via_workers(landscape_prompt, filename, width=1024, height=576, label="16:9 FLUX", start_offset=start_offset)


def generate_batch_hf(items_list, aspect_ratio="16:9"):
    """
    Generates a batch of images by shifting worker key offset per item (Item 1 -> Key 1, Item 2 -> Key 2, etc.)
    Concurrently generates images in parallel across distinct Cloudflare Worker keys for 5x speedup.
    Supports aspect_ratio="16:9" or "9:16" vertical format.
    """
    def _worker_task(indexed_item):
        idx, item = indexed_item
        time.sleep(idx * 0.1) # Micro-stagger to distribute threads across distinct workers
        prompt = item["prompt"]
        out_path = item["output_path"]
        ar = item.get("aspect_ratio", aspect_ratio)
        return generate_image_hf(prompt, out_path, aspect_ratio=ar, start_offset=idx)

    items_with_idx = list(enumerate(items_list))
    with ThreadPoolExecutor(max_workers=min(8, len(items_list))) as executor:
        results = list(executor.map(_worker_task, items_with_idx))
    return results


def generate_image_hf_vertical(prompt, filename):
    """
    Generates a 9:16 vertical image (576x1024) for YouTube Shorts.
    """
    return generate_image_hf(prompt, filename, aspect_ratio="9:16")


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "--status":
        info = get_active_worker_info()
        print(f"Active Worker: #{info['active_index']+1} -> {info['active_url']}")
        print(f"Exhausted ({info['exhausted_count']}): {info['exhausted_urls']}")
        print(f"Remaining: {info['remaining']}")
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--reset":
        reset_worker_state()
        sys.exit(0)

    if len(sys.argv) < 3:
        print("Usage: python hf_image_gen.py <prompt> <output_path>")
        print("       python hf_image_gen.py --status")
        print("       python hf_image_gen.py --reset")
        sys.exit(1)

    prompt_arg = sys.argv[1]
    output_arg = sys.argv[2]
    test_prompt = (
        prompt_arg
        + ", simple 2D flat cartoon illustration style, thick clean black outlines, "
        "flat solid colors, solid background, no shading"
    )
    generate_image_hf(test_prompt, output_arg)
