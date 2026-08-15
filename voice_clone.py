import torch
import torchaudio
import os
import types

# ── Patch resemble-perth watermarker before importing chatterbox ──────────
# The watermarker is used for audio watermarking only — it is NOT needed
# for voice generation. This patch prevents the NoneType crash on Windows.
import sys
perth_mock = types.ModuleType("perth")

class _NoopWatermarker:
    def __init__(self, *a, **kw): pass
    def apply_watermark(self, wav, *a, **kw): return wav

perth_mock.PerthImplicitWatermarker = _NoopWatermarker
sys.modules["perth"] = perth_mock
# ─────────────────────────────────────────────────────────────────────────

def clone_voice(text, reference_wav, output_path, exaggeration=0.5, cfg_weight=0.5):
    """
    Clones a voice from a reference WAV file and generates speech.

    Args:
        text:           The narration text to speak.
        reference_wav:  Path to the reference WAV audio (10-30s clean recording).
        output_path:    Where to save the output WAV file.
        exaggeration:   0.0-1.0 — how strongly to clone the emotion/style (default 0.5)
        cfg_weight:     0.0-1.0 — lower = more similar to reference (default 0.5)
    """
    from chatterbox.tts import ChatterboxTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    print("Loading Chatterbox TTS model (downloads ~1GB on first run)...")

    model = ChatterboxTTS.from_pretrained(device=device)

    print(f"Cloning voice from: {reference_wav}")
    print(f"Generating: \"{text}\"")

    wav = model.generate(
        text,
        audio_prompt_path=reference_wav,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
    )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    torchaudio.save(output_path, wav, model.sr)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Saved to: {output_path} ({size_kb:.1f} KB)")
    return output_path


if __name__ == "__main__":
    os.makedirs(r"C:\Users\ASUS\kokoro\voice_test", exist_ok=True)

    test_lines = [
        {
            "text": "Are we actually aliens on our own planet? The answer might shock you.",
            "output": r"C:\Users\ASUS\kokoro\voice_test\clone_test_1.wav"
        },
        {
            "text": "Around one million years ago, our ancestors discovered fire. And that changed everything.",
            "output": r"C:\Users\ASUS\kokoro\voice_test\clone_test_2.wav"
        },
    ]

    reference = r"C:\Users\ASUS\.gemini\antigravity\scratch\sany_explorer\reference_voice.wav"

    for item in test_lines:
        clone_voice(
            text=item["text"],
            reference_wav=reference,
            output_path=item["output"],
            exaggeration=0.5,
            cfg_weight=0.5,
        )
        print()

    print("Done! Listen to cloned voice samples at:")
    print("  C:\\Users\\ASUS\\kokoro\\voice_test\\")
