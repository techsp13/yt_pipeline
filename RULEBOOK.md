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

## RULE 6: Mandatory 5-Thumbnail A/B Testing Standards
- **Always Generate 5 Distinct Thumbnails:** Every project MUST automatically generate 5 complete, distinct thumbnail options (`Thumbnail_1.png` to `Thumbnail_5.png`) saved into `12_Thumbnail/`.
- **Diversity Across All 5:**
  * **Option 1 (Hero Hook):** Primary curiosity gap / SEO hook + main dramatic focal scene + `mind_blown` mascot pose.
  * **Option 2 (Sensory / Process):** Sensory / mechanism angle (e.g. smell, thermal scan, heat vision) + `pointing_right` mascot pose.
  * **Option 3 (Science / Evidence):** Deep lab investigation, DNA / blueprints, evidence proof + `explaining` mascot pose.
  * **Option 4 (Hidden Mystery):** Invisible beacon, gas plumes, unseen forces + `shocked` mascot pose.
  * **Option 5 (The Contrast):** Stark split-screen contrast (victim vs unaffected, untouched vs devoured) + `curious` mascot pose.
- **Typography & Font:** Big bold hand-drawn 2D cartoon doodle bubble lettering in vibrant Doodle Yellow (`#FFCC00` / `#FFE100`) with thick black marker outlines around every letter.
- **Format:** 16:9 widescreen YouTube thumbnail format, high-contrast composition, 100% borderless.
- **Telegram Interactive Suite:** All 5 thumbnails are sent to Telegram as an album with interactive buttons (`Pick #1` to `Pick #5` or `Regen 5`) allowing one-click selection of the active master thumbnail while retaining all 5 for YouTube Studio A/B testing.

---

## RULE 7: Pure Contiguous Boundary Slicing & Zero Audio Tampering
- **Continuous Master Source:** Always generate the full script audio in a single uninterrupted call (`Full_Script_Voice_pcm.wav`).
- **Pure Boundary Slicing:** When slicing into Scene 1, Scene 2, ... Scene N for image-audio hard-locking:
  * Slice strictly at boundary timestamps (`Scene 1: [0, T1]`, `Scene 2: [T1, T2]`, `Scene N: [TN-1, Total]`).
  * **ZERO Trimming / Silence-Cutting:** Never trim, strip, silence-cut, tempo-alter, or tamper with any part of the sliced audio.
  * Natural pauses, breaths, and emphasis must remain 100% untouched inside their respective scene slice.
- **Perfect Reconstruction:** When all per-scene video clips are concatenated, the resulting audio must be a 100% bit-for-bit contiguous replica of the original master audio stream ($\sum \text{Scenes} \equiv \text{Master Audio}$).

---

## RULE 8: Minimalist 2D Webcomic Doodle Art Standards (Zero Clutter, Dynamic Clothing & Screen Fit)
- **Minimalist Focal Hierarchy (1–2 Hero Elements Max):** Each scene MUST feature only 1 or 2 primary focal elements (e.g. 1 campfire with stickmen, 1 arm with bacteria blobs, 1 flower in meadow, 1 open vault). Never crowd or pollute frames with unnecessary floating objects, background clutter, or complex micro-details.
- **Dynamic Era-Appropriate Clothing:** The mascot character MUST wear clothing that dynamically matches the exact time period and topic of the story (e.g., prehistoric caveman fur pelt wrap for Stone Age, linen kilt for Ancient Egypt, classical tunic for Antiquity, medieval tunic for Middle Ages, modern suit/jacket for recent eras). Never force Greek/Roman togas onto non-classical topics.
- **Solid Full-Color Objects (No Wireframe / Line-Only Drawings):** All animals, props, tools, weapons, and environmental subjects MUST be fully colored, opaque 2D cartoon objects with solid cel-shaded fills and thick black ink outlines. Strictly NO transparent wireframes, faint mirages, or line-only outline sketches.
- **Fit-to-Screen Camera Framing (No Extreme Cropping):** Medium and wide camera shots MUST be used so that the entire product, weapon, prop, animal, and character fit comfortably inside the 16:9 widescreen canvas with clean breathing room. Never generate extreme cropped close-ups where the character's head, forehead, or key items are cut off at the edge of the frame.
- **Flat 2-Tone / 3-Tone Environments:** Clean, solid flat backgrounds (e.g., solid pastel sky + simple ground horizon line, solid clean room wall, or solid dark navy night). Generous open negative space.
- **Strict Zero-Text Policy in Art:** Absolutely NO random AI gibberish text, letters, logos, or corner watermarks (especially top-left). Scene art must be 100% pure visual illustration.
- **Line & Color DNA:** Bold clean thick black ink marker outlines, flat vibrant cel-shaded color fills, zero 3D realism, zero gritty shading. Consistent 2D webcomic aesthetic (Mack & Zenn style).

---

## RULE 9: Authentic Natural Object Colors & Multi-Tone Separation (No Monochrome Tinting)
- **Object-Specific Natural Colors:** Every individual element in the scene MUST have its own authentic, distinct color:
  * **Trees & Foliage:** Lush, vibrant green leaves and solid dark brown wooden trunks. Strictly NEVER color trees or foliage yellow/beige matching the background.
  * **Sky:** Clean natural light-blue sky (`#87CEEB`) with soft white cartoon clouds.
  * **Grass & Ground:** Fresh green grass blades and tufts resting on warm natural dirt/earth terrain.
  * **Animals:** Authentic multi-colored cartoon anatomy (e.g. Golden lion body with rich dark brown mane; orange tiger with black stripes; solid dark brown bear fur; grey elephant).
  * **Characters & Props:** Tan skin (`#C89B78`), era-appropriate clothing (brown fur wrap, blue tunic, khaki safari shirt), steel grey weapons with brown wooden handles.
- **Strictly Banned Monochromatic Washes:** Absolutely NO monochrome color drenching where the entire background, trees, and sky are bathed in a single uniform yellow, beige, or olive-green tint. Each object must stand out with its own proper natural color.
- **High Contrast & Negative Space:** Sharp visual clarity and cel-shaded definition with bold black marker outlines.

---

## RULE 10: Minimal Text & Hand-Drawn Marker Typography Standard (Reference Match)
- **Ultra-Minimal Text (1–3 Words Max, Zero Clutter):**
  * NEVER put long phrases, full sentences, or multiple floating text labels in scene images.
  * Maximum 1 to 3 punchy words per visual (e.g., `"NOT FROM HERE?"`, `"DECOMPOSE"`, `"BACTERIA"`).
  * If the illustration already communicates the story visually, use **ZERO text**. The visual action and mascot must carry the explanation.
- **Hand-Drawn Marker Font & Styling (Matching Reference):**
  * **Font Aesthetic:** Casual, organic hand-lettered marker / comic comic-book typography (`PatrickHand-Regular.ttf` style). Must look like an artist drew it on paper with a felt-tip pen.
  * **Color Code:**
    - **Bold Red (`#E11D48` / `#D32F2F`):** For high-curiosity questions, hooks, anomalies, or alerts (e.g., `"NOT FROM HERE?"`).
    - **Solid Black (`#0F172A` / `#000000`):** For physical/biological processes, scientific terms, or core nouns (e.g., `"DECOMPOSE"`).
  * **Hand-Drawn Visual Accents:** Complement text with simple hand-drawn directional arrows (red dashed curve or solid black arrows) guiding the eye to the focal subject.
  * **Banned Text Styles:** Strictly NO artificial digital UI boxes, typewriter badges, neon gradients, heavy dropshadows, or blocky sterile system fonts. Pure hand-drawn marker lettering only.