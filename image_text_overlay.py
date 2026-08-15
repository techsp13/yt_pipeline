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
    Draws doodle-style text labels onto an image in-place.

    Args:
        image_path: Path to the PNG/JPG file to annotate.
        labels:     List of strings to draw (e.g. ['1999', '$5']).
        position:   'top' (default) or 'bottom' — where to place labels.

    Returns True on success, False if nothing was drawn.
    """
    if not labels or not os.path.exists(image_path):
        return False

    try:
        img = Image.open(image_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Determine font size relative to image width (≈6% of width, min 24 px)
        font_size = max(24, int(w * 0.06))
        font = _best_font(font_size)

        # Measure total text width to arrange labels horizontally
        padding = int(w * 0.03)
        x = padding
        y = padding if position == "top" else (h - font_size - padding * 3)

        for label in labels:
            # Sample background colour at target position for contrast
            try:
                sample_x = min(x + font_size // 2, w - 1)
                sample_y = min(y + font_size // 2, h - 1)
                bg_pix = img.getpixel((sample_x, sample_y))
                text_color = _contrast_color(bg_pix)
            except Exception:
                text_color = (0, 0, 0)

            # Draw thick black outline (stroke effect)
            outline = 3
            for dx in range(-outline, outline + 1):
                for dy in range(-outline, outline + 1):
                    if dx != 0 or dy != 0:
                        draw.text((x + dx, y + dy), label, font=font, fill=(0, 0, 0, 255))

            # Draw white fill on top
            draw.text((x, y), label, font=font, fill=(255, 255, 255, 255))

            # Advance x for next label
            bbox = draw.textbbox((0, 0), label, font=font)
            label_w = bbox[2] - bbox[0]
            x += label_w + padding * 2

            # Wrap to next line if overflowing
            if x > w - padding:
                x = padding
                y += font_size + padding

        # Save back as RGB PNG
        img = img.convert("RGB")
        img.save(image_path, "PNG")
        return True

    except Exception as e:
        print(f"[TextOverlay] Failed to overlay text on {image_path}: {e}")
        return False


def apply_prompt_labels(image_path: str, prompt: str) -> bool:
    """
    Convenience wrapper: extracts labels from a prompt string and overlays them.
    Returns True if labels were applied, False if no labels found or error.
    """
    labels = extract_labels_from_prompt(prompt)
    if not labels:
        return False
    print(f"[TextOverlay] Applying labels {labels} onto {os.path.basename(image_path)}")
    return overlay_text_labels(image_path, labels, position="top")


if __name__ == "__main__":
    # Quick smoke test
    import sys
    if len(sys.argv) >= 3:
        img_path = sys.argv[1]
        test_labels = sys.argv[2:]
        ok = overlay_text_labels(img_path, test_labels)
        print("Applied:", ok)
    else:
        print("Usage: python image_text_overlay.py <image.png> <label1> [label2 ...]")
