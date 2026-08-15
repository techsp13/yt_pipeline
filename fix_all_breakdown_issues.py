import os, sys, re

sys.stdout.reconfigure(encoding="utf-8")

bk_path = r"D:\youtube_automation_agent\channels\money\the_beanie_baby_economic_bubble_2026-07-29_223132\04_Scenes\Scene_Breakdown.md"

with open(bk_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Global replacements: Ty Incorporated -> Ty Inc.
content = content.replace("Ty Incorporated.,", "Ty Inc.,")
content = content.replace("Ty Incorporated.", "Ty Inc.")
content = content.replace("Ty Incorporated", "Ty Inc.")

# Fix any double punctuation like "Inc.." or "Inc.,"
content = content.replace("Inc..,", "Inc.,")
content = content.replace("Inc..", "Inc.")

# 2. Split scenes and process each scene block
parts = re.split(r"(\*\*V\d+\*\*)", content)

new_parts = []

for idx, part in enumerate(parts):
    if re.match(r"\*\*V\d+\*\*", part):
        new_parts.append(part)
        continue

    if not part.strip():
        new_parts.append(part)
        continue

    block = part

    # Check scene number from previous part if possible
    sc_match = re.search(r"V(\d+)", parts[idx-1]) if idx > 0 else None
    sc_num = int(sc_match.group(1)) if sc_match else 0

    # Fix V32 specifically
    if sc_num == 32:
        # Give V32 proper spoken title card narration
        block = re.sub(
            r"\*\*Narration\s*:?\*\*\s*.*",
            '**Narration:** "The Beanie Baby Bubble: Was It a Clever Scam?"',
            block
        )

    # Fix V35 specifically (double punctuation check)
    if sc_num == 35:
        block = block.replace("Ty Inc.,", "Ty Inc.,")

    # Fix V68 specifically
    if sc_num == 68:
        block = re.sub(
            r"\*\*Narration\s*:?\*\*\s*.*",
            '**Narration:** "Here\'s where the scam question truly crystallizes."',
            block
        )

    # Normalize Narration Quotes for ALL scenes (ensure consistent "..." quotes)
    nm = re.search(r"(\*\*Narration\s*:?\*\*\s*)(.+)", block)
    if nm:
        prefix = nm.group(1)
        raw_text = nm.group(2).strip()
        
        # If visual note is outside, keep visual note inside parenthetical or strip
        # Clean text
        clean_text = raw_text.strip('"').strip("'").strip()
        
        # Remove any lingering stray trailing/leading quotes inside
        clean_text = re.sub(r'^"+|"+$', '', clean_text).strip()
        clean_text = re.sub(r"^'+|'+$", '', clean_text).strip()
        
        # Handle visual notes like (Visual: ...)
        vis_match = re.search(r"\(\s*Visual\s*:[^\)]*\)", clean_text, re.IGNORECASE)
        vis_str = ""
        if vis_match:
            vis_str = " " + vis_match.group(0)
            clean_text = clean_text.replace(vis_match.group(0), "").strip()

        if clean_text:
            # Rewrap narration in clean quotes
            formatted_narration = f'{prefix}"{clean_text}"{vis_str}'
            block = block.replace(nm.group(0), formatted_narration)
        elif vis_str:
            # Visual only scene
            formatted_narration = f'{prefix}""{vis_str}'
            block = block.replace(nm.group(0), formatted_narration)

    new_parts.append(block)

final_content = "".join(new_parts)

with open(bk_path, "w", encoding="utf-8") as f:
    f.write(final_content)

print("✅ Successfully updated Scene_Breakdown.md with clean quotes, V32 title narration, and Ty Inc. fixes!")
