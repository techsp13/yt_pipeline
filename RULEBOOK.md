# YouTube Automation Agent -- Core Rulebook

---

## RULE 1: Final Video Duration == Master Voiceover Duration (100% Exact Match)
- The Final Compiled Video (Video_Final.mp4) duration MUST ALWAYS EXACTLY MATCH the Master Audio (Full_Script_Voice.mp3 / Full_Script_Voice_pcm.wav) duration.
- No trailing audio or scenes may ever be dropped, truncated, or clipped.
- abs(final_video_duration - master_audio_duration) < 0.050s (millisecond-accurate alignment).

---

## RULE 2: Contiguous Audio Slicing & Explanation Flow (No Cut-Offs)
To ensure the narration sounds completely natural and explanations never feel rushed, clipped, or broken:
- Scene 1: Starts at 0.000s and runs until Scene 2 Narration Start.
- Scene 2: Starts at Scene 2 Narration Start and runs until Scene 3 Narration Start.
- Scene i: Starts at Scene i Narration Start and runs until Scene i+1 Narration Start.
- Scene N (Last Scene): Starts at Scene N Narration Start and runs until the very end of the master audio (total_audio_duration).

Why: Any pauses, breaths, or explanation emphasis between sentences are automatically allocated to the current visual scene, giving the viewer proper time to absorb the illustration and hear the complete explanation without jarring audio cuts.

---

## RULE 3: Zero-Crop Aspect-Fit Visual Framing
- 16:9 Landscape (1024x576): 0% cropped edges. The complete subject must fit inside the 16:9 frame with canvas background color extension.
- 9:16 Vertical (576x1024): 0% cropped edges. Subject is centered with background color matching and breathing room for subtitles and stickman overlay.

---

## RULE 4: Multi-Worker Image Generation & Failover
- Primary: 8 Cloudflare Worker AI pool (@cf/black-forest-labs/flux-1-schnell with prompt payload).
- Rotates automatically across keys when rate-limited.
- Automatic failover to ZeroGPU FLUX space so image generation never fails.

---

## RULE 5: Strict Ban on TTS-Hostile Acronyms & Unpronounceable Jargon
- NEVER write obscure, unpronounceable acronyms or technical jargon in spoken scripts (e.g. CRISPR, Cas9, mRNA, siRNA, TALENs, DNA-PKcs, GWAS, PCR).
- AI voice models (Cartesia/ElevenLabs) garble and mispronounce these, destroying video credibility and audience retention.
- Mandatory Substitutions:
  * Instead of "CRISPR" / "CRISPR-Cas9", ALWAYS say "molecular scissors" or "gene editing tool".
  * Instead of "Cas9", say "cutting enzyme" or "protein blade".
  * Instead of "mRNA", say "messenger RNA".
  * Instead of "TALENs / siRNA", use plain-English descriptive words.
- All scripts MUST be 100% natural, spoken, conversational English that any voice model can pronounce flawlessly without stuttering.

---

## RULE 6: High-CTR Split-Screen Thumbnail Standards
- Composition: Split-Screen Layout (Left Side = Text, Right Side = Large Central Object).
- Font: STRICTLY Patrick Hand handmade doodle font (PatrickHand-Regular.ttf).
- Text Color: Vibrant Doodle Yellow (#FFE100) with thick 10px black marker outline and drop shadow.
- Spacing: Exact ~30px clean margin between text block and object.
- Object Size: Maximized (680x676px zone) for prominent, eye-catching visual punch.
- No Stickman: 100% stickman-free on thumbnails for clean, high-impact focus.