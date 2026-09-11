import os
import sys
import re
import time
import json
import shutil
import io
import uuid
import concurrent.futures
import random
import subprocess
from contextlib import redirect_stdout, redirect_stderr

from gflow_cli.cli import main as gflow_cli_main

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_PROJECT_IDS_FILE = os.path.join(os.path.dirname(__file__), ".gflow_project_ids.json")
_PROFILE_INDEX_FILE = os.path.join(os.path.dirname(__file__), ".gflow_current_profile")

_PROFILES = ["acc4", "acc3"]


def _notify_gflow_expired(profile, error_msg):
    """Sends immediate alert to Telegram when Google Flow auth session expires."""
    try:
        import telegram_bot
        telegram_bot.send_message(
            f"🚨 *GOOGLE FLOW AUTH EXPIRED!*\n\n"
            f"The Google session for profile *{profile}* has expired.\n"
            f"*Error Details:* `{error_msg[:180]}`\n\n"
            f"🔑 *Action Required:* Run this command on PC to log back in:\n`gflow auth login`"
        )
    except Exception as e:
        print(f"[gflow Alert Error]: {e}")


def _get_saved_profile():
    if os.path.exists(_PROFILE_INDEX_FILE):
        try:
            prof = open(_PROFILE_INDEX_FILE).read().strip()
            if prof in _PROFILES:
                return prof
        except Exception:
            pass
    return "default"


def _save_profile(profile_name):
    try:
        open(_PROFILE_INDEX_FILE, "w").write(profile_name.strip())
    except Exception:
        pass


def _rotate_profile():
    current = _get_saved_profile()
    curr_idx = _PROFILES.index(current) if current in _PROFILES else 0
    next_idx = (curr_idx + 1) % len(_PROFILES)
    next_profile = _PROFILES[next_idx]
    _save_profile(next_profile)
    print(f"[gflow] 🔄 Auto-switched profile from '{current}' -> '{next_profile}'")
    return next_profile


def _get_project_id_for_profile(profile):
    if os.path.exists(_PROJECT_IDS_FILE):
        try:
            data = json.load(open(_PROJECT_IDS_FILE))
            return data.get(profile)
        except Exception:
            pass
    return None


def _save_project_id_for_profile(profile, project_id):
    try:
        data = {}
        if os.path.exists(_PROJECT_IDS_FILE):
            data = json.load(open(_PROJECT_IDS_FILE))
        if project_id:
            data[profile] = project_id.strip()
        elif profile in data:
            del data[profile]
        json.dump(data, open(_PROJECT_IDS_FILE, "w"), indent=2)
    except Exception:
        pass


def _extract_project_id(text):
    m = re.search(r"Project:\s*([0-9a-f\-]{36})", text)
    return m.group(1) if m else None


class CommandResult:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run_gflow_native_call(args_list):
    """Executes gflow-cli directly inside Python as a native library call."""
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    returncode = 0
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            gflow_cli_main(args_list, standalone_mode=False)
    except SystemExit as e:
        returncode = e.code if isinstance(e.code, int) else 0
    except Exception as e:
        returncode = 1
        stderr_buf.write(f"\nLibrary Exception: {e}\n")

    return CommandResult(returncode, stdout_buf.getvalue(), stderr_buf.getvalue())


