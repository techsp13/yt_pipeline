# =======================================================
# 🚀 AUTOMATED GOOGLE COLAB GPU VOICE SERVER
# =======================================================
# 1. Open https://colab.research.google.com/
# 2. Select "T4 GPU" (Runtime -> Change runtime type -> T4 GPU)
# 3. Paste and Run this cell!
# 4. Copy the "public URL" (e.g. https://xxxx.gradio.live) and send it on Telegram as:
#    COLAB_URL = https://xxxx.gradio.live

!pip install --no-deps chatterbox-tts
!pip install librosa torchaudio transformers diffusers pykakasi pyloudnorm s3tokenizer conformer resemble-perth gradio

import os
import json
import torch
import torchaudio
import gradio as gr
from chatterbox.tts import ChatterboxTTS

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🚀 Loading Chatterbox Voice Cloning Engine on GPU: {device.upper()}...")
model = ChatterboxTTS.from_pretrained(device=device)

def process_voice_batch(payload_file, ref_file):
    os.makedirs("07_Voice", exist_ok=True)
    with open(payload_file.name, "r", encoding="utf-8") as f:
        scenes = json.load(f)
    
    ref_path = ref_file.name
    total = len(scenes)
    print(f"🎙️ Starting GPU Voice Synthesis for {total} scenes...")
    
    for idx, item in enumerate(scenes, 1):
        scene_name = item["scene"]
        text = item["narration"]
        out_wav = f"07_Voice/{scene_name}_Voice.wav"
        out_mp3 = f"07_Voice/{scene_name}_Voice.mp3"
        
        print(f"[{idx}/{total}] Synthesizing {scene_name}...")
        wav = model.generate(text, audio_prompt_path=ref_path)
        torchaudio.save(out_wav, wav, model.sr)
        
        os.system(f"ffmpeg -y -i {out_wav} -q:a 2 {out_mp3} -loglevel quiet")
        if os.path.exists(out_wav):
            os.remove(out_wav)
            
    zip_path = "07_Voice.zip"
    os.system("zip -r 07_Voice.zip 07_Voice")
    print(f"🎉 DONE! Generated {total} voice files in 07_Voice.zip")
    return zip_path

demo = gr.Interface(
    fn=process_voice_batch,
    inputs=[gr.File(label="scenes_payload.json"), gr.File(label="reference_voice.wav")],
    outputs=gr.File(label="07_Voice.zip"),
    title="Colab GPU Voice Cloning Server"
)

demo.launch(share=True)
