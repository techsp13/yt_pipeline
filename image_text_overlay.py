"""
image_text_overlay.py
Renders accurate, doodle-style text labels directly onto generated images using PIL.
This bypasses the image model for text, eliminating spelling errors.
"""
import re
import os
from PIL import Image, ImageDraw, ImageFont

# Path to Comic Sans Bold (doodle-style) — always present on Windows
COMIC_BOLD   = r"C:\Windows\Fonts\comicbd.ttf"
COMIC_NORMAL = r"C:\Windows\Fonts\comic.ttf"

# Fallback: any TTF that exists
_FALLBACK_FONTS = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def _best_font(size: int) -> ImageFont.FreeTypeFont:
    for path in [COMIC_BOLD, COMIC_NORMAL] + _FALLBACK_FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _contrast_color(bg_rgb) -> tuple:
    """Returns black or white depending on background luminance."""
    r, g, b = bg_rgb[:3]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return (0, 0, 0) if lum > 128 else (255, 255, 255)


def extract_labels_from_prompt(prompt: str) -> list[str]:
    """
    Parse the labels the prompt asked the model to draw.
    Looks for the 'TEXT ON IMAGE: ...' prefix pattern.
    Returns a list of unique label strings.
    """
    # Pattern: TEXT ON IMAGE: 'Label1', 'Label2', ...
    m = re.search(r"TEXT ON IMAGE:\s*(.+?)(?:in bold doodle|\.|\n|$)", prompt, re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    # Extract quoted or repr'd values
    labels = re.findall(r"['\"]([^'\"]{1,25})['\"]", raw)
    # Deduplicate while preserving order
    seen, result = set(), []
    for lbl in labels:
        lbl = lbl.strip()
        if lbl and lbl not in seen:
            seen.add(lbl)
            result.append(lbl)
    return result


def overlay_text_labels(image_path: str, labels: list[str], *, position: str = "top") -> bool:
    """
    STRICT USER DIRECTIVE:
    NEVER add white left top corner text.
    Any text must be proper doodle-style text generated natively within the scene (or on signs,
    boards, charts, or thought bubbles as bold black marker lettering).

    This function is intentionally a NO-OP to prevent duplicate white top-left text.
    """
    return False


def apply_prompt_labels(image_path: str, prompt: str) -> bool:
    """
    STRICT USER DIRECTIVE:
    NEVER add white left top corner text.
    Permanently disabled to prevent duplicate white top-left text.
    """
    return False


if __name__ == "__main__":
    print("[image_text_overlay] Top-left white text overlay permanently disabled per project styling rules.")