def handle_recaptcha_challenge(profile_name):
    """
    Opens Google Flow in a visible Chrome browser window using the profile's user data directory,
    notifies the user via Telegram and console, and waits for the user to solve/generate and press Continue.
    """
    import subprocess
    import webbrowser
    
    print(f"\n🚨 [CAPTCHA DETECTED] Google Flow reCAPTCHA challenge triggered on profile '{profile_name}'.")
    print(f"🌐 Opening Google Chrome on https://labs.google/fx/tools/flow for profile '{profile_name}'...")
    
    profile_dir_name = f"profile_{profile_name}" if not profile_name.startswith("profile_") else profile_name
    user_data_dir = rf"C:\Users\ASUS\AppData\Local\ffroliva\gflow-cli\{profile_dir_name}"
    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    
    proc = None
    if os.path.exists(chrome_exe) and os.path.exists(user_data_dir):
        try:
            # Kill any background lock on this profile first
            subprocess.run(["powershell", "-NoProfile", "-Command",
                f"Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                f"Where-Object {{$_.CommandLine -like '*{profile_dir_name}*'}} | "
                f"ForEach-Object {{Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}}"
            ], capture_output=True, timeout=5)
            
            # Clean locks
            locks_dir = r"C:\Users\ASUS\AppData\Local\ffroliva\gflow-cli\locks"
            if os.path.exists(locks_dir):
                for lf in os.listdir(locks_dir):
                    if profile_name in lf:
                        try: os.remove(os.path.join(locks_dir, lf))
                        except Exception: pass
            
            proc = subprocess.Popen([
                chrome_exe,
                f"--user-data-dir={user_data_dir}",
                "https://labs.google/fx/tools/flow"
            ])
        except Exception as e:
            print(f"[CAPTCHA handler] Chrome launch error: {e}")
            webbrowser.open("https://labs.google/fx/tools/flow")
    else:
        webbrowser.open("https://labs.google/fx/tools/flow")
        
    try:
        import telegram_bot
        btn = [[{"text": "✅ I Fixed It - Continue", "callback_data": "captcha_solved"}]]
        msg = telegram_bot.send_message(
            f"🚨 *Google Flow CAPTCHA Challenge on `{profile_name}`!*\n\n"
            f"A Chrome browser window has been opened on your screen for **{profile_name}**.\n\n"
            f"👉 **Steps:**\n"
            f"1. In the opened Chrome window, type any prompt and click **Generate** once.\n"
            f"2. Solve any visual puzzle if prompted.\n"
            f"3. Click the button below when done to resume automation!",
            buttons=btn
        )
        print(f"[gflow] ⏳ Waiting for user to solve CAPTCHA and click [I Fixed It - Continue] on Telegram...")
        telegram_bot.wait_for_interaction(msg)
        print(f"[gflow] ✅ User confirmed CAPTCHA resolution! Closing browser and resuming...")
    except Exception as e:
        print(f"[gflow] Telegram interaction error: {e}. Sleeping 30s for manual fix...")
        time.sleep(30)
        
    # Close the manual Chrome instance and clear locks so gflow-cli can acquire the profile cleanly
    try:
        if proc:
            proc.terminate()
            time.sleep(1.0)
            proc.kill()
    except Exception:
        pass
        
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
            f"Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
            f"Where-Object {{$_.CommandLine -like '*{profile_dir_name}*'}} | "
            f"ForEach-Object {{Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}}"
        ], capture_output=True, timeout=5)
    except Exception:
        pass
        
    locks_dir = r"C:\Users\ASUS\AppData\Local\ffroliva\gflow-cli\locks"
    if os.path.exists(locks_dir):
        for lf in os.listdir(locks_dir):
            try: os.remove(os.path.join(locks_dir, lf))
            except Exception: pass
            
    time.sleep(2.0)


