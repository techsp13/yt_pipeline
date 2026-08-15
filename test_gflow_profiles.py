import subprocess, os, shutil

test_dir = r"D:\youtube_automation_agent\_test_gflow"
os.makedirs(test_dir, exist_ok=True)

for prof in ['default', 'acc2', 'acc3']:
    cmd = ['gflow', 'image', 't2i', 'minimalist cute stick figure', '--model', 'imagen4', '--aspect', '16:9', '--out', test_dir, '--profile', prof]
    print(f"\n--- Testing Profile: {prof} ---")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print('Return code:', res.returncode)
        print('Stdout:', res.stdout.strip()[:300])
        print('Stderr:', res.stderr.strip()[:300])
    except Exception as e:
        print('Exception:', e)

shutil.rmtree(test_dir, ignore_errors=True)
