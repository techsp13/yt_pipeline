import os, time, subprocess

out_dir = r"D:\youtube_automation_agent\_test_speed"
os.makedirs(out_dir, exist_ok=True)

models = ['nano2', 'imagen4']
for m in models:
    t0 = time.time()
    cmd = ['gflow', 'image', 't2i', 'minimalist cute stick figure', '--model', m, '--aspect', '16:9', '--out', out_dir, '--profile', 'acc2']
    print(f"Testing model: {m}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    dur = time.time() - t0
    print(f"Model {m}: returncode={res.returncode}, time={dur:.1f}s")
    if res.returncode != 0:
        print("Stderr:", res.stderr[:200])

import shutil
shutil.rmtree(out_dir, ignore_errors=True)
