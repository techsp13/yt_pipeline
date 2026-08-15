import os
import re
import sys
import subprocess
import textwrap
import imageio_ffmpeg
from dotenv import load_dotenv

# Import our helper modules
from voiceover import generate_speech
from hf_image_gen import generate_image_hf

# Load env variables
load_dotenv()

# Get ffmpeg executable path from imageio-ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

def parse_scene_breakdown(file_path):
    """
    Parses the scene breakdown file.
    Expected format:
    **V1** or **V01**
    **Image Prompt:** ...
    **Narration:** "..."
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by **V[number]** or similar scene header
    parts = re.split(r"\*\*V(\d+)\*\*", content)
    if len(parts) < 2:
        # Try split by V[number] without asterisks
        parts = re.split(r"V(\d+)", content)
        
    if len(parts) < 2:
        raise ValueError("Could not find scene markers (e.g., **V1**) in the input file.")

    # The split returns: [text_before, scene_num_1, scene_content_1, scene_num_2, scene_content_2, ...]
    scenes = []
    for i in range(1, len(parts), 2):
        scene_num = parts[i].zfill(2) # Pad with zero, e.g. "01"
        scene_block = parts[i+1]
        
        # Extract Image Prompt
        prompt_match = re.search(r"\*\*(?:Image Prompt|Visual)\s*:?\*\*\s*(.+)", scene_block, re.IGNORECASE)
        if not prompt_match:
            # Try matching without bold markers
            prompt_match = re.search(r"(?:Image Prompt|Visual)\s*:?\s*(.+)", scene_block, re.IGNORECASE)
            
        image_prompt = prompt_match.group(1).split("\n")[0].strip() if prompt_match else ""
        
        # Extract Narration
        narration_match = re.search(r"\*\*Narration\s*:?\*\*\s*\"([^\"]+)\"", scene_block, re.IGNORECASE)
        if not narration_match:
            narration_match = re.search(r"Narration\s*:?\s*\"([^\"]+)\"", scene_block, re.IGNORECASE)
        if not narration_match:
            # Fallback to single quotes or plain text without quotes
            narration_match = re.search(r"\*\*Narration\s*:?\*\*\s*(.+)", scene_block, re.IGNORECASE)
            
        narration = ""
        if narration_match:
            narration = narration_match.group(1).split("\n")[0].strip()
            # Clean outer quotes if any
            narration = narration.strip('"').strip("'")
            
        if image_prompt or narration:
            scenes.append({
                "number": scene_num,
                "image_prompt": image_prompt,
                "narration": narration
            })
            
    return scenes

def get_audio_duration(audio_path):
    """
    Gets duration of audio file in seconds by running ffmpeg -i and parsing the duration string.
    """
    cmd = [FFMPEG_PATH, "-i", audio_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # The duration details are printed to stderr by ffmpeg
        output = result.stderr
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", output)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            duration = hours * 3600 + minutes * 60 + seconds
            return duration
    except Exception as e:
        print(f"Error getting audio duration for {audio_path}: {e}")
    return 3.0 # Fallback

def build_scene_video(image_path, audio_path, narration_text, output_path):
    """
    Creates a single scene .mp4 video with burnt-in captions.
    """
    duration = get_audio_duration(audio_path)
    
    # Wrap text for drawing subtitles
    wrapped_text = "\n".join(textwrap.wrap(narration_text, width=45))
    
    # Escape single quotes and backslashes for ffmpeg drawtext filter
    escaped_text = wrapped_text.replace("\\", "\\\\").replace("'", "'\\''").replace(":", "\\:")
    
    # Use Arial font on Windows
    font_path = "C\\:/Windows/Fonts/arial.ttf"
    
    # Drawtext filter options:
    # - Centers horizontally: x=(w-text_w)/2
    # - Positions 10% from bottom: y=h-text_h-40
    # - Adds black outline or solid black background box for readability
    vf_filter = (
        f"drawtext=text='{escaped_text}':x=(w-text_w)/2:y=h-text_h-50:"
        f"fontfile='{font_path}':fontsize=26:fontcolor=white:"
        f"box=1:boxcolor=black@0.6:boxborderw=12:line_spacing=8"
    )
    
    cmd = [
        FFMPEG_PATH, "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-vf", vf_filter,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path
    ]
    
    print(f"Building scene video clip: {output_path} (Duration: {duration:.2f}s)")
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

def assemble_pipeline(scene_file, output_dir, final_output_name="final_output.mp4"):
    """
    Main pipeline function: parses breakdown, generates assets, compiles scenes, and concatenates.
    """
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = os.path.join(output_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    print("Parsing scene breakdown...")
    scenes = parse_scene_breakdown(scene_file)
    print(f"Found {len(scenes)} scenes in breakdown.")

    style_prefix = "A simple 2D flat cartoon webcomic illustration of "

    # Suffix to force minimalist 2D cartoon doodle style on FLUX (matching your stick body reference)
    style_suffix = (
        ", simple 2D flat cartoon illustration, minimalist stick-figure webcomic style. "
        "The stickman has a body made only of single black marker lines (no clothing, no shirts, no pants). "
        "He has a simple round white head with messy brown hair, dot eyes, and a simple mouth. "
        "The background is a flat two-tone split background divided by a simple horizontal dividing line, "
        "using soft aesthetic pastel colors (like zen beige sky and warm tan ground). "
        "All objects are simple 2D flat cartoon doodles drawn with a black marker, flat solid color fill, with clear visible details. "
        "Completely flat drawing, thick clean black outlines, no shading, no gradients, no shadows, no 3D rendering."
    )

    concat_files = []
    
    for scene in scenes:
        num = scene["number"]
        prompt = scene["image_prompt"]
        narration = scene["narration"]
        
        print(f"\n--- Scene V{num} ---")
        print(f"Prompt: {prompt}")
        print(f"Narration: {narration}")

        image_path = os.path.join(output_dir, f"V{num}.png")
        audio_path = os.path.join(output_dir, f"V{num}.mp3")
        clip_path = os.path.join(temp_dir, f"V{num}.mp4")

        # 1. Generate Voiceover (skip if exists)
        if not os.path.exists(audio_path):
            if narration:
                success = generate_speech(narration, audio_path)
                if not success:
                    print(f"Warning: Voiceover generation failed for scene V{num}. Skipping.")
                    continue
            else:
                print(f"No narration text for scene V{num}. Skipping.")
                continue
        else:
            print(f"Audio file already exists: {audio_path}")

        # 2. Generate Image (skip if exists)
        if not os.path.exists(image_path):
            if prompt:
                # Add emphasis on DNA details for DNA scenes specifically
                current_prompt = prompt
                if "DNA" in prompt.upper():
                    current_prompt = prompt.replace("DNA strand", "DNA double helix strand with clear visible base-pair details")
                
                full_prompt = current_prompt + style_suffix
                success = generate_image_hf(full_prompt, image_path)
                if not success:
                    print(f"Warning: Image generation failed for scene V{num}. Skipping.")
                    continue
            else:
                print(f"No image prompt for scene V{num}. Skipping.")
                continue
        else:
            print(f"Image file already exists: {image_path}")

        # 3. Create Scene Clip
        try:
            build_scene_video(image_path, audio_path, narration, clip_path)
            concat_files.append(clip_path)
        except Exception as e:
            print(f"Failed to build video clip for scene V{num}: {e}")

    if not concat_files:
        print("No video clips were built. Cannot concatenate.")
        return

    # 4. Concatenate clips
    concat_list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for clip in concat_files:
            # Write absolute paths with forward slashes for ffmpeg safety
            f.write(f"file '{clip.replace(os.sep, '/')}'\n")

    final_video_path = os.path.join(output_dir, final_output_name)
    print(f"\nConcatenating {len(concat_files)} clips into final video: {final_video_path}")
    
    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c", "copy",
        final_video_path
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("Final video assembled successfully!")
        
        # Cleanup temp directory
        # shutil.rmtree(temp_dir) # uncomment if you want to auto-cleanup
    except Exception as e:
        print(f"Failed to concatenate final video: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python assemble_video.py <scene_breakdown_file> <output_directory> [final_video_name.mp4]")
        sys.exit(1)
        
    scene_file_arg = sys.argv[1]
    output_dir_arg = sys.argv[2]
    final_name = sys.argv[3] if len(sys.argv) > 3 else "final_output.mp4"
    
    assemble_pipeline(scene_file_arg, output_dir_arg, final_name)
