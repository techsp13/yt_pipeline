"""
inspect_rendered_clips.py
"""
import os, sys, json, subprocess, re

proj = r'D:\youtube_automation_agent\channels\history\How_Did_Ancient_People_Stay_Cool_Without_Electrici_2026-08-11_084945'
ffmpeg = r'C:\Users\ASUS\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe'
tmp_dir = os.path.join(proj, 'output_temp')
tl_p = os.path.join(proj, '14_Checkpoints', 'Scene_Timeline.json')

with open(tl_p, encoding='utf-8') as f:
    tl = json.load(f)

scenes = tl['scenes']
print('Timeline scene count:', len(scenes))
print('Sum of timeline durations:', sum(s['duration'] for s in scenes))
print('Sum of timeline frame_counts:', sum(s['frame_count'] for s in scenes))

total_frames_found = 0
total_dur_found = 0.0

diffs = []
for s in scenes:
    sn = f"{s['number']:02d}"
    clip_p = os.path.join(tmp_dir, f'Scene_{sn}.mkv')
    res = subprocess.run([ffmpeg, '-i', clip_p], capture_output=True, text=True)
    out = res.stderr
    
    m_dur = re.search(r'Duration: (\d+):(\d+):([\d\.]+)', out)
    dur = 0.0
    if m_dur:
        dur = int(m_dur.group(1))*3600 + int(m_dur.group(2))*60 + float(m_dur.group(3))
        total_dur_found += dur
    
    cmd2 = [ffmpeg, '-i', clip_p, '-map', '0:v', '-c', 'copy', '-f', 'null', '-']
    res2 = subprocess.run(cmd2, capture_output=True, text=True)
    m_f = re.findall(r'frame=\s*(\d+)', res2.stderr)
    f_cnt = int(m_f[-1]) if m_f else 0
    total_frames_found += f_cnt
    
    tgt_dur = s['duration']
    tgt_f = s['frame_count']
    if abs(dur - tgt_dur) > 0.05 or f_cnt != tgt_f:
        diffs.append((sn, tgt_dur, dur, tgt_f, f_cnt))

print(f'\nTotal Sum of Actual Clip Durations : {total_dur_found:.4f}s')
print(f'Total Sum of Actual Video Frames   : {total_frames_found} frames ({total_frames_found/25.0:.4f}s)')
print(f'Mismatched Clips Count             : {len(diffs)}')

if diffs:
    print('\nMismatched Clips Details:')
    for sn, td, ad, tf, af in diffs[:15]:
        print(f'  Scene V{sn}: Target Dur={td:.3f}s ({tf}f) | Actual Dur={ad:.3f}s ({af}f)')
