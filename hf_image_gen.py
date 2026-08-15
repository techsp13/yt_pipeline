import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Worker Configuration ──────────────────────────────────────────────────────

WORKERS = [
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


# ─── Core Shared Generation Logic ─────────────────────────────────────────────

def _generate_via_flux_fallback(prompt, filename, width, height, tag=""):
    try:
        import urllib.parse, random
        encoded_p = urllib.parse.quote(prompt)
        w, h = (576, 1024) if width < height else (1024, 576)
        seed = random.randint(100, 999999)
        
        # 1. Try FLUX Model
        fallback_url = f"https://image.pollinations.ai/prompt/{encoded_p}?width={w}&height={h}&seed={seed}&nologo=true&model=flux"
        r = requests.get(fallback_url, timeout=25)
        if r.status_code == 200 and len(r.content) > 1000:
            dirname = os.path.dirname(filename)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(filename, "wb") as f:
                f.write(r.content)
            print(f"{tag}[SUCCESS via FLUX Fallback] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
            return True

        # 2. Backup to Turbo Model
        backup_url = f"https://image.pollinations.ai/prompt/{encoded_p}?width={w}&height={h}&seed={seed}&nologo=true&model=turbo"
        r_b = requests.get(backup_url, timeout=20)
        if r_b.status_code == 200 and len(r_b.content) > 1000:
            dirname = os.path.dirname(filename)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(filename, "wb") as f:
                f.write(r_b.content)
            print(f"{tag}[SUCCESS via Turbo Fallback] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
            return True
    except Exception as fe:
        print(f"{tag}[FALLBACK ERROR] Fallback generator exception: {fe}")
    return False


def _generate_image_via_workers(prompt, filename, width, height, label="", start_offset=0):
    """
    Shared image generation logic with persistent worker locking.
    Starts from active_index + start_offset so parallel batch threads use distinct worker keys.
    Uses the active working key until its daily quota limit is hit.
    Exhausted keys are saved to disk and never retried.
    """
    tag = f"[{label}] " if label else ""

    state = _load_worker_state()
    active_idx = (state.get("active_index", 0) + start_offset) % len(WORKERS)
    exhausted_urls = set(state.get("exhausted", []))

    # Find current active non-exhausted worker index
    all_indices = list(range(len(WORKERS)))
    candidates = [i for i in (all_indices[active_idx:] + all_indices[:active_idx]) if WORKERS[i] not in exhausted_urls]

    if not candidates:
        print(f"{tag}[WARNING] All Cloudflare Workers hit daily free quota limit. Using FLUX Fallback Generator...")
        return _generate_via_flux_fallback(prompt, filename, width, height, tag)

    # Lock onto the primary active candidate key
    cur_idx = candidates[0]

    # Enforce Cloudflare Worker maximum prompt character limit (cap at 1900 chars)
    if prompt and len(prompt) > 1900:
        prompt = prompt[:1900].rsplit(' ', 1)[0]

    headers = {
        "Authorization": "Bearer 987654321",
        "Content-Type": "application/json"
    }
    payload = {"prompt": prompt}

    # Attempt generation on the SAME active key
    url = WORKERS[cur_idx]

    for attempt in range(1, 4):
        print(f"{tag}Using Active Key #{cur_idx+1} (Attempt {attempt}/3): {url}")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            resp_text = (response.text or "").lower()
            is_quota = any(q in resp_text for q in ["quota", "exceeded", "upgrade"])
            is_concurrency = "concurrency" in resp_text

            if response.status_code == 200 and len(response.content) > 3000:
                dirname = os.path.dirname(filename)
                if dirname:
                    os.makedirs(dirname, exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"{tag}[SUCCESS] Saved to {filename} ({os.path.getsize(filename)//1024} KB)")
                
                # STORE WORKING KEY: Lock active_index onto this working key for all future images
                state["active_index"] = cur_idx
                _save_worker_state(state)
                return True

            elif is_quota or response.status_code in [429, 402, 503]:
                print(f"{tag}[QUOTA EXHAUSTED] Key #{cur_idx+1} hit daily limit ({response.status_code}). Permanently marking exhausted and rotating...")
                if url not in state.setdefault("exhausted", []):
                    state["exhausted"].append(url)
                next_active = (cur_idx + 1) % len(WORKERS)
                state["active_index"] = next_active
                _save_worker_state(state)
                # Recursively try next active key
                return _generate_image_via_workers(prompt, filename, width, height, label, start_offset=start_offset)

            elif is_concurrency:
                print(f"{tag}[KEY BUSY] Key #{cur_idx+1} busy (concurrency). Retrying same key after 1.2s pause...")
                time.sleep(1.2)

            else:
                print(f"{tag}[KEY ERROR] Key #{cur_idx+1} returned status {response.status_code}. Retrying...")
                time.sleep(1.0)

        except Exception as e:
            print(f"{tag}[KEY RETRY] Key #{cur_idx+1} attempt {attempt} error: {e}")
            time.sleep(1.0)

    # If 3 attempts on active key were busy, try next candidate key
    if len(candidates) > 1:
        next_idx = candidates[1]
        state["active_index"] = next_idx
        _save_worker_state(state)
        print(f"{tag}[KEY ROTATE] Active Key #{cur_idx+1} busy after 3 retries. Switching to Key #{next_idx+1}...")
        return _generate_image_via_workers(prompt, filename, width, height, label, start_offset=start_offset)

    print(f"{tag}[FALLBACK] Active Cloudflare worker busy. Using FLUX Fallback...")
    return _generate_via_flux_fallback(prompt, filename, width, height, tag)


# ─── Public API ───────────────────────────────────────────────────────────────

from concurrent.futures import ThreadPoolExecutor

def generate_image_hf(prompt, filename, aspect_ratio="16:9", start_offset=0):
    """
    Generates an image via Cloudflare Worker API pool.
    Supports aspect_ratio="16:9" (1024x576) or "9:16" (576x1024).
    """
    if aspect_ratio == "9:16":
        return _generate_image_via_workers(prompt, filename, width=576, height=1024, label="9:16", start_offset=start_offset)
    else:
        return _generate_image_via_workers(prompt, filename, width=1024, height=576, label="16:9", start_offset=start_offset)


def generate_batch_hf(items_list):
    """
    Generates a batch of images by shifting worker key offset per item (Item 1 -> Key 1, Item 2 -> Key 2, etc.)
    Concurrently generates images in parallel across distinct Cloudflare Worker keys for 5x speedup.
    """
    def _worker_task(indexed_item):
        idx, item = indexed_item
        time.sleep(idx * 0.1) # Micro-stagger to distribute threads across distinct workers
        prompt = item["prompt"]
        out_path = item["output_path"]
        return generate_image_hf(prompt, out_path, aspect_ratio="16:9", start_offset=idx)

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
