import os
import time
import json
import requests
from dotenv import load_dotenv

# Load variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def is_telegram_configured():
    """Checks if Telegram configuration is available in .env."""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

def flush_updates():
    """Flushes all pending updates from Telegram's queue so we don't process old messages."""
    if not is_telegram_configured():
        return
    if os.environ.get("PIPELINE_RESTARTED") == "1":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        # Get the latest update to find the offset
        response = requests.get(url, params={"limit": 1, "offset": -1, "timeout": 5}, timeout=10)
        if response.status_code == 200:
            updates = response.json().get("result", [])
            if updates:
                latest_update_id = updates[0]["update_id"]
                # Acknowledge it by polling with offset = latest_update_id + 1
                requests.get(url, params={"offset": latest_update_id + 1, "limit": 1, "timeout": 1}, timeout=5)
                print("Telegram updates queue flushed successfully.")
    except Exception as e:
        print(f"[Telegram] Failed to flush updates: {e}")

def send_message(text, buttons=None):
    """
    Sends a text message to Telegram, optionally with inline buttons.
    Splits the message automatically if it exceeds Telegram's 4096-character limit.
    """
    if not is_telegram_configured():
        # CLI Fallback if Telegram not configured
        print(f"\n[Telegram MOCK] Message: {text}")
        if buttons:
            print("Options:")
            options = []
            for row in buttons:
                for btn in row:
                    options.append(btn["callback_data"])
                    print(f" - {btn['text']} ({btn['callback_data']})")
            val = input(f"Select option [{'/'.join(options)}]: ").strip().lower()
            return {"mock": True, "selected": val}
        return {"mock": True}

    if len(text) > 4000:
        import textwrap
        chunks = textwrap.wrap(text, width=4000, replace_whitespace=False)
        last_res = None
        for i, chunk in enumerate(chunks):
            is_last = (i == len(chunks) - 1)
            chunk_buttons = buttons if is_last else None
            last_res = _send_message_chunk(chunk, chunk_buttons)
        return last_res
    else:
        return _send_message_chunk(text, buttons)

def _send_message_chunk(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 400 and ("parse" in response.text.lower() or "entities" in response.text.lower()):
            # Fallback retry without markdown
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=20)
        if response.status_code != 200:
            print(f"[Telegram API Response] Status: {response.status_code}, Body: {response.text}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Telegram ERROR] Failed to send message: {e}")
        return None

def send_photo(photo_path, caption=None, buttons=None):
    """Sends a photo with optional caption and inline buttons."""
    if not is_telegram_configured():
        print(f"\n[Telegram MOCK] Sending Photo: {photo_path} (Caption: {caption})")
        if buttons:
            return send_message(caption or "Select an action:", buttons)
        return {"mock": True}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
    }
    if caption:
        # Telegram caption limit is 1024 characters. Truncate to 1000 to be safe.
        if len(caption) > 1000:
            caption = caption[:997] + "..."
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

    try:
        if isinstance(photo_path, str) and photo_path.startswith("http"):
            payload["photo"] = photo_path
            response = requests.post(url, json=payload, timeout=40)
            if response.status_code == 400:
                payload.pop("parse_mode", None)
                response = requests.post(url, json=payload, timeout=40)
            if response.status_code != 200:
                print(f"[Telegram API Response] sendPhoto Status: {response.status_code}, Body: {response.text}")
            response.raise_for_status()
            return response.json()
        else:
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                response = requests.post(url, data=payload, files=files, timeout=40)
                if response.status_code == 400:
                    if "caption" in payload:
                        payload["caption"] = payload["caption"][:200] + "..."
                    payload.pop("parse_mode", None)
                    f.seek(0)
                    response = requests.post(url, data=payload, files=files, timeout=40)
                if response.status_code != 200:
                    print(f"[Telegram API Response] sendPhoto Status: {response.status_code}, Body: {response.text}")
                response.raise_for_status()
                return response.json()
    except Exception as e:
        print(f"[Telegram ERROR] Failed to send photo: {e}")
