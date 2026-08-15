import os, sys, re

sys.stdout.reconfigure(encoding="utf-8")

bk_path = r"D:\youtube_automation_agent\channels\money\the_beanie_baby_economic_bubble_2026-07-29_223132\04_Scenes\Scene_Breakdown.md"
with open(bk_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix V35: Ty Inc -> Ty Inc.
content = content.replace('"His company, Ty Inc, didn’t', '"His company, Ty Inc., didn’t')

# Fix V45: He Ltd. production -> He limited production
content = content.replace('""He Ltd. production."', '"He limited production."')
content = content.replace('"He Ltd. production."', '"He limited production."')

# Fix V56: leading period before or -> Or
content = content.replace('".or Toys R Us.', '"Or Toys R Us.')

# Fix V109: Ty Inc, -> Ty Inc.,
content = content.replace('for Ty Inc,"', 'for Ty Inc.,"')

# Fix V128: Ltd.-edition -> limited-edition & clean outer quotes
content = content.replace('""the housing crisis, Ltd.-edition sneaker drops"', '"the housing crisis, limited-edition sneaker drops,"')
content = content.replace('"the housing crisis, Ltd.-edition sneaker drops"', '"the housing crisis, limited-edition sneaker drops,"')

# Fix V143 & V144 continuity flow (no empty scene mid-sentence)
content = content.replace(
    '**V143**\n**Image Prompt:** Forlorn Beanie Baby plush toy sitting alone on a simple shelf. Character in green hoodie shrugging, questioning. Top background: Mint green with tiny gold coins. Bottom background: Light tan.\n**Narration:** ""',
    '**V143**\n**Image Prompt:** Forlorn Beanie Baby plush toy sitting alone on a simple shelf. Character in green hoodie shrugging, questioning. Top background: Mint green with tiny gold coins. Bottom background: Light tan.\n**Narration:** "craze a calculated illusion,"'
)

with open(bk_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Applied all fixes to Scene_Breakdown.md!")
