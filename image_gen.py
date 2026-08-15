import os
import requests
import fal_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# fal_client automatically reads FAL_KEY from os.environ after load_dotenv() is called.

def generate_image(prompt, filename, style="vector_illustration", image_size="landscape_16_9"):
    """
    Generates an image using fal.ai Recraft V3 model and saves it to disk.
    """
    if not os.getenv("FAL_KEY"):
        raise ValueError("FAL_KEY environment variable is not set. Please add it to your .env file.")

    print(f"Sending prompt to fal.ai (Recraft v3, Style: {style}): {prompt}")
    
    try:
        # Submit the request to fal.ai
        handler = fal_client.subscribe(
            "fal-ai/recraft/v3/text-to-image",
            arguments={
                "prompt": prompt,
                "style": style,
                "image_size": image_size
            },
            with_logs=True
        )
        
        # Extract the image URL
        images = handler.get("images", [])
        if not images:
            print("No images returned from fal.ai.")
            return False
            
        image_url = images[0].get("url")
        print(f"Image generated successfully. Downloading from: {image_url}")
        
        # Download the file
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Saved image to {filename} (Size: {len(response.content)} bytes)")
            return True
        else:
            print(f"Failed to download image. Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Error during image generation: {e}")
        return False

if __name__ == "__main__":
    # Test script if run directly
    import sys
    if len(sys.argv) < 3:
        print("Usage: python image_gen.py <prompt> <output_path>")
        sys.exit(1)
        
    prompt_arg = sys.argv[1]
    output_arg = sys.argv[2]
    
    # Custom test suffix if needed
    test_prompt = prompt_arg + ", clean simple hand-drawn cartoon doodle, solid color background, webcomic style"
    generate_image(test_prompt, output_arg)
