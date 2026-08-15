import os
import sys
import time
import subprocess
import requests
import msvcrt
from dotenv import load_dotenv

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LOCK_FILE_PATH = r"D:\youtube_automation_agent\.launcher.lock"
_lock_fp = None

def is_pid_running(pid):
    try:
        if not pid or not str(pid).isdigit():
            return False
        out = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /FO CSV', shell=True, text=True)
        return str(pid) in out
    except Exception:
        return False

def acquire_single_instance_lock():
    global _lock_fp
    try:
        if os.path.exists(LOCK_FILE_PATH):
            try:
                with open(LOCK_FILE_PATH, "r") as f:
                    old_pid = f.read().strip()
                if old_pid and not is_pid_running(old_pid):
                    os.remove(LOCK_FILE_PATH)
            except Exception:
                pass

        _lock_fp = open(LOCK_FILE_PATH, "a+")
        _lock_fp.seek(0)
        msvcrt.locking(_lock_fp.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_fp.truncate(0)
        _lock_fp.write(str(os.getpid()))
        _lock_fp.flush()
        return True
    except (IOError, OSError):
        print("[Single Instance Guard] Another telegram_launcher instance is already running!")
        sys.exit(0)

acquire_single_instance_lock()

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env")
    sys.exit(1)

print("💻 Telegram Full Remote Terminal Active (Single Instance Guard Enabled)!")
print("Send any CMD command in Telegram (e.g., 'd:', 'python -u youtube_agent.py', 'dir', 'tasklist').")

current_cwd = r"D:\youtube_automation_agent"

def send_msg(text):
    try:
        # Split message if exceeds 4000 chars
        for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                "chat_id": CHAT_ID,
                "text": f"```\n{chunk}\n```",
                "parse_mode": "Markdown"
            }, timeout=10)
    except Exception as e:
        print(f"Error sending msg: {e}")

offset = 0
try:
    res = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1&timeout=2", timeout=5).json()
    if res.get("result"):
        offset = res["result"][-1]["update_id"] + 1
except Exception:
    pass

running_proc = None

while True:
    try:
        # Check for emergency /stop or /kill commands from Telegram even while youtube_agent is running
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        params = {"timeout": 1}
        if offset:
            params["offset"] = offset

        res = requests.get(url, params=params, timeout=5).json()
        for update in res.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "").strip()

            if not text:
                continue

            if text.lower() in ["/stop", "/kill", "/pause", "stop", "kill"]:
                if running_proc and running_proc.poll() is None:
                    running_proc.terminate()
                    try:
                        running_proc.kill()
                    except Exception:
                        pass
                    running_proc = None
                    if os.path.exists(r"D:\youtube_automation_agent\.pipeline.lock"):
                        try:
                            os.remove(r"D:\youtube_automation_agent\.pipeline.lock")
                        except Exception:
                            pass
                    send_msg("🛑 *Voice generation / pipeline process stopped completely!*")
                else:
                    send_msg("No active pipeline process currently running.")
                continue

            if text.lower() in ["/help", "help"]:
                help_msg = (
                    "🤖 *YouTube Automation Agent — All Commands*\n\n"
                    "🚀 *Pipeline Execution:*\n"
                    "• `/start` or `/run` — Launch/start the video pipeline\n"
                    "• `/retry` or `/resume` — Resume/retry the current pipeline step\n"
                    "• `/stop` or `/kill` — Emergency stop & kill active process immediately\n\n"
                    "🎙️ *Voice Generation & Colab:*\n"
                    "• `/voice` — Trigger Step 8 Voice Generation Menu\n"
                    "• `/colab <URL>` — Set Colab GPU URL (e.g. `/colab https://xxxx.gradio.live`)\n"
                    "• 📦 Attach `07_Voice.zip` — Directly upload voice zip into chat\n\n"
                    "✏️ *Script & Image Controls:*\n"
                    "• `/start_video <topic>` — Start new project with custom topic\n"
                    "• `/rewrite` — Reset pipeline to Step 4 (Script Writing)\n"
                    "• `/unapprove <num>` — Reject a scene image (e.g. `/unapprove 12`)\n"
                    "• `/reset` — Reset project state to step 1\n"
                )
                send_msg(help_msg)
                continue

            # If youtube_agent is running, check if process died, but DON'T poll getUpdates to avoid stealing inline button callbacks
            if running_proc and running_proc.poll() is None:
                time.sleep(1)
                continue

            print(f"[Command Received]: {text}")
            
            # Change directory command handling
            if text.lower().startswith("cd "):
                new_dir = text[3:].strip()
                target = os.path.abspath(os.path.join(current_cwd, new_dir))
                if os.path.exists(target) and os.path.isdir(target):
                    current_cwd = target
                    send_msg(f"Directory changed to: {current_cwd}")
                else:
                    send_msg(f"Directory not found: {target}")
                continue
            elif text.lower() in ["d:", "c:", "e:"]:
                drive = text.upper() + "\\"
                if os.path.exists(drive):
                    current_cwd = drive
                    send_msg(f"Switched drive to: {current_cwd}")
                continue
            
            # Colab URL configuration command
            if text.lower().startswith("/colab "):
                colab_url = text[7:].strip()
                env_path = r"D:\youtube_automation_agent\.env"
                lines = []
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        lines = [l for l in f.readlines() if not l.startswith("COLAB_URL=")]
                lines.append(f"COLAB_URL={colab_url}\n")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                send_msg(f"✅ *Colab GPU URL set to:* `{colab_url}`\nAll voice cloning for `{colab_url}` will now render on Google Colab GPU in your reference voice (`reference_voice.wav`)!")
                continue

            # Execute command in CMD
            send_msg(f"⚡ Executing in [{current_cwd}]:\n{text}")
            
            if any(kw in text.lower() for kw in ["youtube_agent.py", "/run", "/start", "/active", "active", "/retry", "/retry_audio", "/voice", "/resume"]):
                cmd = f'cd /d "{current_cwd}" && python -u D:\\youtube_automation_agent\\youtube_agent.py'
                running_proc = subprocess.Popen(cmd, shell=True, cwd=current_cwd)
                send_msg("🚀 youtube_agent.py launched/resumed!")

            else:
                cmd_full = f'cd /d "{current_cwd}" && {text}'
                proc = subprocess.run(cmd_full, shell=True, capture_output=True, text=True, timeout=60)
                out = proc.stdout if proc.stdout else proc.stderr
                send_msg(out if out else "[Command completed with no output]")
                
    except Exception as e:
        time.sleep(3)
    time.sleep(1)
