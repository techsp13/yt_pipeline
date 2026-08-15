import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set.")
        return
        
    try:
        client = genai.Client(api_key=api_key)
        print("Listing available models from Gemini API...")
        
        # In the new google-genai SDK, we list models using client.models.list()
        for m in client.models.list():
            print(f"Name: {m.name}, Supported Actions: {m.supported_actions}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
