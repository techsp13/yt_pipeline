"""
pipeline_watchdog.py
====================
Autonomous Self-Healing Supervisor Daemon for YouTube Automation Agent.

Guarantees 24/7 Uninterrupted Operation:
1. Cleans stale locks (.pipeline.lock, playwright profile locks) automatically.
2. Keeps youtube_agent.py running continuously without human intervention.
3. Automatically restarts from the last saved checkpoint on crashes, reboots, or internet drops.
4. Alerts Telegram on recovery events.
"""

import os
import sys
import time
import subprocess
import json

# Crucial Windows Console Encoding Guard: Prevent CP1252 charmap crashes on emojis/unicode
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

AGENT_DIR = r"D:\youtube_automation_agent"
sys.path.insert(0, AGENT_DIR)

LOCK_FILE = os.path.join(AGENT_DIR, ".pipeline.lock")
LOG_FILE = os.path.join(AGENT_DIR, "watchdog.log")

def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t}] [WATCHDOG] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        try:
            print(line.encode("ascii", errors="replace").decode("ascii"), flush=True)
        except Exception:
            pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def notify_telegram(msg):
    try:
        import telegram_bot
        telegram_bot.send_message(msg)
    except Exception as e:
        log(f"Telegram notice failed: {e}")

def is_pid_alive(pid):
    try:
        pid = int(pid)
        if pid <= 0:
            return False
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False

def clean_stale_locks():
    # 1. Clean .pipeline.lock if process is dead
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                holder = f.read().strip()
            if not holder or not holder.isdigit() or not is_pid_alive(holder):
                os.remove(LOCK_FILE)
                log(f"Cleaned stale pipeline lock (dead PID: {holder}).")
        except Exception as e:
            try:
                os.remove(LOCK_FILE)
                log(f"Forced removal of pipeline lock: {e}")
            except Exception:
                pass

    # 2. Clean playwright browser profile locks (strict top-level singleton locks only)
    profiles_dir = os.path.join(AGENT_DIR, ".gflow", "profiles")
    if os.path.exists(profiles_dir):
        try:
            for entry in os.listdir(profiles_dir):
                prof_path = os.path.join(profiles_dir, entry)
                if os.path.isdir(prof_path):
                    for lf in ["SingletonLock", "SingletonCookie", "SingletonSocket", "DevToolsActivePort", "LOCK"]:
                        lp = os.path.join(prof_path, lf)
                        if os.path.exists(lp):
                            try:
                                os.remove(lp)
                                log(f"Cleaned stale browser profile lock: {entry}/{lf}")
                            except Exception:
                                pass
        except Exception:
            pass

def check_internet():
    try:
        import socket
        socket.create_connection(("1.1.1.1", 53), timeout=3)
        return True
    except Exception:
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception:
            return False

def run_supervisor():
    log("=" * 60)
    log("  AUTONOMOUS PIPELINE WATCHDOG DAEMON STARTED")
    log("=" * 60)

    notify_telegram("🛡️ *Pipeline Watchdog Daemon Online!*\nThe automation agent is running with full self-healing & auto-restart enabled.")

    restart_count = 0

    while True:
        # Ensure internet is connected
        if not check_internet():
            log("Internet disconnected. Waiting for connection...")
            while not check_internet():
                time.sleep(10)
            log("Internet restored.")

        clean_stale_locks()

        log("Launching youtube_agent.py...")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["AUTONOMOUS_MODE"] = "1"

        proc = None
        try:
            proc = subprocess.Popen(
                [sys.executable, "-u", os.path.join(AGENT_DIR, "youtube_agent.py")],
                cwd=AGENT_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            # Stream output to watchdog log with safe encoding
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    try:
                        print(f"[Agent] {line_str}", flush=True)
                    except Exception:
                        try:
                            print(f"[Agent] {line_str.encode('ascii', errors='replace').decode('ascii')}", flush=True)
                        except Exception:
                            pass
                    try:
                        with open(LOG_FILE, "a", encoding="utf-8") as f:
                            f.write(f"[{time.strftime('%H:%M:%S')}] {line_str}\n")
                    except Exception:
                        pass

            proc.wait()
            rc = proc.returncode
            log(f"Agent process exited with code {rc}.")

            if rc == 0:
                log("Agent completed task normally or handed off. Restarting in 5s for standing loop...")
                time.sleep(5)
            else:
                restart_count += 1
                log(f"Crash detected (Exit code {rc}). Auto-restarting attempt #{restart_count} in 5s...")
                notify_telegram(
                    f"⚠️ *Pipeline Auto-Recovered:* Agent exited unexpectedly (code `{rc}`). "
                    f"Auto-resuming from last checkpoint in 5 seconds..."
                )
                time.sleep(5)

        except KeyboardInterrupt:
            log("Watchdog received KeyboardInterrupt. Exiting.")
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
            break
        except Exception as e:
            log(f"Watchdog exception: {e}. Retrying in 10s...")
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
            time.sleep(10)

if __name__ == "__main__":
    run_supervisor()
