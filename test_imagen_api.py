import os
import sys
import creative_assistant
from google import genai
from google.genai import types

keys = creative_assistant.load_all_gemini_keys()
print(f"Loaded {len(keys)} Gemini API keys.")

prompt = "Minimalist cute 2D flat cartoon space science doodle style illustration of a stick figure with curly black afro hair and black hoodie in space, 16:9 aspect ratio."
output_path = r"D:\youtube_automation_agent\test_imagen_direct.png"

success = False
for key in keys:
    try:
        print(f"Testing key {key[:15]}...")
        client = genai.Client(api_key=key)
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                output_mime_type="image/png"
            )
        )
        if response.generated_images:
            image = response.generated_images[0].image
            image.save(output_path)
            print(f"SUCCESS! Saved direct Imagen image to: {output_path}")
            success = True
            break
    except Exception as e:
        print(f"Key error: {e}")

if not success:
    print("Imagen API test failed.")
