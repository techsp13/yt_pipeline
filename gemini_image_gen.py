import os
import io
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

# Load environment variables
load_dotenv()

def generate_image_gemini(prompt, filename, aspect_ratio="16:9"):
    """
    Generates an image using Gemini 3.1 Flash Image model via the Gemini API (Free Tier compatible).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your .env file.")

    print(f"Sending prompt to gemini-3.1-flash-image: {prompt}")
    
    try:
        # Initialize GenAI client
        client = genai.Client(api_key=api_key)
        
        # Call generate_content specifying that we want text and image modalities
        response = client.models.generate_content(
            model='gemini-2.5-flash-image',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE]
            )
        )
        
        # Extract the binary image data from the parts
        image_data = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    break
        
        if not image_data:
            print("No image data was returned in the Gemini response parts.")
            if response.text:
                print(f"Response text: {response.text}")
            return False
            
        # Load and save the image
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        image = Image.open(io.BytesIO(image_data))
        image.save(filename)
        print(f"Saved image to {filename} (Format: {image.format}, Size: {image.size})")
        return True
        
    except Exception as e:
        print(f"Error during Gemini image generation: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python gemini_image_gen.py <prompt> <output_path>")
        sys.exit(1)
        
    prompt_arg = sys.argv[1]
    output_arg = sys.argv[2]
    
    # Custom test suffix
    test_prompt = prompt_arg + ", simple 2D flat cartoon illustration style, thick black outlines, flat solid colors, solid background, no shading"
    generate_image_gemini(test_prompt, output_arg)
