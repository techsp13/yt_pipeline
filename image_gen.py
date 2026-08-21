import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def generate_image(prompt, filename, style="vector_illustration", image_size="landscape_16_9", aspect_ratio="16:9"):
    """
    Generates an image using Google Flow Imagen (gflow) with fallback to Cloudflare Workers.
    """
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    # Map image_size / aspect_ratio
    if "portrait" in str(image_size).lower() or aspect_ratio == "9:16":
        aspect = "9:16"
    elif "square" in str(image_size).lower() or aspect_ratio == "1:1":
        aspect = "1:1"
    else:
        aspect = "16:9"

    print(f"[image_gen] Generating image via gflow (Aspect: {aspect}): {prompt[:80]}...")
    try:
        from gflow_assistant import generate_imagen_image
        success = generate_imagen_image(prompt, filename, aspect_ratio=aspect)
        if success and os.path.exists(filename) and os.path.getsize(filename) > 1000:
            print(f"[image_gen] ✅ Successfully generated via gflow -> {filename}")
            return True
    except Exception as e:
        print(f"[image_gen] ⚠️ gflow error: {e}. Falling back to Cloudflare...")

    # Fallback to Cloudflare Workers
    try:
        from hf_image_gen import generate_image_hf
        print(f"[image_gen] 🔄 Generating via Cloudflare Workers fallback...")
        generate_image_hf(prompt, filename, aspect_ratio=aspect)
        if os.path.exists(filename) and os.path.getsize(filename) > 1000:
            print(f"[image_gen] ✅ Successfully generated via Cloudflare fallback -> {filename}")
            return True
    except Exception as e:
        print(f"[image_gen] ❌ Cloudflare fallback error: {e}")

    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python image_gen.py <prompt> <output_path> [aspect_ratio]")
        sys.exit(1)
        
    prompt_arg = sys.argv[1]
    output_arg = sys.argv[2]
    aspect_arg = sys.argv[3] if len(sys.argv) > 3 else "16:9"
    generate_image(prompt_arg, output_arg, aspect_ratio=aspect_arg)

