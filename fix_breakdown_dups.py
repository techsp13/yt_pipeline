import os
import re

proj_dir = r"D:\youtube_automation_agent\channels\history\why_ancient_human_do_drug_2026-07-24_210849"
breakdown_file = os.path.join(proj_dir, "04_Scenes", "Scene_Breakdown.md")

with open(breakdown_file, "r", encoding="utf-8") as f:
    content = f.read()

scene_blocks = re.split(r"\*\*V\d+\*\*", content)
headers = re.findall(r"\*\*V(\d+)\*\*", content)

fixed_blocks = [scene_blocks[0]]
seen_narrations = {}
removed_count = 0

for idx, header in enumerate(headers):
    block = scene_blocks[idx + 1] if idx + 1 < len(scene_blocks) else ""
    num = int(header)
    scene_id = f"V{num:02d}"

    narration_match = re.search(r"(\*\*Narration:\*\*\s*\"?)(.*?)(\"?\n|$)", block, re.IGNORECASE | re.DOTALL)
    if narration_match:
        prefix, raw_narration, suffix = narration_match.groups()
        clean_narr = raw_narration.strip('"').strip()
        if clean_narr:
            if clean_narr in seen_narrations:
                removed_count += 1
                print(f"[{scene_id}] Clearing duplicate narration identical to V{seen_narrations[clean_narr]:02d}: \"{clean_narr}\"")
                block = block.replace(narration_match.group(0), f'{prefix}""\n')
            else:
                seen_narrations[clean_narr] = num

    fixed_blocks.append(f"**V{header}**" + block)

fixed_content = "".join(fixed_blocks)
with open(breakdown_file, "w", encoding="utf-8") as f:
    f.write(fixed_content)

print(f"\n[Deduplication Complete] Removed {removed_count} duplicate narration lines from Scene_Breakdown.md!")
