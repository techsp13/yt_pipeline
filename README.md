# Sany Explorer — Automated Video Pipeline

This project contains the unified Python scripts to generate high-quality video animations for Sany Explorer using:
- **ElevenLabs** for voiceover generation (with automatic multi-account API key rotation).
- **fal.ai (Recraft V3)** for generating premium, consistent 2D vector doodle images.
- **ffmpeg** (via `imageio-ffmpeg`) for high-performance audio/image sync and burning in clean captions.

---

## 1. Setup & Installation

### Step 1: Install Dependencies
Ensure you have run:
```bash
pip install requests python-dotenv imageio-ffmpeg fal-client
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` in the `sany_explorer` folder and fill in the values:
```env
# ElevenLabs API Keys (Comma-separated list for rotation)
ELEVENLABS_API_KEYS=key1,key2,key3

# ElevenLabs Voice Configuration
# NOTE FOR FREE PLAN USERS: ElevenLabs blocks premade/library voices (like "Rachel" or "Adam") via the API.
# You must create a voice using the "Voice Design" tool on the website, and copy its custom Voice ID here.
ELEVENLABS_VOICE_ID=your_designed_voice_id

# fal.ai API Key (Get from fal.ai for Recraft V3)
FAL_KEY=your_fal_key_here

# Telegram Bot Configuration (for n8n approvals)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

---

## 2. Running the Pipeline

To run the complete assembly pipeline manually:
```bash
python assemble_video.py <scene_breakdown_file> <output_directory> [final_video_name.mp4]
```
Example:
```bash
python assemble_video.py test_breakdown.txt C:\Users\ASUS\kokoro\output_video final_video.mp4
```

### Incremental Resuming
The script has **resume support built-in**: if `V01.mp3` or `V01.png` already exist in the output directory, it skips re-generating them, saving you characters on ElevenLabs and credits on fal.ai. If you want to force regeneration, simply delete the files from the output folder.

---

## 3. n8n Integration

Instead of complex binary processing in JavaScript nodes, configure your n8n workflow to run the Python script:

```
[Gemini Scene Breakdown Output] 
   └── [Write Breakdown to disk: C:\Users\ASUS\kokoro\scene_breakdown.txt]
         └── [Execute Command Node]
```

**Execute Command Node Settings:**
- **Command:** `python C:\Users\ASUS\.gemini\antigravity\scratch\sany_explorer\assemble_video.py C:\Users\ASUS\kokoro\scene_breakdown.txt C:\Users\ASUS\kokoro\output_video final_video.mp4`

---

## 4. Telegram Approval Bot in n8n

To add approval checkpoints directly in n8n:

1. **Send Video for Approval**:
   - Add a **Read/Write Files from Disk** node in n8n after the script completes to read `C:\Users\ASUS\kokoro\output_video\final_video.mp4`.
   - Add a **Telegram Node**:
     - **Resource**: Chat
     - **Operation**: Send Video
     - **Chat ID**: your Chat ID (or environment variable)
     - **Video**: select the binary data from the read file node
     - **Reply Markup**: Select `Inline Keyboard` and input:
       ```json
       {
         "inline_keyboard": [
           [
             { "text": "✅ Approve & Publish", "callback_data": "approve" },
             { "text": "❌ Reject", "callback_data": "reject" }
           ]
         ]
       }
       ```

2. **Handle Response (Telegram Trigger)**:
   - Add a **Telegram Trigger** node set to trigger on **Callback Query**.
   - Connect it to an **If Node**:
     - Check if the callback query data is equal to `approve`.
     - **True**: Proceed with uploading to YouTube/TikTok.
     - **False**: Send a message back stating "Video rejected, pipeline stopped."
