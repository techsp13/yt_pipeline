import os
import sys
from dotenv import load_dotenv

sys.path.append(r"D:\youtube_automation_agent")
from hf_image_gen import _generate_image_via_workers, generate_image_hf

# Artifacts output directory
art_dir = r"C:\Users\ASUS\.gemini\antigravity\brain\e8efb994-11f5-42d4-9b99-16f171d44f2c"

# 1. Logo Prompt (Square 1:1)
logo_prompt = (
    "A cute minimalist 2D flat cartoon YouTube logo avatar on a vibrant split mint-green and light-tan background. "
    "Features a cute minimalist stick figure with a round white circular head, stylish short black hair, simple black dot eyes, and a happy smile, wearing a green hoodie with a white dollar sign. "
    "Clean thick black marker outlines, flat solid colors, cute doodle style, 100% flat vector webcomic illustration, no 3D, no shading."
)

# 2. Cover / Banner Prompt (16:9)
banner_prompt = (
    "A cute minimalist 2D flat cartoon YouTube channel cover banner illustration on a vibrant split pastel mint-green and light-tan background. "
    "In the center, cute bold hand-drawn text says RICH SANY with thick clean black outlines. "
    "Surrounding the text are cute minimalist stick figures wearing green dollar hoodies, standing next to cute colorful doodles of piggy banks, gold coins, vault doors, and cash stacks. "
    "Clean thick black marker outlines, flat solid color fills, 100% flat vector webcomic illustration, no 3D, no shading."
)

logo_path = os.path.join(art_dir, "logo_rich_sany.png")
banner_path = os.path.join(art_dir, "banner_rich_sany.png")

print("Generating YouTube Logo for Rich Sany (1024x1024 Square)...")
success_logo = _generate_image_via_workers(logo_prompt, logo_path, width=1024, height=1024, label="Logo")

print("Generating YouTube Banner for Rich Sany (1024x576 16:9)...")
success_banner = generate_image_hf(banner_prompt, banner_path)

print(f"Logo result: {success_logo}")
print(f"Banner result: {success_banner}")