def send_media_group(image_items):
    """
    Sends a batch album of up to 10 photos to Telegram in a single message.
    image_items: list of tuples (image_path, caption_str)
    Guarantees every image is sent: filters missing/empty files and falls back to individual send_photo if album fails.
    """
    if not is_telegram_configured():
        print(f"\n[Telegram MOCK] Sending Media Group: {len(image_items)} images")
        return {"mock": True}

    # Filter out missing or empty images
    valid_items = [item for item in image_items if os.path.exists(item[0]) and os.path.getsize(item[0]) >= 1000]
    if not valid_items:
        print("[Telegram WARNING] send_media_group: No valid image files to send!")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"

    media = []
    for i, (path, cap) in enumerate(valid_items):
        key = f"photo_{i}"
        m_item = {"type": "photo", "media": f"attach://{key}"}
        if cap:
            if len(cap) > 1000:
                cap = cap[:997] + "..."
            m_item["caption"] = cap
            m_item["parse_mode"] = "Markdown"
        media.append(m_item)

    try:
        response = None
        for attempt in range(2):
            opened_files = []
            try:
                files = {}
                for i, (path, _) in enumerate(valid_items):
                    key = f"photo_{i}"
                    f = open(path, "rb")
                    opened_files.append(f)
                    files[key] = f
                payload = {"chat_id": TELEGRAM_CHAT_ID, "media": json.dumps(media)}
                response = requests.post(url, data=payload, files=files, timeout=60)
            finally:
                for f in opened_files:
                    f.close()
            if response is None or response.status_code != 400:
                break
            # First 400: retry with plaintext captions (Markdown entity errors)
            for m_item in media:
                m_item.pop("parse_mode", None)
        if response is not None and response.status_code != 200:
            print(f"[Telegram API Response] sendMediaGroup Status: {response.status_code}, Body: {response.text}")
        if response is None:
            raise RuntimeError("sendMediaGroup returned no response")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Telegram ERROR] Failed to send media group album: {e}. Falling back to individual photo sending...")
        # Fallback: Send photos individually one by one so user sees every single image
        results = []
        for path, cap in valid_items:
            res = send_photo(path, caption=cap)
            if res:
                results.append(res)
            time.sleep(0.5)
        return results if results else None


def send_audio(audio_path, caption=None, buttons=None):
    """Sends an audio file with optional caption and inline buttons."""
    if not is_telegram_configured():
        print(f"\n[Telegram MOCK] Sending Audio: {audio_path} (Caption: {caption})")
        if buttons:
            return send_message(caption or "Select an action:", buttons)
        return {"mock": True}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
    }
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

    try:
        with open(audio_path, "rb") as f:
            files = {"audio": f}
            response = requests.post(url, data=payload, files=files, timeout=40)
            if response.status_code == 400 and "parse" in response.text.lower():
                payload.pop("parse_mode", None)
                f.seek(0)
                response = requests.post(url, data=payload, files=files, timeout=40)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[Telegram ERROR] Failed to send audio: {e}")
        return None

def send_document(file_path, caption=None, buttons=None):
    """Sends a document file with optional caption and inline buttons."""
    if not is_telegram_configured():
        print(f"\n[Telegram MOCK] Sending Document: {file_path} (Caption: {caption})")
        if buttons:
            return send_message(caption or "Select an action:", buttons)
        return {"mock": True}

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    payload = {"chat_id": TELEGRAM_CHAT_ID}
    if caption:
        # Telegram caption limit is 1024 characters. Truncate to 1000 to be safe.
        if len(caption) > 1000:
            caption = caption[:997] + "..."
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

    try:
        with open(file_path, "rb") as f:
            files = {"document": f}
            response = requests.post(url, data=payload, files=files, timeout=40)
            if response.status_code == 400:
                # Fallback: retry with plaintext and shorter caption
                if "caption" in payload:
                    payload["caption"] = payload["caption"][:200] + "..."
                payload.pop("parse_mode", None)
                f.seek(0)
                response = requests.post(url, data=payload, files=files, timeout=40)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[Telegram ERROR] Failed to send document: {e}")
        return None

LAST_TELEGRAM_OFFSET = None

def flush_telegram_updates():
    """Flushes and discards all pending Telegram updates from the bot queue."""
    global LAST_TELEGRAM_OFFSET

    if not is_telegram_configured():
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        res = requests.get(url, params={"limit": 1, "offset": -1}, timeout=5)
        if res.status_code == 200:
            results = res.json().get("result", [])
            if results:
                LAST_TELEGRAM_OFFSET = results[-1]["update_id"] + 1
                requests.get(url, params={"offset": LAST_TELEGRAM_OFFSET}, timeout=5)
                print(f"[Telegram] Flushed update queue up to offset {LAST_TELEGRAM_OFFSET}.")
    except Exception as e:
        print(f"[Telegram] Warning during update queue flush: {e}")