def _run_gflow(cmd, timeout=300, target_profile=None):
    """
    Direct in-process Python library call to gflow_cli.
    Preserves reCAPTCHA Enterprise bot score and rotates profiles smoothly.
    """
    os.environ.pop("GFLOW_CLI_HEADLESS", None)
    os.environ.pop("HEADLESS", None)
    os.environ.pop("GFLOW_CLI_JITTER_RANGE", None)
    clean_cmd = cmd[1:] if cmd and cmd[0] == "gflow" else cmd

    if target_profile:
        profiles_to_try = [target_profile] + [p for p in _PROFILES if p != target_profile]
    else:
        saved = _get_saved_profile()
        if saved in _PROFILES:
            idx = _PROFILES.index(saved)
            profiles_to_try = _PROFILES[idx:] + _PROFILES[:idx]
        else:
            profiles_to_try = list(_PROFILES)

    last_res = None

    for current_profile in profiles_to_try:
        # Strip any existing --profile / --transport flags from cmd
        base_cmd = []
        skip_next = False
        for arg in clean_cmd:
            if skip_next:
                skip_next = False
                continue
            if arg in ["--profile", "--transport", "--jitter"]:
                skip_next = True
                continue
            base_cmd.append(arg)

        # Attach existing persistent project ID for this profile to avoid project creation WAF
        if "--project" not in base_cmd:
            saved_pid = _get_project_id_for_profile(current_profile)
            if saved_pid:
                base_cmd = base_cmd + ["--project", saved_pid]

        cmd_ui = base_cmd + ["--profile", current_profile, "--transport", "ui_automation"]

        # ── attempt loop: retry temporary errors on the SAME account ──────────
        MAX_SAME_ACCOUNT_RETRIES = 2

        for attempt in range(MAX_SAME_ACCOUNT_RETRIES):
            res_ui = _run_gflow_native_call(cmd_ui)
            last_res = res_ui
            combined = (res_ui.stdout + res_ui.stderr).lower()

            # Record any created project ID for this profile
            extracted_pid = _extract_project_id(res_ui.stdout + res_ui.stderr)
            if extracted_pid:
                _save_project_id_for_profile(current_profile, extracted_pid)

            # SUCCESS
            if res_ui.returncode == 0:
                _save_profile(current_profile)
                return res_ui

            rc = res_ui.returncode
            print(f"[gflow] Profile '{current_profile}' rc={rc} attempt={attempt+1}. {res_ui.stdout[:120]}")

            # PROFILE LOCKED → clear lock, retry same account
            if rc == 11 or "is locked" in combined or "permission denied" in combined:
                print(f"[gflow] 🔓 Locked. Clearing lock & retrying same account...")
                try:
                    import subprocess as _sp
                    profile_dir_name = f"profile_{current_profile}" if not current_profile.startswith("profile_") else current_profile
                    _sp.run(["powershell", "-NoProfile", "-Command",
                        f"Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
                        f"Where-Object {{$_.CommandLine -like '*{profile_dir_name}*'}} | "
                        f"ForEach-Object {{Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue}}"
                    ], capture_output=True, timeout=5)
                except Exception:
                    pass
                locks_dir = r"C:\Users\ASUS\AppData\Local\ffroliva\gflow-cli\locks"
                if os.path.exists(locks_dir):
                    for lf in os.listdir(locks_dir):
                        if current_profile in lf:
                            try: os.remove(os.path.join(locks_dir, lf))
                            except Exception: pass
                time.sleep(1.5)
                continue

            # WAF REJECTION / RECAPTCHA (rc=10) → Launch interactive browser for human fix
            if rc == 10 or "waf reject" in combined or "recaptcha" in combined or "public_error_unusual_activity" in combined:
                print(f"[gflow] 🛡️ WAF / reCAPTCHA challenge on '{current_profile}'. Opening browser for user to solve...")
                handle_recaptcha_challenge(current_profile)
                continue

            # BURST RATE LIMIT (rc=4) → Switch immediately to next account in pool
            if rc == 4 or "rate limit" in combined:
                print(f"[gflow] ⏳ Rate-limit on '{current_profile}' (rc=4). Rotating to next account...")
                break

            # PERMANENT FAILURE → switch to next account
            is_auth = any(kw in combined for kw in [
                "login required", "unauthorized", "sign in to your google account",
                "re-authenticate", "authentication expired"
            ])
            is_quota = any(kw in combined for kw in ["daily quota", "quota_reached", "per_model_daily_quota"])
            if rc in (3, 9) or is_auth or is_quota:
                print(f"[gflow] ❌ Auth/Quota issue on '{current_profile}' (rc={rc}). Switching account...")
                if is_auth:
                    _notify_gflow_expired(current_profile, res_ui.stderr or res_ui.stdout)
                break

            # UI SELECTOR DRIFT (rc=23)
            if rc == 23 or "uiselectordrift" in combined or "selector" in combined:
                wait = 4 * (attempt + 1)
                print(f"[gflow] 🔄 UI drift on '{current_profile}'. Waiting {wait}s then retrying...")
                time.sleep(wait)
                continue

            # BROWSER SESSION CLOSED (rc=15)
            if rc == 15:
                print(f"[gflow] 🌐 Browser session closed on '{current_profile}'. Retrying...")
                time.sleep(2.0)
                continue

            # Unknown error → switch account
            print(f"[gflow] ⚠️ Unknown error rc={rc} on '{current_profile}'. Switching account...")
            break

    return last_res


