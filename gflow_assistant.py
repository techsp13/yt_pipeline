import os
import sys
import re
import time
import json
import shutil
import io
import concurrent.futures
from contextlib import redirect_stdout, redirect_stderr

from gflow_cli.cli import main as gflow_cli_main

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_PROJECT_ID_FILE = os.path.join(os.path.dirname(__file__), ".gflow_project_id")
_PROFILE_INDEX_FILE = os.path.join(os.path.dirname(__file__), ".gflow_current_profile")

_PROFILES = ["default", "acc2", "acc3"]


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
    _clear_saved_project_id()
    print(f"[gflow] 🔄 Auto-switched profile from '{current}' -> '{next_profile}'")
    return next_profile


def _get_saved_project_id():
    if os.path.exists(_PROJECT_ID_FILE):
        pid = open(_PROJECT_ID_FILE).read().strip()
        if pid:
            return pid
    return None


def _save_project_id(project_id):
    open(_PROJECT_ID_FILE, "w").write(project_id.strip())


def _clear_saved_project_id():
    if os.path.exists(_PROJECT_ID_FILE):
        try:
            os.remove(_PROJECT_ID_FILE)
            print("[gflow] Cleared saved project ID. A new project will be created.")
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


def _run_gflow(cmd, timeout=300, target_profile=None):
    """
    Direct in-process Python library call to gflow_cli.
    Enforces 100% Headless mode + zero jitter delay for maximum speed.
    """
    os.environ["GFLOW_CLI_HEADLESS"] = "1"
    os.environ["HEADLESS"] = "1"
    os.environ["GFLOW_CLI_JITTER_RANGE"] = "0"
    last_res = None
    
    clean_cmd = cmd[1:] if cmd and cmd[0] == "gflow" else cmd
    profiles_to_try = [target_profile] if target_profile else _PROFILES

    for current_profile in profiles_to_try:
        base_cmd = []
        skip_next = False
        for arg in clean_cmd:
            if skip_next:
                skip_next = False
                continue
            if arg in ["--profile", "--transport"]:
                skip_next = True
                continue
            base_cmd.append(arg)

        # Pass --jitter 0 flag
        base_cmd_with_jitter = base_cmd + ["--jitter", "0"]
        cmd_ui = base_cmd_with_jitter + ["--profile", current_profile, "--transport", "ui_automation"]
        
        # Execute using stable ui_automation transport
        res_ui = _run_gflow_native_call(cmd_ui)
        last_res = res_ui
        combined = (res_ui.stdout + res_ui.stderr).lower()

        # Handle ReturnCode 11 (Profile locked) by clearing lock file and retrying
        if res_ui.returncode == 11 or "is locked" in combined:
            print(f"[gflow] 🔓 Profile '{current_profile}' was locked. Clearing stale lock file and retrying...")
            locks_dir = r"C:\Users\ASUS\AppData\Local\ffroliva\gflow-cli\locks"
            if os.path.exists(locks_dir):
                for lf in os.listdir(locks_dir):
                    if current_profile in lf:
                        try:
                            os.remove(os.path.join(locks_dir, lf))
                        except Exception:
                            pass
            time.sleep(0.5)
            res_ui = _run_gflow_native_call(cmd_ui)
            last_res = res_ui
            combined = (res_ui.stdout + res_ui.stderr).lower()

        if res_ui.returncode == 0:
            return res_ui

        print(f"[gflow] Profile '{current_profile}' returncode {res_ui.returncode}. Output: {res_ui.stdout[:150]}")
        time.sleep(0.5)

    # Only send alert if there is a TRUE auth/login failure across all profiles
    if last_res:
        combined_last = (last_res.stdout + last_res.stderr).lower()
        if any(kw in combined_last for kw in ["login required", "unauthorized", "sign in to your google account", "re-authenticate"]):
            print(f"🚨 [gflow] True Auth Expiry detected on profile '{_get_saved_profile()}'")
            _notify_gflow_expired(_get_saved_profile(), last_res.stderr or last_res.stdout)

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


def generate_imagen_image(prompt, output_path, aspect_ratio="16:9", max_retries=2, override_profile=None):
    """
    Generates a single scene using native `gflow_cli` Python library call.
    Verifies output file existence & non-zero file size.
    """
    prompt = sanitize_prompt_for_safety(prompt)
    abs_path = os.path.abspath(output_path)
    out_dir = os.path.dirname(abs_path)
    os.makedirs(out_dir, exist_ok=True)

    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except Exception:
            pass

    for attempt in range(max_retries):
        temp_dir = os.path.join(out_dir, f"_gflow_tmp_{attempt}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)

        project_id = _get_saved_project_id()
        cmd = ['image', 't2i', '--model', 'imagen4', '--aspect', aspect_ratio, '--out', temp_dir]
        if project_id:
            cmd += ['--project', project_id]
        cmd.append(prompt.replace("\n", " ").strip())

        res = _run_gflow(cmd, timeout=300, target_profile=override_profile)

        pid = _extract_project_id(res.stdout + res.stderr)
        if pid:
            _save_project_id(pid)

        files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                 if (f.endswith('.jpg') or f.endswith('.png')) and os.path.getsize(os.path.join(temp_dir, f)) > 10000]

        if files:
            newest = max(files, key=os.path.getmtime)
            shutil.copy2(newest, abs_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"[gflow Parallel Worker] SUCCESS -> {abs_path} ({os.path.getsize(abs_path)} bytes)")
            return True

        print(f"[gflow Parallel Worker] Attempt {attempt+1} failed. Clearing project ID and retrying...")
        _clear_saved_project_id()
        shutil.rmtree(temp_dir, ignore_errors=True)
        time.sleep(1)

    return False


def generate_batch_imagen_images(batch_scenes, out_dir, aspect_ratio="16:9"):
    """
    Generates scenes in PARALLEL using 3 Multi-Profile Workers (default, acc2, acc3).
    Dramatically increases speed from ~50s down to ~12-15s!
    """
    if not batch_scenes:
        return True

    os.environ["GFLOW_CLI_JITTER_RANGE"] = "0"
    os.environ["GFLOW_CLI_HEADLESS"] = "1"
    os.environ["HEADLESS"] = "1"

    print(f"[gflow 3x Parallel] Launching 3 multi-profile workers for {len(batch_scenes)} scenes...")

    work_items = []
    for idx, item in enumerate(batch_scenes):
        profile = _PROFILES[idx % len(_PROFILES)]
        work_items.append((item, profile))

    def _worker(task):
        item, profile = task
        print(f"[Worker:{profile}] Generating Scene V{item['num']} ({item['padded_filename']})...")
        return generate_imagen_image(item["prompt"], item["output_path"], aspect_ratio=aspect_ratio, override_profile=profile)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(_PROFILES), len(batch_scenes))) as executor:
        results = list(executor.map(_worker, work_items))

    success_count = sum(1 for r in results if r)
    print(f"[gflow 3x Parallel OK] Completed {success_count}/{len(batch_scenes)} scene images!")
    return success_count == len(batch_scenes)