def wait_for_interaction(sent_message_result):
    """
    Blocks execution and polls Telegram getUpdates for an inline button click
    corresponding to the sent message, or any text message if sent_message_result is None.
    """
    global LAST_TELEGRAM_OFFSET
    if sent_message_result and isinstance(sent_message_result, dict) and sent_message_result.get("mock"):
        return sent_message_result.get("selected", "approve")

    valid_message_ids = set()
    if isinstance(sent_message_result, list):
        for r in sent_message_result:
            if isinstance(r, dict) and r.get("result", {}).get("message_id"):
                valid_message_ids.add(r["result"]["message_id"])
    elif isinstance(sent_message_result, dict) and sent_message_result.get("result", {}).get("message_id"):
        valid_message_ids.add(sent_message_result["result"]["message_id"])

    if valid_message_ids:
        print(f"Waiting for Telegram approval/interaction on message(s) {list(valid_message_ids)}...")
    else:
        print("Waiting for any Telegram text command/interaction...")

    # Always sync offset to the latest pending message (+1) so historical clicks NEVER auto-trigger!
    if LAST_TELEGRAM_OFFSET is None:
        flush_telegram_updates()


    offset = LAST_TELEGRAM_OFFSET

    # Ultra-responsive poll loop (1s timeout for instant button response)
    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 1}
        if offset:
            params["offset"] = offset

        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code != 200:
                time.sleep(0.2)
                continue
                
            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                LAST_TELEGRAM_OFFSET = offset
                
                # Check for callback buttons
                if "callback_query" in update:
                    cb = update["callback_query"]
                    callback_data = cb.get("data", "")
                    callback_query_id = cb.get("id")
                    
                    # Instantly stop loading spinner in Telegram UI
                    if callback_query_id:
                        ans_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
                        try:
                            requests.post(ans_url, json={"callback_query_id": callback_query_id}, timeout=3)
                        except Exception:
                            pass
                    
                    # Intercept global /reset, /retry, /rewrite callbacks from the help menu
                    if callback_data in ["/reset", "/retry", "/rewrite"]:
                        print(f"Telegram global interaction received: {callback_data}")
                    # Accept direct action taps (Approve, Reject, Regen, Title, Thumb) on ANY message or photo
                    is_direct_action = (
                        callback_data.startswith(("approve_", "reject_", "regen_", "skip_", "edit_", "title:")) or
                        callback_data in ["approve_all_batch", "approve_all", "regen_thumb", "approve_thumb", "reset_title_text"]
                    )

                    # For other non-action callbacks, enforce matching message ID to prevent old menu leaks
                    if valid_message_ids and not is_direct_action:
                        cb_msg = (cb.get("message") or {}).get("message_id")
                        if cb_msg not in valid_message_ids:
                            print(f"[Telegram] Ignoring stale tap '{callback_data}' on "
                                  f"message {cb_msg} (waiting on {sorted(valid_message_ids)}).")
                            continue

                    # Instantly accept any action callback button tap
                    if callback_data:
                        print(f"Telegram interaction received instantly: {callback_data}")
                        return callback_data

                # Fallback: Check if user sent a text reply or file document
                elif "message" in update:
                    msg = update["message"]
                    text = msg.get("text", "")
                    doc = msg.get("document")
                    if doc:
                        # Clear updates offset
                        requests.get(url, params={"offset": offset, "limit": 1})
                        file_id = doc.get("file_id")
                        file_name = doc.get("file_name", "")
                        try:
                            file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                            file_info = requests.get(file_info_url).json()
                            file_path = file_info.get("result", {}).get("file_path")
                            if file_path:
                                download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                                print(f"[Telegram] Downloading document ({file_name}) from {download_url}...")
                                r = requests.get(download_url, timeout=60)
                                r.raise_for_status()
                                
                                if file_name.endswith(".zip") or "07_Voice" in file_name:
                                    dl_zip_path = r"C:\Users\ASUS\Downloads\07_Voice.zip"
                                    with open(dl_zip_path, "wb") as zf:
                                        zf.write(r.content)
                                    print(f"[Telegram] Zip document saved to {dl_zip_path}")
                                    return "file_zip"
                                else:
                                    file_content = r.content.decode('utf-8', errors='ignore')
                                    print(f"[Telegram] Text document downloaded. Length: {len(file_content)} chars")
                                    return f"file:{file_content}"
                            else:
                                print(f"[Telegram ERROR] No file path returned for file_id: {file_id}")
                        except Exception as e:
                            print(f"[Telegram ERROR] Failed to download document: {e}")
                            send_message("❌ *Failed to download the attached file.* Please try again.")
                            continue
                            
                    if text:
                        # Clear updates offset
                        requests.get(url, params={"offset": offset, "limit": 1})
                        
                        # Intercept global help command
                        if text.strip().lower() in ["/help", "help"]:
                            help_text = (
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
                            help_buttons = [
                                [
                                    {"text": "🔄 Retry Step", "callback_data": "/retry"},
                                    {"text": "🛑 Stop Process", "callback_data": "/stop"}
                                ],
                                [
                                    {"text": "🎙️ Voice Menu", "callback_data": "/voice"},
                                    {"text": "✏️ Rewrite Script", "callback_data": "/rewrite"}
                                ]
                            ]
                            send_message(help_text, help_buttons)
                            continue
                            
                        print(f"Telegram text input received: {text}")
                        return f"text:{text}"

        except Exception as e:
            print(f"[Telegram ERROR] Exception during polling: {e}")
            time.sleep(5)

def wait_for_batch_interactions(sent_message_results):
    """
    Blocks execution and polls Telegram getUpdates for inline button clicks
    corresponding to ALL messages in the batch.
    Returns dict: {message_id: callback_data}
    """
    results = {}
    valid_results = [r for r in sent_message_results if r is not None]

    if not valid_results:
        return results

    # Handle mock mode
    if any(r.get("mock") for r in valid_results):
        for r in valid_results:
            mock_id = id(r)
            results[mock_id] = r.get("selected", "approve")
        return results

    # Build set of message_ids we're waiting on
    pending = {}
    for r in valid_results:
        msg_id = r.get("result", {}).get("message_id")
        if msg_id is not None:
            pending[msg_id] = True

    total = len(pending)
    if total == 0:
        return results

    print(f"Waiting for Telegram interactions on {total} messages...")

    offset = None
    while pending:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        params = {"timeout": 30}
        if offset:
            params["offset"] = offset

        try:
            response = requests.get(url, params=params, timeout=45)
            if response.status_code != 200:
                time.sleep(5)
                continue

            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1

                if "callback_query" in update:
                    cb = update["callback_query"]
                    cb_msg = cb.get("message", {})
                    cb_msg_id = cb_msg.get("message_id")

                    if cb_msg_id in pending:
                        callback_data = cb["data"]
                        callback_query_id = cb["id"]

                        ans_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
                        requests.post(ans_url, json={"callback_query_id": callback_query_id})

                        results[cb_msg_id] = callback_data
                        del pending[cb_msg_id]
                        reviewed = total - len(pending)
                        print(f"Batch progress: {reviewed}/{total} images reviewed...")

                elif "message" in update:
                    msg = update["message"]
                    text = msg.get("text", "")
                    if text and pending:
                        first_pending_id = next(iter(pending))
                        results[first_pending_id] = f"text:{text}"
                        del pending[first_pending_id]
                        reviewed = total - len(pending)
                        print(f"Batch progress: {reviewed}/{total} images reviewed...")

        except Exception as e:
            print(f"[Telegram ERROR] Exception during batch polling: {e}")
            time.sleep(5)

    print(f"All {total} interactions received.")
    return results

if __name__ == "__main__":
    # Test script locally or over Telegram
    if not is_telegram_configured():
        print("Telegram bot credentials not found in .env. Running CLI mock test.")
        test_buttons = [[
            {"text": "Option A", "callback_data": "a"},
            {"text": "Option B", "callback_data": "b"}
        ]]
        res = send_message("Mock selection test", test_buttons)
        choice = wait_for_interaction(res)
        print(f"You selected: {choice}")
    else:
        print("Running Telegram active bot test...")
        test_buttons = [[
            {"text": "Approve", "callback_data": "approve"},
            {"text": "Reject", "callback_data": "reject"}
        ]]
        res = send_message("*Testing YouTube Automation Bot*\nDo you approve this test?", test_buttons)
        if res:
            choice = wait_for_interaction(res)
            send_message(f"Test confirmed. You clicked: *{choice}*")
        else:
            print("Test failed. Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env.")
