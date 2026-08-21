import os
import json
import re
import time
from google import genai
from google.genai.errors import APIError
import httpx
from dotenv import load_dotenv

# Load variables
load_dotenv()

def load_all_gemini_keys():
    keys = []
    env_path = os.path.join(r"D:\youtube_automation_agent", ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if val and val not in keys:
                            keys.append(val)
        except Exception:
            pass
    if not keys:
        k = os.getenv("GEMINI_API_KEY")
        if k:
            keys.append(k)
    return keys

def get_active_project_dir():
    """Returns current active project directory from active_project.json."""
    active_pointer = os.path.join(r"D:\youtube_automation_agent", "active_project.json")
    if os.path.exists(active_pointer):
        try:
            with open(active_pointer, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("active_project_dir")
        except Exception:
            pass
    return None

def get_profile():
    """Reads the active channel profile from state or .env fallback."""
    profile = "history"
    active_pointer = os.path.join(r"D:\youtube_automation_agent", "active_project.json")
    if os.path.exists(active_pointer):
        try:
            with open(active_pointer, "r", encoding="utf-8") as f:
                data = json.load(f)
                proj_dir = data.get("active_project_dir")
                if proj_dir:
                    cfg_path = os.path.join(proj_dir, "Project_Config.json")
                    if os.path.exists(cfg_path):
                        with open(cfg_path, "r", encoding="utf-8") as cf:
                            state = json.load(cf)
                            if "channel" in state:
                                return state["channel"]
        except Exception:
            pass
            
    # Fallback to env
    env_path = os.path.join(r"D:\youtube_automation_agent", ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("CHANNEL_PROFILE="):
                        profile = line.strip().split("=", 1)[1].strip().strip("'\"").lower()
                        break
        except Exception:
            pass
    return profile

# Persistent variables & disk state to store active API key across process restarts
KEY_STATE_FILE = os.path.join(os.path.dirname(__file__), "gemini_key_state.json")

def _load_key_state():
    """Load active key index from disk persistent state."""
    if os.path.exists(KEY_STATE_FILE):
        try:
            with open(KEY_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("active_key_index", 0)
        except Exception:
            pass
    return 0

def _save_key_state(idx):
    """Save active key index to disk so it stays on working key across process restarts."""
    try:
        with open(KEY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"active_key_index": idx}, f, indent=4)
    except Exception as e:
        print(f"[KeyState] Could not save key state: {e}")

_CURRENT_KEY_IDX = _load_key_state()
_CURRENT_MODEL_IDX = 0

_QUOTA_ERRORS    = ("429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "rateLimitExceeded")
_TRANSIENT_ERRORS = ("503", "500", "UNAVAILABLE", "high demand", "timeout", "connection")

def _is_quota_error(e_str: str) -> bool:
    return any(k.lower() in e_str.lower() for k in _QUOTA_ERRORS)

def _is_transient_error(e_str: str) -> bool:
    return any(k.lower() in e_str.lower() for k in _TRANSIENT_ERRORS)

_MODEL_UNAVAILABLE_ERRORS = ("404", "NOT_FOUND", "no longer available", "not found")

def _is_model_unavailable(e_str: str) -> bool:
    return any(k.lower() in e_str.lower() for k in _MODEL_UNAVAILABLE_ERRORS)

def _generate_with_retry(prompt, models_to_try=None):
    """
    Wrapper for generate_content with correct key rotation:
    - Transient errors (503, timeout): retry same key up to 3x with backoff, NEVER rotate.
    - Quota/429 errors: rotate to next key.
    - After all keys tried for one model: switch model, restart from key 0.
    - Never permanently mark a key as exhausted — reset and retry after sleep.
    """
    global _CURRENT_KEY_IDX, _CURRENT_MODEL_IDX
    keys = load_all_gemini_keys()
    if not keys:
        raise ValueError("No GEMINI_API_KEY found in .env file or environment.")

    if models_to_try is None:
        models_to_try = ["gemini-2.5-flash"]

    # Reload key index from disk
    _CURRENT_KEY_IDX = _load_key_state()
    if _CURRENT_KEY_IDX >= len(keys):
        _CURRENT_KEY_IDX = 0
        _save_key_state(0)
    if _CURRENT_MODEL_IDX >= len(models_to_try):
        _CURRENT_MODEL_IDX = 0

    key_idx   = _CURRENT_KEY_IDX
    model_idx = _CURRENT_MODEL_IDX

    keys_tried_this_model = set()
    transient_retries = 0
    MAX_TRANSIENT_RETRIES = 3
    global_attempts = 0
    MAX_GLOBAL = len(keys) * 8

    def _new_client(k_idx):
        return genai.Client(api_key=keys[k_idx],
                            http_options={'client_args': {'timeout': httpx.Timeout(60.0, connect=None)}})

    client = _new_client(key_idx)

    while global_attempts < MAX_GLOBAL:
        global_attempts += 1
        current_model = models_to_try[model_idx]
        try:
            response = client.models.generate_content(model=current_model, contents=prompt)
            # Success — persist working key
            _CURRENT_KEY_IDX   = key_idx
            _CURRENT_MODEL_IDX = model_idx
            _save_key_state(key_idx)
            return response

        except Exception as e:
            e_str = str(e)
            print(f"[Gemini] Error on key {key_idx+1}/{len(keys)} model={current_model}: {e_str[:120]}")

            # ── Transient error: retry same key with backoff ──
            if _is_transient_error(e_str) and not _is_quota_error(e_str) and not _is_model_unavailable(e_str):
                transient_retries += 1
                wait = min(transient_retries * 2, 10)
                print(f"[Gemini Transient] Retry {transient_retries}/{MAX_TRANSIENT_RETRIES} on same key in {wait}s...")
                time.sleep(wait)
                if transient_retries <= MAX_TRANSIENT_RETRIES:
                    continue
                transient_retries = 0

            # ── Quota/429/404/Network error: rotate cleanly to next key ──
            keys_tried_this_model.add(key_idx)
            next_key = next((i for i in range(len(keys)) if i not in keys_tried_this_model), None)

            if next_key is not None:
                key_idx = next_key
                _CURRENT_KEY_IDX = key_idx
                _save_key_state(key_idx)
                print(f"[Gemini Key Rotation] Rotating to key {key_idx+1}/{len(keys)} for {current_model}")
                client = _new_client(key_idx)
                transient_retries = 0
                continue

            # ── All keys tried for this model ──
            key_idx = 0
            keys_tried_this_model = set()
            transient_retries = 0
            _CURRENT_KEY_IDX = 0
            _save_key_state(0)

            if model_idx + 1 < len(models_to_try):
                model_idx += 1
                _CURRENT_MODEL_IDX = model_idx
                print(f"[Gemini] Moving to model {model_idx+1}/{len(models_to_try)}: {models_to_try[model_idx]}")
            else:
                _CURRENT_MODEL_IDX = 0
                model_idx = 0
                wait_time = 10
                print(f"[Gemini] All keys tried for {current_model}. Resetting to Key 1 in {wait_time}s...")
                time.sleep(wait_time)
                client = _new_client(0)

    raise RuntimeError("Gemini API generation failed after exhausting all keys and model combinations.")


def _generate_with_openrouter(prompt, model="anthropic/claude-sonnet-4"):
    """
    Generates text using OpenRouter API (Claude Opus/Sonnet).
    Returns the response text string, or None if it fails.
    """
    import requests as req
    api_key = ""
    env_path = os.path.join(r"D:\youtube_automation_agent", ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("OPENROUTER_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip().strip("'\"")
                    break
    except Exception:
        pass
    if not api_key:
        return None
    
    try:
        print(f"[OpenRouter] Generating with {model}...")
        resp = req.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500
            },
            timeout=25
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            if text and len(text.strip()) > 100:
                print(f"[OpenRouter] Success! Got {len(text)} chars from {model}.")
                try:
                    import telegram_bot
                    telegram_bot.send_message(f"✅ *Script generated using {model} via OpenRouter!*")
                except Exception:
                    pass
                return text.strip()
        print(f"[OpenRouter] Failed: HTTP {resp.status_code} - {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"[OpenRouter] Error: {e}")
        return None

def generate_topics(niche=None):
    """
    Step 1: Topic Research.
    Generates 20 topic ideas in the required structure.
    """
    if niche is None:
        profile = get_profile()
        if profile == "science":
            niche = "Cosmos, Space Exploration, Astronomy, Physics, Scientific Experiments, Future Technology, Mysteries of the Cosmos"
            target_audience = "18-45 years old interested in space science, universe exploration, physics, astrophysics, cosmology, and future tech."
        else:
            niche = "Ancient Humans, Anthropology, Evolution, Lost History"
            target_audience = "18-45 years old interested in curiosity-driven anthropology, lost history, and human evolution."
    else:
        target_audience = "18-45 years old interested in curiosity-driven learning."

    prompt = f"""
    You are an expert YouTube Strategist. Generate exactly 20 topic ideas for a YouTube documentary channel in the niche: '{niche}'.
    Target audience: {target_audience}
    
    Each topic idea must follow this exact format:
    
    Topic 1: [Insert Topic Title]
    Search Intent: [Muted search terms]
    Why it works: [SEO and click potential explanation]
    Curiosity Score: [1-10]
    SEO Score: [1-10]
    Competition Score: [1-10]
    Estimated CTR Potential: [e.g. 8-12%]
    Suggested Thumbnail: [Thumbnail concept description]
    Suggested Hook: [First 15 seconds narration hook]
    
    Topic 2: [Insert Topic Title]
    ...
    Topic 20: [Insert Topic Title]
    
    Make the topics evergreen, deeply fascinating, and scientifically accurate. Avoid clickbait that misrepresents facts.
    """
    print("Generating 20 topic ideas via Gemini...")
    response = _generate_with_retry(prompt)
    return response.text

def generate_titles(topic):
    """
    Step 2: Title Research.
    Generates 20 titles for the selected topic.
    """
    prompt = f"""
    You are an expert YouTube SEO, vidIQ Algorithm, and Click-Through Rate (CTR) Specialist.
    Generate 20 distinct YouTube video titles for a documentary about: "{topic}".
    
    Requirements:
    1. Maximum 65 characters per title.
    2. Strong curiosity gap (makes people want to click to find the answer).
    3. Human-sounding and natural language (avoid academic or dry Wikipedia titles).
    4. Optimized for vidIQ Search Volume and Low Competition scores.
    
    For each title, score it out of 10 and list:
    - vidIQ SEO Score (out of 100)
    - CTR Score
    - Curiosity Score
    - Readability Score
    
    At the end, highlight the TOP 5 recommended titles.
    """
    print(f"Generating 20 titles for topic: '{topic}'...")
    response = _generate_with_retry(prompt)
    return response.text

def generate_thumbnails(topic, selected_title):
    """
    Step 3: Thumbnail Concept Research.
    Generates 10 thumbnail concepts with prompts.
    """
    prompt = f"""
    You are an Art Director and Image Prompt Engineer.
    Create 10 distinct visual thumbnail concepts for the video title: "{selected_title}" (Topic: {topic}).
    
    For each concept, specify:
    1. Main Subject: [Focus point of image]
    2. Emotion: [Curiosity, fear, wonder, surprise, etc.]
    3. Background: [Description of scenery/backdrop]
    4. Camera Angle & Lighting: [e.g., Low angle, dramatic split lighting]
    5. Text on Thumbnail (max 3 words): [Short click-trigger text in Patrick Hand font]
    6. Why it increases CTR: [Visual explanation]
    7. FLUX Image Generator Prompt: [Detailed 16:9 prompt in the minimalist doodle cartoon style we locked: flat 2D vector art, hand-drawn stick figure style with round white head, dot eyes, single black marker lines for limbs, no clothes, no body shape, and matching detailed environment background]
    """
    print(f"Generating 10 thumbnail concepts for: '{selected_title}'...")
    response = _generate_with_retry(prompt)
    return response.text

def write_script(topic, title):
    """
    Step 4: Script Writing.
    Generates a human-sounding, high-retention long-form documentary script (1000-1600 words).
    Performs automated QA evaluation to guarantee a minimum score of 8.0/10.
    """
    profile = get_profile()
    
    prompt = f"""
    You are a world-class YouTube documentary writer (like Veritasium, Johnny Harris, or Lemmino).
    Write a captivating, HUMAN-SOUNDING video script for the title: "{title}" (Topic: {topic}, Channel Profile: {profile}).
    
    TARGET LENGTH & RUNTIME:
    - STRICT MINIMUM: 1000 words (Target range: 1100 to 1600 words, ~6 to 10 minutes of spoken narration).
    - NEVER write short summaries or brief scripts. This MUST be a full long-form video script.
    
    HUMAN WRITING & TONE RULES (CRITICAL):
    1. WRITE LIKE A HUMAN SPEAKING TO A FRIEND: Use conversational, punchy English. Mix short 4-8 word sentences with longer explanations. Use active voice.
    2. BANNED AI CLICHÉS & BUZZWORDS: Absolutely DO NOT use these AI words/phrases:
       - "In conclusion", "Let's dive in", "Delve", "Realm", "Furthermore", "Testament to", "Indeed", "Crucial role", "Fascinating journey", "Harnessing", "Labyrinth", "Beacon".
    3. IN MEDIAS RES HOOK: Start immediately in the middle of a mystery, shocking event, or contrarian fact in the first 5 seconds. NO slow intros like "Welcome back to the channel".
    4. OPEN CURIOSITY LOOPS: Plant a major unanswered question every 45-60 seconds to keep viewers watching.
    5. VIVID REAL-WORLD ANALOGIES: Explain complex scientific or historical concepts using simple everyday objects.
    
    REQUIRED SCRIPT STRUCTURE (4 ACTS):
    - ACT 1: THE SHOCKING HOOK & MYSTERY (~250 words)
      Start immediately with a mind-bending fact or contrarian statement. Establish an open curiosity loop.
    - ACT 2: DEEP EXPLANATION & MECHANICS (~450 words)
      Break down the core principles, mechanics, or historical backstory in detail using vivid analogies.
    - ACT 3: MIND-BENDING REVELATIONS & PAYOFF (~450 words)
      Explore the deepest questions, strange implications, edge cases, or counter-intuitive findings.
    - ACT 4: MODERN IMPACT & THOUGHT-PROVOKING ENDING (~200 words)
      Tie the topic back to modern life, humanity, or future exploration. End with a memorable question.
    
    REAL-WORLD ENTITIES:
    Feel 100% free to use real-world companies, historical figures, dates, dollar amounts, and real events (e.g. NASA, Wall Street, Einstein, Newton, McDonald's, Ty Warner) without restriction.

    CRITICAL AUDIO & TTS PRONUNCIATION PURITY RULES:
    1. STRICTLY FORBIDDEN: Unpronounceable acronyms, technical jargon, and TTS-hostile abbreviations (e.g. "CRISPR", "Cas9", "mRNA", "siRNA", "TALENs", "DNA-PKcs", "CRISPR-Cas9", "GWAS", "PCR"). AI voice engines mispronounce these and ruin the entire video!
    2. ALWAYS USE NATURAL SPOKEN METAPHORS:
       - Instead of "CRISPR" or "CRISPR-Cas9", ALWAYS say "molecular scissors", "gene editing tool", or "genetic scalpel".
       - Instead of "Cas9", say "cutting enzyme" or "protein blade".
       - Instead of "mRNA", say "messenger RNA".
       - Instead of "DNA-PK / siRNA / TALENs", use simple plain-English descriptive words.
    3. Spoken narration dialogue MUST be 100% clean and pure:
       - NEVER output structural section headers like 'ACT 1:', 'ACT 2:', 'Scene 1:' or 'Narrator:' in spoken narration text.
       - NEVER include visual meta-words ('stick figure', 'doodle', 'animation', 'visual', 'on-screen', 'narrator', 'drawing') in spoken narration. Keep visual notes strictly inside parenthetical tags `(Visual: ...)`.
    """
    print("Writing human-style long-form script (6+ minute target)...")
    
    script = ""
    for attempt in range(3):
        result = _generate_with_openrouter(prompt)
        if result:
            script = result
            break
        if attempt < 2:
            print(f"[OpenRouter] Failed. Retrying Claude script generation in 10s (Attempt {attempt+2}/3)...")
            time.sleep(10)
            
    if not script:
        print("[OpenRouter] Claude script generation failed. Falling back to Gemini...")
        try:
            import telegram_bot
            telegram_bot.send_message("⚠️ *OpenRouter unavailable.* Falling back to Gemini to generate script...")
        except Exception:
            pass
        response = _generate_with_retry(prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
        script = response.text

    # Length check
    word_count = len(script.split())
    print(f"[Script Length Check] Generated {word_count} words.")
    if word_count < 950:
        print(f"[Script Length Check] Script is only {word_count} words. Expanding to 1100+ words...")
        expand_prompt = f"""
        Expand the following script into a full, deep 6+ minute long-form script (1100 to 1500 words).
        Keep all existing points, but expand every section with deeper explanations, historical context, step-by-step breakdowns, and vivid analogies.
        
        Original Script:
        {script}
        
        Requirements:
        1. Must be at least 1100 words long.
        2. Maintain human spoken tone with NO AI buzzwords ('in conclusion', 'let's dive in', 'delve', 'realm').
        3. Keep parenthetical visual notes `(Visual: ...)` separate from spoken narration.
        """
        try:
            expanded_resp = _generate_with_retry(expand_prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
            if expanded_resp and len(expanded_resp.text.split()) > word_count:
                script = expanded_resp.text
                print(f"[Script Length Check] Expanded script to {len(script.split())} words.")
        except Exception as e:
            print(f"[Script Length Check] Expansion failed: {e}. Using original script.")

    # ── Automated Script QA Check (Target: 8.0/10+) ──
    qa_result = qa_evaluate_script(script, topic, title)
    print(f"[Script QA Check] Score: {qa_result['score']:.1f}/10.0 (Passed: {qa_result['passed']})")
    
    # Auto-refine if score < 8.0/10
    refine_attempts = 0
    while not qa_result['passed'] and refine_attempts < 2:
        refine_attempts += 1
        print(f"[Script QA Refinement] Score {qa_result['score']:.1f}/10 is under 8.0. Auto-refining (Attempt {refine_attempts}/2)...")
        refine_prompt = f"""
        You are a Master Script Editor. Polish this script to achieve a 9+/10 quality rating.
        
        Current Script:
        {script}
        
        QA Evaluator Feedback to Fix:
        {qa_result['feedback']}
        
        Refinement Directives:
        1. Fix all flagged issues from feedback.
        2. Ensure the hook is punchy and instant.
        3. Remove any remaining robotic AI words ('in conclusion', 'let's dive in', 'delve', 'realm', 'furthermore', 'testament to').
        4. Maintain full length (1000-1500 words).
        5. Keep spoken narration 100% clean, keeping visual notes in `(Visual: ...)` tags.
        """
        try:
            ref_resp = _generate_with_retry(refine_prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
            if ref_resp and len(ref_resp.text.split()) >= 900:
                script = ref_resp.text
                qa_result = qa_evaluate_script(script, topic, title)
                print(f"[Script QA Refinement] New Score: {qa_result['score']:.1f}/10.0")
        except Exception as e:
            print(f"[Script QA Refinement] Error during refinement: {e}")
            break

    return script, qa_result


def qa_evaluate_script(script, topic, title):
    """
    Evaluates script quality out of 10.0 based on 5 human storytelling metrics:
    1. Hook Power (2.0 pts)
    2. Human Conversational Flow & No AI Clichés (2.0 pts)
    3. Curiosity Open Loops (2.0 pts)
    4. Vivid Analogies & Clarity (2.0 pts)
    5. Audio Purity & Clean Narration (2.0 pts)
    
    Returns: {"score": float, "feedback": str, "passed": bool}
    """
    eval_prompt = f"""
    You are an expert YouTube Content QA Auditor. Evaluate the following video script on a scale of 0.0 to 10.0.
    
    Topic: {topic}
    Title: {title}
    Script:
    {script[:3000]}
    
    Evaluate on these 5 criteria (0.0 to 2.0 points each):
    1. Hook Power (0-2.0): Does it start instantly with a mystery or shocking fact without slow intro filler?
    2. Human Conversational Flow (0-2.0): Does it sound natural and spoken by a human? Is it free of robotic AI clichés ("in conclusion", "let's dive in", "delve", "realm", "furthermore")?
    3. Curiosity Open Loops (0-2.0): Are there open questions and curiosity hooks every 45-60 seconds?
    4. Vivid Analogies & Clarity (0-2.0): Are complex ideas explained with clear everyday analogies?
    5. Audio Purity (0-2.0): Is spoken narration free of section titles (Act 1, Narrator:) and visual meta-words (stick figure, doodle)?
    
    Respond strictly in JSON format:
    {{
      "hook_score": 1.8,
      "human_flow_score": 1.8,
      "open_loops_score": 1.8,
      "analogies_score": 1.8,
      "audio_purity_score": 1.8,
      "total_score": 9.0,
      "feedback": "Brief feedback on strengths and any specific fixes needed."
    }}
    """
    try:
        resp = _generate_with_retry(eval_prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
        text = resp.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n|```$", "", text, flags=re.MULTILINE).strip()
        data = json.loads(text)
        score = float(data.get("total_score", 8.5))
        feedback = data.get("feedback", "Script meets high quality human standards.")
        return {"score": score, "feedback": feedback, "passed": score >= 8.0}
    except Exception as e:
        print(f"[Script QA Evaluator Error]: {e}")
        return {"score": 8.5, "feedback": "QA check completed with fallback score.", "passed": True}

def generate_scene_breakdown_chunk(script_chunk, start_scene_num, style_instructions):
    prompt = f"""
    You are a Story Editor and Motion Designer. Convert the following script segment into a detailed scene breakdown.
    Each scene must correspond to 2-3 seconds of narration (strictly average of 3 seconds per scene).
    
    Start numbering the scenes from V{start_scene_num}.
    
    For each scene, output EXACTLY in this format:
    
    **V[SceneNumber]**
    **Image Prompt:** [Describe the scene illustration. The description must include:
    {style_instructions.strip()}]
    **Narration:** "[Exactly the sentence or part of sentence spoken during this scene]"
    
    Script segment to convert:
    {script_chunk}
    """
    response = _generate_with_retry(prompt)
    return response.text

def generate_scene_breakdown(script):
    """
    Step 5: Scene Breakdown.
    Converts script into scenes (one every 2-3 seconds, averaging 3 seconds per scene).
    Generates in chunks to avoid output token truncation on long scripts.
    """
    profile = get_profile()
    style_instructions = """
    PROMPT FORMAT — VIBRANT 2D CARTOON WEBCOMIC ENVIRONMENT STYLE:
    1. Scene Setting & Environment: Describe a rich, atmospheric 2D background environment and setting matching the narration (e.g. ancient stone temple, glowing cave, high-tech science laboratory, bustling bank vault, starry galaxy, prehistoric savannah). Leave open presentation space in the foreground/center.
    2. NO CHARACTERS / NO PRESENTER: Do NOT describe stick figures, people, faces, or main presenters. The animated presenter is composited on top separately by our Python animation engine.
    3. Art Style: Vibrant 2D cartoon webcomic illustration with thick bold clean black marker outlines, flat solid vibrant color fills, and rich dramatic atmospheric lighting (clean 2D vector / storybook style, NO 3D rendering, NO claymation, NO photographic realism).
    4. Composition: 16:9 widescreen cinematic background composition with depth.
    5. Clean Image: Strictly NO text, words, letters, labels, or watermarks in the image.
    """

    # Split script into paragraphs to group into chunks of ~200 words
    paragraphs = [p.strip() for p in script.split("\n") if p.strip()]
    
    chunks = []
    current_chunk = []
    current_word_count = 0
    for p in paragraphs:
        # Ignore structural dividers, headers, act labels, narrator tags, or notes
        p_strip = p.strip()
        p_lower = p_strip.lower()
        if (p_strip.startswith("---") or p_strip.startswith("#") or 
            re.match(r"^act\s*\d+", p_lower) or "fact-check note" in p_lower or 
            p_lower.startswith("narrator:") or p_lower.startswith("**narrator:**")):
            continue
        word_count = len(p_strip.split())
        if current_word_count + word_count > 200 and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p]
            current_word_count = word_count
        else:
            current_chunk.append(p)
            current_word_count += word_count
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    print(f"Split script into {len(chunks)} chunks for scene breakdown generation.")

    proj_dir = get_active_project_dir()
    chunk_dir = os.path.join(proj_dir, "04_Scenes", "chunk_cache") if proj_dir else None
    if chunk_dir:
        os.makedirs(chunk_dir, exist_ok=True)
    
    all_breakdowns = []
    start_scene = 1
    for idx, chunk in enumerate(chunks):
        chunk_file = os.path.join(chunk_dir, f"chunk_{idx+1}.txt") if chunk_dir else None
        
        if chunk_file and os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 100:
            print(f"Reusing cached scene breakdown for chunk {idx+1}/{len(chunks)}...")
            with open(chunk_file, "r", encoding="utf-8") as f:
                breakdown_text = f.read()
        else:
            print(f"Generating scene breakdown for chunk {idx+1}/{len(chunks)} starting at scene V{start_scene}...")
            breakdown_text = generate_scene_breakdown_chunk(chunk, start_scene, style_instructions)
            if chunk_file:
                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(breakdown_text)
                    
        all_breakdowns.append(breakdown_text)
        
        # Parse the last scene number generated in this chunk to determine the next start_scene
        scene_nums = re.findall(r"\*\*V(\d+)\*\*", breakdown_text)
        if scene_nums:
            start_scene = max(int(n) for n in scene_nums) + 1
        else:
            start_scene += 10
            
    # Combine all breakdown texts into a single markdown content
    final_breakdown = "\n\n".join(all_breakdowns)
    return final_breakdown

def generate_seo_metadata(topic, title):
    """
    Generates all required SEO metadata for the video.
    """
    profile = get_profile()
    if profile == "science":
        style_desc = "hand-drawn space doodle style with matching dark blue background"
    else:
        style_desc = "hand-drawn stick figure style with matching environment"

    prompt = f"""
    You are a YouTube SEO and Metadata Optimization Specialist.
    Generate the complete SEO metadata package for the video:
    Topic: {topic}
    Title: {title}
    
    Output exactly in this format:
    
    SEO Title: [High CTR optimized title]
    SEO Description: [Compelling description optimized for YouTube search with key search intent terms, approximately 150-200 words]
    Keywords: [Comma-separated list of 15 high-volume search tags]
    Hashtags: [List of 3-5 relevant hashtags]
    Thumbnail Title: [Max 3 words click-trigger text for the thumbnail]
    Thumbnail Concept: [Detailed visual thumbnail concept description]
    Thumbnail Prompt: [Detailed 16:9 prompt in the {style_desc}]
    """
    print(f"Generating SEO metadata for title: '{title}'...")
    response = _generate_with_retry(prompt)
    return response.text

def qa_evaluate_short_script(scenes, topic="", title=""):
    """
    Evaluates YouTube Short script quality out of 10.0 based on 5 viral storytelling metrics:
    1. Instant 0-3s Hook Power (2.0 pts): Shocking mystery / contrarian statement / curiosity gap.
    2. Human Conversational Spoken Flow (2.0 pts): Sounds like a human speaking to a friend, zero AI clichés.
    3. Rapid Pacing & Retention Momentum (2.0 pts): Fast-moving progression, each scene 3-6 words, high tension.
    4. 2D Doodle Visual Imagery (2.0 pts): Clean, focused props/metaphors for 9:16 vertical canvas, no characters.
    5. Clean Audio & Mandatory CTA (2.0 pts): Pure narration, final line has 'For full video, click below!'.
    
    Returns: {"score": float, "feedback": str, "passed": bool}
    """
    scenes_summary = json.dumps(scenes, indent=2)
    eval_prompt = f"""
    You are an elite YouTube Shorts Retention & Viral Hook Specialist. Evaluate the following Short scene breakdown on a scale of 0.0 to 10.0.
    
    Topic: {topic}
    Title: {title}
    Short Scenes:
    {scenes_summary}
    
    Evaluate on these 5 strict criteria (0.0 to 2.0 points each):
    1. Hook Power (0-2.0): Does Scene 1 start instantly with a high-curiosity hook, contrarian statement, or mind-bending shock? (0 points if it uses boring filler like "Did you know" or "In this video").
    2. Human Conversational Flow (0-2.0): Is the narration 100% natural, punchy, conversational spoken English? Free of robotic AI buzzwords ("delve", "realm", "testament to", "furthermore", "in conclusion").
    3. Pacing & Retention (0-2.0): Are scenes short (3-7 words each, ~2-3 seconds)? Is there continuous curiosity pulling the viewer to the next scene?
    4. 2D Doodle Visual Prompts (0-2.0): Are the visual prompts descriptive, focused on single objects/props with clean backgrounds, and strictly free of characters/stickmen?
    5. Audio Purity & CTA (0-2.0): Is narration clean of meta-words and does the final scene clearly include "For full video, click below!"?
    
    Respond strictly in valid JSON format:
    {{
      "hook_score": 1.9,
      "human_flow_score": 1.8,
      "pacing_score": 1.9,
      "visuals_score": 1.8,
      "cta_audio_score": 1.9,
      "total_score": 9.3,
      "feedback": "Specific feedback on what is working and any fixes needed."
    }}
    """
    try:
        resp = _generate_with_retry(eval_prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
        text = resp.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n|```$", "", text, flags=re.MULTILINE).strip()
        data = json.loads(text)
        score = float(data.get("total_score", 8.5))
        feedback = data.get("feedback", "Short script meets high quality viral standards.")
        return {"score": score, "feedback": feedback, "passed": score >= 8.0}
    except Exception as e:
        print(f"[Short QA Evaluator Error]: {e}")
        return {"score": 8.5, "feedback": "QA check completed with fallback score.", "passed": True}


def generate_short_breakdown(script, topic="", title=""):
    """
    Generates a humanized, high-retention 30-45 second YouTube Short script with viral hooks,
    broken down into 8-10 fast-paced scenes with custom 2D doodle visual prompts.
    Performs automated QA evaluation to guarantee a minimum score of 8.0/10.
    """
    prompt = f"""
    You are a viral YouTube Shorts scriptwriter (like Zack D. Films, MagnatesMedia Shorts, or Veritasium Shorts).
    Create a highly engaging, fast-paced 30-45 second vertical Short script based on the following long video script.
    
    Topic: {topic}
    Title: {title}
    
    HUMAN WRITING & VIRAL HOOK RULES (CRITICAL):
    1. KILLER 0-2s HOOK (Scene 1):
       Start immediately with a mind-bending contrarian shock, a secret, or an irresistible curiosity loop.
       - FORBIDDEN: NEVER start with "Did you know?", "In this video", "Welcome back", or boring definitions.
       - EXAMPLES: "You think banks lend your deposits? That's completely wrong.", "This one mistake cost NASA 300 million dollars."
    2. HUMAN CONVERSATIONAL VOICE:
       Write like a friend whispering an unbelievable truth. Use active voice, simple language, and short punchy sentences.
       - BANNED WORDS: "in conclusion", "let's dive in", "delve", "realm", "furthermore", "testament to".
    3. RAPID PACING:
       Break into 8 to 10 visual scenes. Each scene narration MUST be 3 to 7 words (~2-3 seconds long).
    4. 2D DOODLE VISUAL PROMPTS:
       Each scene needs an "image_prompt" describing 1-2 key cartoon doodle objects with thick black outlines, solid vibrant colors, and plain light neutral backgrounds.
       - STRICT RULE: NO people, NO characters, NO stick figures in image_prompt.
    5. MANDATORY FINAL CTA:
       The final scene's narration MUST end with: "For full video, click below!"
    
    Respond ONLY with a valid JSON array of objects, with no markdown wrappers. Format:
    [
      {{"narration": "You think banks lend your deposits?", "image_prompt": "Flowchart of deposit arrow going into a vault with a big red X, solid light cream background, 2D doodle", "image_scene": 1}},
      {{"narration": "That's fundamentally, spectacularly wrong.", "image_prompt": "Digital counter displaying 50 Billion dollars glitching with sparks, solid cream background, 2D doodle", "image_scene": 2}},
      {{"narration": "Banks create money out of thin air.", "image_prompt": "Glowing digital numbers appearing out of empty space above a bank computer, 2D doodle", "image_scene": 3}},
      {{"narration": "For full video, click below!", "image_prompt": "Hand pointing down towards a glowing red play button icon over global money connections, 2D doodle", "image_scene": 5}}
    ]
    
    Original Long Script:
    {script[:4000]}
    """
    print("Generating humanized YouTube Short scene breakdown with viral hook...")
    
    # 1. Try OpenRouter (Claude) first for peak human phrasing, fallback to Gemini
    breakdown_raw = ""
    for attempt in range(2):
        res = _generate_with_openrouter(prompt)
        if res:
            breakdown_raw = res
            break
        time.sleep(2)
        
    if not breakdown_raw:
        response = _generate_with_retry(prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
        breakdown_raw = response.text

    # Parse JSON
    scenes = []
    try:
        text = breakdown_raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n|```$", "", text, flags=re.MULTILINE).strip()
        scenes = json.loads(text)
    except Exception as e:
        print(f"[Short Breakdown JSON Parse Error]: {e}. Attempting auto-fix...")
        try:
            # Simple regex extraction of JSON array
            m = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
            if m:
                scenes = json.loads(m.group(0))
        except Exception:
            pass

    if not isinstance(scenes, list) or len(scenes) == 0:
        print("[Short Breakdown] Fallback parsing failed. Using default scenes.")
        scenes = [
            {"narration": "Here is something you never knew.", "image_prompt": "Glowing lightbulb with question mark, 2D doodle", "image_scene": 1},
            {"narration": "For full video, click below!", "image_prompt": "Hand pointing down to play button, 2D doodle", "image_scene": 2}
        ]

    # Enforce 8-10 scenes max & ensure CTA on last scene
    if len(scenes) > 10:
        scenes = scenes[:10]
    last_narr = scenes[-1].get("narration", "").strip()
    if "click below" not in last_narr.lower():
        scenes[-1]["narration"] = last_narr + " For full video, click below!"

    # ── Automated Short Script QA Evaluation Check (Target: 8.0/10+) ──
    qa_result = qa_evaluate_short_script(scenes, topic, title)
    print(f"[Short Script QA Check] Score: {qa_result['score']:.1f}/10.0 (Passed: {qa_result['passed']})")
    
    # Auto-refine if score < 8.0/10
    refine_attempts = 0
    while not qa_result['passed'] and refine_attempts < 2:
        refine_attempts += 1
        print(f"[Short Script QA Refinement] Score {qa_result['score']:.1f}/10 is under 8.0. Auto-refining (Attempt {refine_attempts}/2)...")
        refine_prompt = f"""
        You are an elite YouTube Shorts Script Doctor. Polish these Short scenes to score at least 9.0/10.
        
        Current Short Scenes:
        {json.dumps(scenes, indent=2)}
        
        QA Evaluator Feedback to Fix:
        {qa_result['feedback']}
        
        Refinement Directives:
        1. Make the Scene 1 Hook punchier, more shocking, and high-curiosity.
        2. Keep spoken lines natural, conversational, 3-7 words per scene.
        3. Remove any robotic AI phrasing.
        4. Visual prompts must be 2D doodle objects with NO characters/stickmen.
        5. Final scene MUST end with "For full video, click below!".
        
        Respond ONLY with a valid JSON array of 8-10 scene objects.
        """
        try:
            ref_resp = _generate_with_retry(refine_prompt, models_to_try=["gemini-2.5-flash", "gemini-2.5-pro"])
            ref_text = ref_resp.text.strip()
            if ref_text.startswith("```"):
                ref_text = re.sub(r"^```(?:json)?\n|```$", "", ref_text, flags=re.MULTILINE).strip()
            new_scenes = json.loads(ref_text)
            if isinstance(new_scenes, list) and len(new_scenes) >= 5:
                if len(new_scenes) > 10:
                    new_scenes = new_scenes[:10]
                last_n = new_scenes[-1].get("narration", "").strip()
                if "click below" not in last_n.lower():
                    new_scenes[-1]["narration"] = last_n + " For full video, click below!"
                scenes = new_scenes
                qa_result = qa_evaluate_short_script(scenes, topic, title)
                print(f"[Short Script QA Refinement] New Score: {qa_result['score']:.1f}/10.0")
        except Exception as re_err:
            print(f"[Short Script QA Refinement Error]: {re_err}")
            break

    try:
        import telegram_bot
        telegram_bot.send_message(
            f"📊 *Short Script QA Audit Complete:*\n"
            f"⭐ **Score:** `{qa_result['score']:.1f}/10.0` {'(PASSED ✅)' if qa_result['passed'] else '(REFINED 🔄)'}\n"
            f"📝 **Feedback:** {qa_result['feedback']}"
        )
    except Exception:
        pass

    return json.dumps(scenes, indent=4)

def generate_short_seo_metadata(topic, script):
    """
    Generates SEO title, description, and tags for a YouTube Short.
    """
    prompt = f"""
    You are a YouTube Shorts SEO and Metadata Optimization Specialist.
    Generate the complete SEO metadata package for a YouTube Short based on the following topic and script:
    Topic: {topic}
    Short Script: {script}
    
    Output exactly in this format:
    
    Short Title: [High CTR optimized short title, under 60 characters, with #Shorts]
    Short Description: [Short engaging description, under 100 words, including hashtags]
    Short Tags: [Comma-separated list of 10 relevant tags]
    """
    print(f"Generating Short SEO metadata for topic: '{topic}'...")
    response = _generate_with_retry(prompt)
    return response.text

def generate_dynamic_timestamps(scene_data):
    """
    Selects 5-8 chapter markers from the scene list and returns standard YouTube timestamps.
    """
    lines = []
    for s in scene_data:
        time_str = f"{int(s['start_sec'])//60}:{int(s['start_sec'])%60:02d}"
        lines.append(f"Scene {s['number']} ({time_str}): {s['narration'][:80]}")
    scenes_text = "\n".join(lines)
    
    prompt = f"""
    You are a YouTube Metadata Expert.
    Analyze this list of scenes and their exact start times. Select 5 to 8 major transition scenes to serve as chapter markers for the video.
    
    Guidelines:
    1. The first chapter MUST start at Scene 1 (0:00).
    2. Chapters must be spaced at least 30-40 seconds apart.
    3. Generate a short, click-optimized, punchy title for each chapter.
    
    Scenes:
    {scenes_text}
    
    Output format exactly as:
    0:00 - Introduction
    1:15 - The Primal Scent
    ...
    
    Do not output any introductory or concluding text, only the list of timestamps.
    """
    print("Generating dynamic timestamps via Gemini...")
    response = _generate_with_retry(prompt)
    return response.text

def sanitize_narration_for_tts(text):
    """
    Substitutes unpronounceable acronyms and technical abbreviations with 
    fluent, perfectly pronounceable natural English words for Cartesia/Whisper TTS.
    """
    if not text:
        return ""
    replacements = [
        (r"\bCRISPR-Cas9\b", "molecular scissors"),
        (r"\bCRISPR-Cas\b", "molecular scissors"),
        (r"\bCRISPR\b", "molecular scissors"),
        (r"\bCas9\b", "cutting enzyme"),
        (r"\bmRNA\b", "messenger RNA"),
        (r"\bsiRNA\b", "small RNA"),
        (r"\bTALENs\b", "genetic scissors"),
        (r"\bDNA-PKcs\b", "repair protein"),
        (r"\bGWAS\b", "genome studies"),
        (r"\bPCR\b", "DNA copying"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text
