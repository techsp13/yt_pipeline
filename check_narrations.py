import sys, re
sys.stdout.reconfigure(encoding='utf-8')

bk = open(
    r'D:\youtube_automation_agent\channels\history\ancient_human_drink_chai_or_morning_drink_2026-07-29_085235\04_Scenes\Scene_Breakdown.md',
    encoding='utf-8'
).read()

parts = re.split(r'\*\*V(\d+)\*\*', bk)
targets = ['11', '13', '19', '68', '106']
for target in targets:
    for i in range(1, len(parts), 2):
        if parts[i] == target:
            block = parts[i+1]
            pat = r'Narration[^"]*"([^"]*)"'
            m = re.search(pat, block, re.IGNORECASE)
            n = m.group(1).strip() if m else 'EMPTY'
            size = 0
            import os
            p = os.path.join(
                r'D:\youtube_automation_agent\channels\history\ancient_human_drink_chai_or_morning_drink_2026-07-29_085235\07_Voice',
                f'Scene_{int(target):02d}_Voice.mp3'
            )
            if os.path.exists(p):
                size = os.path.getsize(p)
            print(f'Scene {target}: [{n[:80]}] | audio: {size} bytes')
