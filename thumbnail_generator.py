"""
thumbnail_generator.py
Automated YouTube Thumbnail Generator in Pure 2D Doodle Style.
Builds each zone manually with PIL compositing — not relying on AI to place objects.
Grid (1280x720):
  Top 40%  (Y 0–288):    TEXT zone (full width)
  Bottom 60% Left 70%  (Y 288–720, X 0–896):    AI OBJECT zone
  Bottom 60% Right 30% (Y 288–720, X 896–1280): STICKMAN zone
"""
import os
import re
from PIL import Image, ImageDraw, ImageFont
import hf_image_gen
import stickman_engine

# Font priority — Patrick Hand first for authentic hand-drawn doodle aesthetic
FONT_PATHS = [
    r"D:\youtube_automation_agent\PatrickHand-Regular.ttf",
    r"C:\Windows\Fonts\comicbd.ttf",
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\ariblk.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]

# ── Grid Constants (1280 x 720) ──────────────────────────────────────────────
W, H       = 1280, 720
TEXT_H     = int(H * 0.42)     # 302px  — top 42% for text
OBJ_Y      = TEXT_H            # 302px  — bottom zone y-start
OBJ_H      = H - TEXT_H       # 418px  — bottom zone height
OBJ_W      = int(W * 0.70)    # 896px  — left 70% width for object
STICK_X    = OBJ_W             # 896px  — stickman x-start
STICK_W    = W - OBJ_W        # 384px  — right 30% width for stickman
BG_COLOR   = (250, 248, 238)  # cream background


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _measure_text_with_tracking(draw, text, font, tracking):
    total_w = 0
    max_h = 0
    for char in text:
        bb = draw.textbbox((0, 0), char, font=font)
        cw = bb[2] - bb[0]
        ch = bb[3] - bb[1]
        total_w += cw + tracking
        max_h = max(max_h, ch)
    if text:
        total_w -= tracking
    return total_w, max_h


def _draw_text_with_tracking(draw, xy, text, font, fill, stroke_w=0, stroke_fill=None, tracking=0):
    x, y = xy
    for char in text:
        bb = draw.textbbox((0, 0), char, font=font)
        cw = bb[2] - bb[0]
        if stroke_w > 0 and stroke_fill:
            draw.text((x, y), char, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)
        else:
            draw.text((x, y), char, font=font, fill=fill)
        x += cw + tracking


