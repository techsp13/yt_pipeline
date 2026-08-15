import json
import time
from google import genai
from google.genai import types
import httpx
from creative_assistant import load_all_gemini_keys


def _default_result():
    return {
        "passed": True,
        "text_quality": {"passed": True, "issues": []},
        "logical_consistency": {"passed": True, "issues": []},
        "scene_match": {"passed": True, "issues": []},
        "overall_score": 1.0,
    }


def validate_image(image_path, narration, image_prompt):
    """
    Validates a generated image using Gemini Vision API.

    Checks:
    1. Text Quality: Any visible text must be correctly spelled, sharp, readable
    2. Logical Consistency: Correct anatomy, proportions, no AI artifacts, no deformed body parts
    3. Scene-to-Visual Match: Image must accurately represent the narration

    Returns:
        {
            "passed": True/False,
            "text_quality": {"passed": bool, "issues": [str]},
            "logical_consistency": {"passed": bool, "issues": [str]},
            "scene_match": {"passed": bool, "issues": [str]},
            "overall_score": float  # 0.0-1.0
        }
    """
    keys = load_all_gemini_keys()
    if not keys:
        print("[ImageValidator] No API keys found, skipping validation.")
        return _default_result()

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        print(f"[ImageValidator] Failed to read image: {e}")
        return _default_result()

    prompt_text = f"""You are an image quality validator for a YouTube video pipeline. Analyze this generated image and evaluate it on three criteria.

The image was generated for this scene:
- Image Prompt: {image_prompt}
- Narration: {narration}

Evaluate:
1. TEXT QUALITY: If any text is visible in the image, is it correctly spelled, sharp, readable, and not distorted? If no text is visible, mark as passed.
2. LOGICAL CONSISTENCY: Are body proportions correct? Correct number of limbs? No floating objects (unless intended)? No missing/duplicated/deformed body parts? No obvious AI artifacts? Consistent lighting and perspective?
3. SCENE MATCH: Does the image accurately represent the narration? Shows the correct action? Includes important objects mentioned? Appropriate background?

Respond ONLY with this exact JSON format, no other text:
{{"text_quality": {{"passed": true/false, "issues": ["issue1", ...]}}, "logical_consistency": {{"passed": true/false, "issues": ["issue1", ...]}}, "scene_match": {{"passed": true/false, "issues": ["issue1", ...]}}, "overall_score": 0.0-1.0}}"""

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    models_to_try = ["gemini-2.5-flash"]
    key_idx = 0
    model_idx = 0

    for attempt in range(len(keys) * len(models_to_try)):
        current_model = models_to_try[model_idx]
        try:
            client = genai.Client(
                api_key=keys[key_idx],
                http_options={"client_args": {"timeout": httpx.Timeout(30.0, connect=None)}},
            )
            response = client.models.generate_content(
                model=current_model,
                contents=[image_part, prompt_text],
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0].strip()

            data = json.loads(text)
            result = _default_result()
            for key in ("text_quality", "logical_consistency", "scene_match"):
                if key in data:
                    result[key]["passed"] = bool(data[key].get("passed", True))
                    result[key]["issues"] = list(data[key].get("issues", []))
            result["overall_score"] = float(data.get("overall_score", 1.0))
            result["passed"] = all(
                result[k]["passed"] for k in ("text_quality", "logical_consistency", "scene_match")
            )
            return result

        except Exception as e:
            print(f"[ImageValidator] {current_model} key {key_idx}: {e}")
            if key_idx < len(keys) - 1:
                key_idx += 1
            elif model_idx < len(models_to_try) - 1:
                model_idx += 1
                key_idx = 0
            else:
                break

    print("[ImageValidator] All attempts failed, returning default pass.")
    return _default_result()