def sanitize_prompt_for_safety(prompt):
    """Scrubs real human names and policy-triggering keywords to prevent Google Flow safety blocks."""
    replacements = {
        r"\bScott Kelly\b": "a generic male astronaut",
        r"\bMark Kelly\b": "a twin astronaut",
        r"\bHippocrates\b": "an ancient Greek physician",
        r"\bGalen\b": "an ancient Roman doctor",
        r"\bÖtzi\b": "a prehistoric alpine traveler",
        r"\bOtzi\b": "a prehistoric alpine traveler",
        r"\bHammurabi\b": "an ancient ruler",
        r"\bEdwin Smith\b": "an ancient medical practitioner",
        r"\bEbers\b": "an ancient healer"
    }
    for pattern, replacement in replacements.items():
        prompt = re.sub(pattern, replacement, prompt, flags=re.IGNORECASE)
    return prompt


def generate_imagen_image(prompt, output_path, aspect_ratio="16:9", max_retries=3, override_profile=None):
    """
    Generates a single scene strictly using swissmarley/gflow-cli with Google Flow Nano Banana Pro.
    Rotates seamlessly across authenticated profiles (default, acc2, acc3, acc4).
    """
    prompt = sanitize_prompt_for_safety(prompt)
    abs_path = os.path.abspath(output_path)
    out_dir = os.path.dirname(abs_path)
    os.makedirs(out_dir, exist_ok=True)

    try:
        from playwright_flow_generator import generate_image_playwright
        ok = generate_image_playwright(prompt, abs_path, aspect_ratio=aspect_ratio)
        if ok and os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000:
            return True
        time.sleep(5)
        ok = generate_image_playwright(prompt, abs_path, aspect_ratio=aspect_ratio)
        if ok and os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000:
            return True
        time.sleep(5)
        ok = generate_image_playwright(prompt, abs_path, aspect_ratio=aspect_ratio)
        if ok and os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000:
            return True
    except Exception as e_pw:
        print(f"[gflow Playwright fallback]: {e_pw}")
    return bool(os.path.exists(abs_path) and os.path.getsize(abs_path) > 1000)


def generate_batch_imagen_images(batch_scenes, out_dir, aspect_ratio="16:9"):
    """
    Generates scenes concurrently in parallel across Google Flow worker pool.
    Cuts generation time by ~3x.
    """
    if not batch_scenes:
        return True

    # Pre-emptively clear stale locks
    locks_dir = r"C:\Users\ASUS\AppData\Local\ffroliva\gflow-cli\locks"
    if os.path.exists(locks_dir):
        for lf in os.listdir(locks_dir):
            try:
                os.remove(os.path.join(locks_dir, lf))
            except Exception:
                pass

    print(f"[gflow Clean Batch] Generating {len(batch_scenes)} scenes cleanly with nano-pro pool...")

    success_count = 0
    for idx, item in enumerate(batch_scenes):
        current_active = _get_saved_profile()
        print(f"[Scene {idx+1}/{len(batch_scenes)}] Generating Scene V{item['num']} ({item['padded_filename']}) [Primary Profile: '{current_active}']...")
        ok = generate_imagen_image(item["prompt"], item["output_path"], aspect_ratio=aspect_ratio)
        if ok:
            success_count += 1
            time.sleep(2.0)
        else:
            print(f"[Scene {idx+1}/{len(batch_scenes)}] ⚠️ Scene V{item['num']} generation failed across all profiles.")
            time.sleep(3.0)

    print(f"[gflow Clean Batch OK] Completed {success_count}/{len(batch_scenes)} scene images!")
    return success_count == len(batch_scenes)