def _prepare_text_layout(draw, text):
    text = text.upper().strip()
    words = text.split()
    if len(words) >= 2:
        mid = (len(words) + 1) // 2
        # Keep number + unit pairs (e.g., '45' and 'C') together on the same line
        if mid < len(words) and re.match(r"^\d+$", words[mid - 1]) and re.match(r"^[A-Z]$", words[mid]):
            mid += 1
        elif mid > 1 and re.match(r"^\d+$", words[mid - 2]) and re.match(r"^[A-Z]$", words[mid - 1]):
            mid -= 1
        lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        lines = [l for l in lines if l]
    else:
        lines = [text]

    font_size = int(TEXT_H * 0.44)  # ~132px start
    font = _get_font(font_size)
    tracking = max(4, int(font_size * 0.05))

    max_allowed_w = int(W * 0.88)
    for _ in range(50):
        max_w = 0
        for line in lines:
            lw, _ = _measure_text_with_tracking(draw, line, font, tracking)
            max_w = max(max_w, lw)
        if max_w <= max_allowed_w or font_size <= 24:
            break
        font_size = int(font_size * 0.93)
        font = _get_font(font_size)
        tracking = max(3, int(font_size * 0.05))

    line_gap = int(font_size * 0.18)

    dims = [_measure_text_with_tracking(draw, l, font, tracking) for l in lines]
    total_h = sum(d[1] for d in dims) + line_gap * (len(lines) - 1)
    curr_y = max(10, (TEXT_H - total_h) // 2)

    styles = [
        {"bg": (255, 215, 0, 255), "text": (0, 0, 0, 255), "stroke": None, "stroke_w": 0},
        {"bg": (225, 30, 30, 255),  "text": (255, 255, 255, 255), "stroke": (0, 0, 0, 255), "stroke_w": max(2, int(font_size * 0.03))},
        {"bg": (20, 20, 20, 255),   "text": (255, 255, 255, 255), "stroke": None, "stroke_w": 0}
    ]

    layout = []
    for i, line in enumerate(lines):
        lw, lh = dims[i]
        style = styles[i % len(styles)]
        
        pad_x = int(font_size * 0.30)
        pad_y = int(font_size * 0.16)
        
        banner_w = lw + pad_x * 2
        banner_h = lh + pad_y * 2
        bx1 = (W - banner_w) // 2
        by1 = curr_y - pad_y // 2
        bx2 = bx1 + banner_w
        by2 = by1 + banner_h

        tx = bx1 + pad_x
        ty = by1 + pad_y // 2

        layout.append({
            "line": line,
            "banner_box": [bx1, by1, bx2, by2],
            "text_pos": (tx, ty),
            "style": style,
            "font_size": font_size
        })
        curr_y += banner_h + line_gap

    return layout, font, tracking


def _draw_banners(canvas: Image.Image, layout: list) -> None:
    draw = ImageDraw.Draw(canvas)
    for item in layout:
        bx1, by1, bx2, by2 = item["banner_box"]
        style = item["style"]
        font_size = item["font_size"]
        
        shadow_off = max(4, int(font_size * 0.05))
        draw.rounded_rectangle(
            [bx1 + shadow_off, by1 + shadow_off, bx2 + shadow_off, by2 + shadow_off],
            radius=14,
            fill=(0, 0, 0, 90)
        )
        
        draw.rounded_rectangle(
            [bx1, by1, bx2, by2],
            radius=14,
            fill=style["bg"],
            outline=(0, 0, 0, 255),
            width=max(3, int(font_size * 0.04))
        )


def _draw_text_letters(canvas: Image.Image, layout: list, font, tracking) -> None:
    draw = ImageDraw.Draw(canvas)
    for item in layout:
        line = item["line"]
        tx, ty = item["text_pos"]
        style = item["style"]
        
        _draw_text_with_tracking(
            draw,
            (tx, ty),
            line,
            font,
            style["text"],
            stroke_w=style["stroke_w"],
            stroke_fill=style["stroke"],
            tracking=tracking
        )


def _make_bg_transparent(img: Image.Image, thresh: int = 60) -> Image.Image:
    """Removes off-white/light background completely to ensure 100% transparent blending with zero box edges."""
    img = img.convert("RGBA")
    w, h = img.size
    
    # 1. Floodfill from all 4 corners + edge midpoints with high tolerance
    sample_points = [
        (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
        (w // 2, 0), (0, h // 2), (w - 1, h // 2), (w // 2, h - 1)
    ]
    for pt in sample_points:
        try:
            ImageDraw.floodfill(img, pt, (0, 0, 0, 0), thresh=thresh)
        except Exception:
            pass
            
    # 2. Color keying pass: Convert remaining near-cream/white pixels near edges to transparent
    import numpy as np
    data = np.array(img)
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    
    # Identify light/off-white background pixels (R>235, G>235, B>225)
    light_bg_mask = (r > 235) & (g > 235) & (b > 220) & (a > 0)
    
    # Convert light background mask to transparent
    data[..., 3][light_bg_mask] = 0
    
    return Image.fromarray(data, "RGBA")


def _overlay_brand_badge(obj: Image.Image, brand_name: str = "NETFLIX") -> Image.Image:
    """Overlays an authentic, 100% proper brand logo wordmark (e.g. NETFLIX) onto doodle objects for instant viewer recognition."""
    if not brand_name:
        return obj
    
    obj = obj.convert("RGBA")
    text = brand_name.upper().strip()
    
    # Load bold display font
    font = _get_font(int(obj.height * 0.16))
    
    # Calculate text dimensions
    dummy_draw = ImageDraw.Draw(obj)
    bb = dummy_draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    
    # Create brand badge image
    pad_x, pad_y = 16, 8
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    badge = Image.new("RGBA", (bw + 16, bh + 16), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge)
    
    # 1. White outer sticker outline
    bdraw.rounded_rectangle([2, 2, bw + 14, bh + 14], radius=12, fill=(255, 255, 255, 255))
    # 2. Black doodle border
    bdraw.rounded_rectangle([6, 6, bw + 10, bh + 10], radius=10, fill=(0, 0, 0, 255))
    # 3. Netflix Official Red Fill (#E50914)
    bdraw.rounded_rectangle([9, 9, bw + 7, bh + 7], radius=8, fill=(229, 9, 20, 255))
    
    # 4. White Bold "NETFLIX" Text with dark stroke
    tx = (bw + 16 - tw) // 2
    ty = (bh + 16 - th) // 2 - 2
    _draw_text_with_tracking(bdraw, (tx, ty), text, font, fill=(255, 255, 255, 255), stroke_w=3, stroke_fill=(0, 0, 0, 255))
    
    # Place badge at top-left corner of the object area to prevent overlapping
    px, py = 10, 10
    obj.paste(badge, (px, py), badge)
    return obj


def _paste_object(canvas: Image.Image, img_path: str, min_y: int = OBJ_Y, brand_name: str = None) -> None:
    """Fit and paste object into bottom-left zone (X: 0–896) ensuring zero text overlay and clean single subject layout."""
    if not os.path.exists(img_path):
        return
    obj = Image.open(img_path)
    obj = _make_bg_transparent(obj)
    
    top_limit = max(OBJ_Y, min_y + 10)
    avail_h = H - top_limit - int(H * 0.03)
    avail_w = OBJ_W - 40
    
    scale = min(avail_w / obj.width, avail_h / obj.height)
    new_w, new_h = int(obj.width * scale), int(obj.height * scale)
    obj = obj.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Position object on the left side below text banners
    px = max(20, (OBJ_W - new_w) // 2)
    py = H - new_h - int(H * 0.03)
    if py < top_limit:
        py = top_limit
    canvas.paste(obj, (px, py), obj)


def _add_sticker_effect(stick: Image.Image, outline_width: int = 7, outline_color: tuple = (255, 255, 255, 255), shadow_color: tuple = (0, 0, 0, 90)) -> Image.Image:
    """Adds a crisp professional white sticker outline and drop shadow around the stickman."""
    from PIL import ImageFilter
    w, h = stick.size
    pad = outline_width * 2 + 10
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    alpha = stick.split()[3]

    outline_mask = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    outline_mask.paste(alpha, (pad, pad))
    expanded_mask = outline_mask.filter(ImageFilter.MaxFilter(outline_width * 2 + 1))

    shadow = Image.new("RGBA", (w + pad * 2, h + pad * 2), shadow_color)
    shadow_blur = expanded_mask.filter(ImageFilter.GaussianBlur(5))
    out.paste(shadow, (6, 6), shadow_blur)

    border = Image.new("RGBA", (w + pad * 2, h + pad * 2), outline_color)
    out.paste(border, (0, 0), expanded_mask)

    out.paste(stick, (pad, pad), stick)
    return out


def _paste_stickman(canvas: Image.Image, pose_name: str, cap: bool = False, cap_color: str = "green") -> None:
    """Fit, apply white sticker outline, and paste stickman into bottom-right zone (X: 896–1280, Y: 302–720)."""
    if pose_name not in stickman_engine.ANIMATIONS:
        pose_name = "mind_blown"
    try:
        frames = stickman_engine.get_animation_frames(pose_name, loops=1, cx=540, cy=1380, s=1.0,
                                                      cap=cap, cap_color=cap_color)
        stick = frames[len(frames) // 2] if frames else frames[0]
    except Exception:
        frames = stickman_engine.get_animation_frames("mind_blown", loops=1, cap=cap, cap_color=cap_color)
        stick = frames[0]

    bbox = stick.getbbox()
    if bbox:
        stick = stick.crop(bbox)

    # Apply professional sticker outline & drop shadow for high visibility
    stick = _add_sticker_effect(stick, outline_width=7, outline_color=(255, 255, 255, 255))

    # Scale to fill right 30% x bottom 60% zone
    scale = min(STICK_W / stick.width, OBJ_H / stick.height)
    new_w, new_h = int(stick.width * scale), int(stick.height * scale)
    stick = stick.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Bottom-align in stickman zone
    px = STICK_X + (STICK_W - new_w) // 2
    py = H - new_h - int(H * 0.02)
    canvas.paste(stick, (px, py), stick)



def generate_thumbnail(
    prompt: str,
    text_overlay: str,
    pose_name: str = "mind_blown",
    output_path: str = "thumbnail.png",
    cap: bool = False,
    cap_color: str = "green",
    use_ai: bool = True,
    subject_image_path: str = None,
    brand_name: str = None,
    include_stickman: bool = False,
    layout_mode: str = "split"  # "split" (one side text, one side image) or "centered"
) -> str:
    """
    Builds YouTube thumbnail in Pure 2D Doodle Style with Patrick Hand handmade font:
    - Left Side: Large Patrick Hand Doodle Yellow Text (thick black marker outline + drop shadow)
    - Right Side: Large Prominent 2D Doodle Subject
    - Stickman: Omitted by default for clean, high-impact focus
    """
    tmp_obj = output_path.replace(".png", "_obj_tmp.png")

    if not brand_name:
        combined_str = f"{prompt} {text_overlay}".upper()
        if "NETFLIX" in combined_str:
            brand_name = "NETFLIX"
        elif "BLOCKBUSTER" in combined_str:
            brand_name = "BLOCKBUSTER"

    if subject_image_path and os.path.exists(subject_image_path):
        tmp_obj = subject_image_path
    elif use_ai or not prompt:
        print(f"[ThumbnailGen] Generating doodle object: '{prompt}'...")
        style = (
            ", clean 2D vector doodle illustration, thick black outlines, "
            "vibrant flat solid color fills, plain light cream background, "
            "single compact centered subject, no text, no humans, no stickman."
        )
        gen_ok = False
        try:
            from gflow_assistant import generate_imagen_image
            gen_ok = generate_imagen_image(prompt + style, tmp_obj, aspect_ratio="16:9")
        except Exception as e:
            print(f"[ThumbnailGen] gflow attempt error: {e}")
        
        if not gen_ok or not os.path.exists(tmp_obj) or os.path.getsize(tmp_obj) < 1000:
            print(f"[ThumbnailGen] Falling back to Cloudflare Workers...")
            hf_image_gen.generate_image_hf(prompt + style, tmp_obj)
    else:
        proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(output_path)))
        sc1_p = os.path.join(proj_dir, "06_Images", "Final", "Scene_01.png")
        if not os.path.exists(sc1_p):
            sc1_p = os.path.join(proj_dir, "06_Images", "Approved", "Scene_01.png")
        if os.path.exists(sc1_p):
            tmp_obj = sc1_p
        else:
            gen_ok = False
            try:
                from gflow_assistant import generate_imagen_image
                gen_ok = generate_imagen_image(prompt, tmp_obj, aspect_ratio="16:9")
            except Exception:
                pass
            if not gen_ok or not os.path.exists(tmp_obj):
                hf_image_gen.generate_image_hf(prompt, tmp_obj)

    # 2. Build cream canvas
    canvas = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(canvas)

    # 3. Clean and wrap text for Patrick Hand font (Smart stacking for maximum HUGE font size)
    text_clean = text_overlay.upper().strip()
    words = text_clean.split()
    if len(words) >= 6:
        # Stack into 3 punchy lines for maximum readability & giant font size
        p1 = (len(words) + 2) // 3
        p2 = p1 + (len(words) - p1 + 1) // 2
        lines = [" ".join(words[:p1]), " ".join(words[p1:p2]), " ".join(words[p2:])]
    elif len(words) in [4, 5]:
        p = (len(words) + 1) // 2
        lines = [" ".join(words[:p]), " ".join(words[p:])]
    elif len(words) == 3:
        lines = [words[0], " ".join(words[1:])]
    else:
        lines = [text_clean]

    font_path = r"D:\youtube_automation_agent\PatrickHand-Regular.ttf"
    if not os.path.exists(font_path):
        font_path = next((p for p in FONT_PATHS if os.path.exists(p)), None)

    if layout_mode == "split":
        # ── SPLIT LAYOUT: ULTRA-LARGE TEXT (LEFT) + PROMINENT OBJECT (RIGHT) ──
        # Left Text Zone: X: 35 to 595 (width: 560px)
        # 30px Clean Gap: X: 595 to 625
        # Right Object Zone: X: 625 to 1260 (width: 635px, height: 680px)

        text_zone_left = 35
        max_allowed_w = 580
        font_size = 165
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

        # Letter tracking, dedicated word gap, and vertical line gap
        letter_spacing = max(4, int(font_size * 0.04))
        word_space = int(font_size * 0.52)   # Spacious, clear separation between words
        line_gap = int(font_size * 0.28)     # Comfortable vertical gap between lines

        def _get_char_width(ch):
            if ch == " ":
                return word_space
            b = draw.textbbox((0, 0), ch, font=font)
            return (b[2] - b[0]) + letter_spacing

        def _get_spaced_line_width(txt):
            if not txt:
                return 0
            return sum(_get_char_width(ch) for ch in txt) - letter_spacing

        # Fit font size to maximum readable bounds with word and line spacing
        for _ in range(40):
            max_w = max(_get_spaced_line_width(l) for l in lines)
            line_boxes = [draw.textbbox((0, 0), l, font=font) for l in lines]
            total_h = sum(b[3] - b[1] for b in line_boxes) + line_gap * (len(lines) - 1)
            if (max_w <= max_allowed_w and total_h <= H * 0.88) or font_size <= 50:
                break
            font_size -= 3
            font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
            letter_spacing = max(4, int(font_size * 0.04))
            word_space = int(font_size * 0.52)
            line_gap = int(font_size * 0.28)

        line_boxes = [draw.textbbox((0, 0), l, font=font) for l in lines]
        line_heights = [b[3] - b[1] for b in line_boxes]
        total_text_h = sum(line_heights) + line_gap * (len(lines) - 1)
        text_start_y = (H - total_text_h) // 2

        # Paste Object in Right Zone (X: 630 to 1260)
        if os.path.exists(tmp_obj):
            obj_raw = Image.open(tmp_obj)
            obj_trans = _make_bg_transparent(obj_raw)
            bbox = obj_trans.getbbox()
            if bbox:
                obj_trans = obj_trans.crop(bbox)

            obj_zone_left = 625
            avail_obj_w = 635
            avail_obj_h = int(H * 0.94)  # 676px height

            scale = min(avail_obj_w / obj_trans.width, avail_obj_h / obj_trans.height)
            new_w, new_h = int(obj_trans.width * scale), int(obj_trans.height * scale)
            obj_resized = obj_trans.resize((new_w, new_h), Image.Resampling.LANCZOS)

            obj_x = obj_zone_left + (avail_obj_w - new_w) // 2
            obj_y = (H - new_h) // 2
            canvas.paste(obj_resized, (obj_x, obj_y), obj_resized)

        # Draw Left Side Patrick Hand Extra-Thick Bold Doodle Yellow Text with proper word & line spacing
        curr_y = text_start_y
        yellow_fill = (255, 225, 0, 255)
        black_outline = (0, 0, 0, 255)
        shadow_color = (0, 0, 0, 100)

        # Multi-layer bold rendering: fattens the font itself + gives a clean crisp outline
        bold_core_stroke = max(4, int(font_size * 0.040))     # Fattens yellow letter body
        black_contour_stroke = bold_core_stroke + max(3, int(font_size * 0.025))  # Clean black border

        for i, line in enumerate(lines):
            lw = _get_spaced_line_width(line)
            lx = text_zone_left + (max_allowed_w - lw) // 2

            # 1. Soft drop shadow pass (offset 5, 5)
            cx = lx + 5
            cy = curr_y + 5
            for ch in line:
                if ch != " ":
                    draw.text((cx, cy), ch, font=font, fill=shadow_color, stroke_width=black_contour_stroke, stroke_fill=shadow_color)
                cx += _get_char_width(ch)

            # 2. Black contour outline pass
            cx = lx
            for ch in line:
                if ch != " ":
                    draw.text((cx, curr_y), ch, font=font, fill=black_outline, stroke_width=black_contour_stroke, stroke_fill=black_outline)
                cx += _get_char_width(ch)

            # 3. Extra-Thick Bold Yellow Core pass (fattens the font body)
            cx = lx
            for ch in line:
                if ch != " ":
                    draw.text((cx, curr_y), ch, font=font, fill=yellow_fill, stroke_width=bold_core_stroke, stroke_fill=yellow_fill)
                cx += _get_char_width(ch)

            curr_y += line_heights[i] + line_gap

    else:
        # ── CENTERED LAYOUT: TOP TEXT, CENTER IMAGE ──
        font_size = 110
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        for _ in range(25):
            max_w = max(draw.textbbox((0, 0), l, font=font)[2] - draw.textbbox((0, 0), l, font=font)[0] for l in lines)
            if max_w < W * 0.90 or font_size <= 30:
                break
            font_size -= 4
            font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

        line_heights = [draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1] for l in lines]
        total_text_h = sum(line_heights) + (len(lines) - 1) * 15
        text_start_y = 35

        if os.path.exists(tmp_obj):
            obj_raw = Image.open(tmp_obj)
            obj_trans = _make_bg_transparent(obj_raw)
            avail_obj_h = H - (text_start_y + total_text_h + 30) - 20
            avail_obj_w = int(W * 0.85)

            scale = min(avail_obj_w / obj_trans.width, avail_obj_h / obj_trans.height)
            new_w, new_h = int(obj_trans.width * scale), int(obj_trans.height * scale)
            obj_resized = obj_trans.resize((new_w, new_h), Image.Resampling.LANCZOS)

            obj_x = (W - new_w) // 2
            obj_y = text_start_y + total_text_h + 20 + max(0, (avail_obj_h - new_h) // 2)
            canvas.paste(obj_resized, (obj_x, obj_y), obj_resized)

        curr_y = text_start_y
        for i, line in enumerate(lines):
            bb = draw.textbbox((0, 0), line, font=font)
            lw = bb[2] - bb[0]
            lh = bb[3] - bb[1]
            lx = (W - lw) // 2

            draw.text((lx + 6, curr_y + 6), line, font=font, fill=(0, 0, 0, 180), stroke_width=8, stroke_fill=(0, 0, 0, 180))
            draw.text((lx, curr_y), line, font=font, fill=(255, 230, 0, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))
            curr_y += lh + 15

    # 4. Optional Stickman
    if include_stickman:
        _paste_stickman(canvas, pose_name, cap=cap, cap_color=cap_color)

    # Save and clean up
    canvas.convert("RGB").save(output_path, "PNG", quality=95)
    if os.path.exists(tmp_obj) and tmp_obj != subject_image_path:
        try:
            os.remove(tmp_obj)
        except Exception:
            pass

    print(f"[ThumbnailGen] SUCCESS! Saved to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_thumbnail(
        prompt="A woolly mammoth and small campfire",
        text_overlay="HOW THEY SURVIVED!",
        pose_name="mind_blown",
        output_path="test_thumb.png"
    )
