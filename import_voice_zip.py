import os
import json
import sys
import zipfile
import shutil

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def import_voice_zip(zip_path=None):
    pointer_file = r"D:\youtube_automation_agent\Current"
    proj_dir = None
    if os.path.exists(pointer_file):
        with open(pointer_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            proj_dir = data.get("active_project_dir")

    if not proj_dir or not os.path.exists(proj_dir):
        proj_dir = r"D:\youtube_automation_agent\channels\money\the_cola_wars_2026-07-25_131744"

    # Search common download locations if zip_path not provided
    if not zip_path or not os.path.exists(zip_path):
        search_paths = [
            r"C:\Users\ASUS\Downloads\07_Voice.zip",
            r"D:\youtube_automation_agent\07_Voice.zip",
            os.path.join(proj_dir, "07_Voice.zip")
        ]
        for p in search_paths:
            if os.path.exists(p):
                zip_path = p
                break

    if not zip_path or not os.path.exists(zip_path):
        print("❌ Could not find 07_Voice.zip in Downloads folder.")
        return False

    voice_target_dir = os.path.join(proj_dir, "07_Voice")
    os.makedirs(voice_target_dir, exist_ok=True)

    print(f"📦 Unzipping {zip_path} into {voice_target_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(proj_dir)

    # Check imported files
    files = [f for f in os.listdir(voice_target_dir) if f.endswith(".mp3")]
    print(f"🎉 SUCCESS! Imported {len(files)} cloned voiceover files.")

    # Update project step to 10 for video editing
    cfg_path = os.path.join(proj_dir, "Project_Config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["step"] = 10
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        print("🎬 Updated Project_Config.json to Step 10 (Video Compilation Ready)!")

    return True

if __name__ == "__main__":
    import_voice_zip()
