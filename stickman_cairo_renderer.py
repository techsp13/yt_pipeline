"""
stickman_cairo_renderer.py — PyCairo renderer for the VERIFIED Sany character designs.
Matches the exact character from 00_FREE_HANDS_ALL_3_STICKMEN.png:
- Sany Explain: Tan safari vest with 4 pockets, olive shirt stripe, brown boots, brown cap with shaggy tufts
- Big round eyes with blink support, expressive eyebrows, audio-reactive mouth shapes
- White circle hands with black outline (natural free hands)
- Full 1920x1080 landscape native rendering so character is never cropped
"""

import math
import cairo
import numpy as np
from PIL import Image

from stickman_engine import (
    Pose, Keyframe, bake_keyframes, interp_pose,
    W, H, FPS, SCALE2, d2r, endpoint, lerp, ease,
)

# ── Cairo ↔ PIL ────────────────────────────────────────────────────────────────

def cairo_surface_to_pil(surface):
    surface.flush()
    buf = surface.get_data()
    arr = np.frombuffer(buf, dtype=np.uint8).reshape(
        surface.get_height(), surface.get_width(), 4
    ).copy()
    arr[:, :, [0, 2]] = arr[:, :, [2, 0]]  # BGRA → RGBA
    return Image.fromarray(arr, "RGBA")


# ── Colors ────────────────────────────────────────────────────────────────────

BLACK = (20, 20, 20)
WHITE = (255, 255, 255)

# Sany Explain (History)
VEST_TAN    = (195, 160, 110)
SHIRT_OLIVE = (95, 115, 75)
HAIR_BROWN  = (105, 65, 35)
BOOT_BROWN  = (90, 55, 30)

def _sc(ctx, rgb, a=1.0):
    ctx.set_source_rgba(rgb[0]/255, rgb[1]/255, rgb[2]/255, a)


def _bezier_pts(p0, p1, p2, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n; mt = 1 - t
        x = mt*mt*p0[0] + 2*mt*t*p1[0] + t*t*p2[0]
        y = mt*mt*p0[1] + 2*mt*t*p1[1] + t*t*p2[1]
        pts.append((x, y))
    return pts


# ── Character: Sany Explain (History) ─────────────────────────────────────────

def _draw_sany_explain(ctx, cx, cy, s, pose):
    """
    Renders Sany Explain matching the verified 00_FREE_HANDS_ALL_3_STICKMEN.png:
    - Brown shaggy dome cap + 4 triangle tufts
    - White round head, large round eyes, expressive eyebrows, mouth
    - Tan safari vest with 4 pockets & olive center shirt stripe
    - Free white circular hands
    - Brown boots
    """
    lw = max(2.5, 14 * s)
    arm_w = max(3.0, 22 * s)

    torso_w = 130 * s
    torso_h = 430 * s
    leg_len = 320 * s
    head_r  = 170 * s
    hand_r  = 25 * s

    lean_rad = math.radians(pose.torso_lean)
    lean_dx = torso_h * 0.3 * math.sin(lean_rad)

    hip_cx = cx + lean_dx * 0.2
    hip_y = cy + 180 * s + pose.bob * s
    sh_cx = cx - lean_dx
    sh_y = cy - 250 * s + pose.bob * s

    # ── LEGS ──
    ctx.set_line_width(arm_w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)

    # Left Leg
    l_hip_angle = pose.l_hip + pose.torso_lean * 0.5
    l_knee_x = hip_cx - 70 * s + leg_len * 0.45 * math.sin(d2r(l_hip_angle))
    l_knee_y = hip_y + leg_len * 0.45 * math.cos(d2r(l_hip_angle))
    l_foot_x = l_knee_x + leg_len * 0.55 * math.sin(d2r(l_hip_angle + pose.l_knee))
    l_foot_y = l_knee_y + leg_len * 0.55 * math.cos(d2r(l_hip_angle + pose.l_knee))

    _sc(ctx, BLACK)
    ctx.move_to(hip_cx - 70 * s, hip_y)
    ctx.line_to(l_knee_x, l_knee_y)
    ctx.line_to(l_foot_x, l_foot_y)
    ctx.stroke()

    # Right Leg
    r_hip_angle = pose.r_hip + pose.torso_lean * 0.5
    r_knee_x = hip_cx + 70 * s + leg_len * 0.45 * math.sin(d2r(r_hip_angle))
    r_knee_y = hip_y + leg_len * 0.45 * math.cos(d2r(r_hip_angle))
    r_foot_x = r_knee_x + leg_len * 0.55 * math.sin(d2r(r_hip_angle + pose.r_knee))
    r_foot_y = r_knee_y + leg_len * 0.55 * math.cos(d2r(r_hip_angle + pose.r_knee))

    _sc(ctx, BLACK)
    ctx.move_to(hip_cx + 70 * s, hip_y)
    ctx.line_to(r_knee_x, r_knee_y)
    ctx.line_to(r_foot_x, r_foot_y)
    ctx.stroke()

    # ── BOOTS ──
    boot_w = 110 * s
    boot_h = 50 * s
    for fx, fy in [(l_foot_x, l_foot_y), (r_foot_x, r_foot_y)]:
        ctx.save()
        ctx.translate(fx, fy)
        ctx.scale(boot_w / 2, boot_h / 2)
        ctx.arc(0, 0, 1.0, 0, 2 * math.pi)
        ctx.restore()
        _sc(ctx, BOOT_BROWN)
        ctx.fill_preserve()
        _sc(ctx, BLACK)
        ctx.set_line_width(max(2, 8 * s))
        ctx.stroke()

    # ── TORSO: Olive Shirt + Tan Safari Vest ──
    shirt = [
        (sh_cx - torso_w, sh_y),
        (sh_cx + torso_w, sh_y),
        (hip_cx + 105 * s, hip_y),
        (hip_cx - 105 * s, hip_y),
    ]
    ctx.move_to(*shirt[0])
    for pt in shirt[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    _sc(ctx, SHIRT_OLIVE)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(lw)
    ctx.stroke()

    # Left Vest Panel
    vest_l = [
        (sh_cx - torso_w, sh_y),
        (sh_cx - 15 * s, sh_y),
        (hip_cx - 20 * s, hip_y),
        (hip_cx - 105 * s, hip_y),
    ]
    ctx.move_to(*vest_l[0])
    for pt in vest_l[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    _sc(ctx, VEST_TAN)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(max(2, 10 * s))
    ctx.stroke()

    # Right Vest Panel
    vest_r = [
        (sh_cx + 15 * s, sh_y),
        (sh_cx + torso_w, sh_y),
        (hip_cx + 105 * s, hip_y),
        (hip_cx + 20 * s, hip_y),
    ]
    ctx.move_to(*vest_r[0])
    for pt in vest_r[1:]:
        ctx.line_to(*pt)
    ctx.close_path()
    _sc(ctx, VEST_TAN)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(max(2, 10 * s))
    ctx.stroke()

    # 4 Vest Pockets
    pw, ph = 50 * s, 60 * s
    pocket_positions = [
        (sh_cx - 95 * s, sh_y + torso_h * 0.32),
        (sh_cx + 45 * s, sh_y + torso_h * 0.32),
        (sh_cx - 95 * s, sh_y + torso_h * 0.63),
        (sh_cx + 45 * s, sh_y + torso_h * 0.63),
    ]
    for px, py in pocket_positions:
        ctx.rectangle(px, py, pw, ph)
        _sc(ctx, VEST_TAN)
        ctx.fill_preserve()
        _sc(ctx, BLACK)
        ctx.set_line_width(max(2, 6 * s))
        ctx.stroke()

    # Center Olive Stripe
    ctx.rectangle(sh_cx - 10 * s, sh_y, 20 * s, torso_h)
    _sc(ctx, SHIRT_OLIVE)
    ctx.fill()

    # ── ARMS & HANDS (Bezier Curves) ──
    # Left Arm
    l_sh_x = sh_cx - 120 * s
    l_sh_y = sh_y
    l_elbow_angle = pose.l_shoulder + pose.torso_lean
    l_elbow_x = l_sh_x + 95 * s * math.sin(d2r(l_elbow_angle))
    l_elbow_y = l_sh_y + 95 * s * math.cos(d2r(l_elbow_angle))
    l_hand_angle = l_elbow_angle + pose.l_elbow
    l_hand_x = l_elbow_x + 85 * s * math.sin(d2r(l_hand_angle))
    l_hand_y = l_elbow_y + 85 * s * math.cos(d2r(l_hand_angle))

    pts = _bezier_pts((l_sh_x, l_sh_y), (l_elbow_x, l_elbow_y), (l_hand_x, l_hand_y))
    _sc(ctx, BLACK)
    ctx.set_line_width(arm_w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.stroke()

    # Left Hand (White Circle)
    ctx.arc(l_hand_x, l_hand_y, hand_r, 0, 2 * math.pi)
    _sc(ctx, WHITE)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(max(2, 10 * s))
    ctx.stroke()

    # Right Arm
    r_sh_x = sh_cx + 120 * s
    r_sh_y = sh_y
    r_elbow_angle = pose.r_shoulder + pose.torso_lean
    r_elbow_x = r_sh_x + 95 * s * math.sin(d2r(r_elbow_angle))
    r_elbow_y = r_sh_y + 95 * s * math.cos(d2r(r_elbow_angle))
    r_hand_angle = r_elbow_angle + pose.r_elbow
    r_hand_x = r_elbow_x + 85 * s * math.sin(d2r(r_hand_angle))
    r_hand_y = r_elbow_y + 85 * s * math.cos(d2r(r_hand_angle))

    pts = _bezier_pts((r_sh_x, r_sh_y), (r_elbow_x, r_elbow_y), (r_hand_x, r_hand_y))
    _sc(ctx, BLACK)
    ctx.set_line_width(arm_w)
    ctx.move_to(*pts[0])
    for pt in pts[1:]:
        ctx.line_to(*pt)
    ctx.stroke()

    # Right Hand (White Circle)
    ctx.arc(r_hand_x, r_hand_y, hand_r, 0, 2 * math.pi)
    _sc(ctx, WHITE)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(max(2, 10 * s))
    ctx.stroke()

    # ── HEAD ──
    hx = sh_cx + head_r * 0.12 * math.sin(d2r(pose.head_tilt))
    hy = sh_y - head_r - 8 * s + head_r * math.sin(d2r(pose.head_nod)) * 0.1

    # White Head Circle
    ctx.arc(hx, hy, head_r, 0, 2 * math.pi)
    _sc(ctx, WHITE)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(max(2, 18 * s))
    ctx.stroke()

    # Brown Shaggy Cap (Dome chord over top of head)
    x0, y0 = hx - head_r - 10 * s, hy - head_r - 20 * s
    x1, y1 = hx + head_r + 10 * s, hy - 35 * s
    cap_cx = (x0 + x1) / 2.0
    cap_cy = (y0 + y1) / 2.0
    cap_rx = abs(x1 - x0) / 2.0
    cap_ry = abs(y1 - y0) / 2.0

    ctx.save()
    ctx.translate(cap_cx, cap_cy)
    ctx.scale(cap_rx, cap_ry)
    ctx.arc(0, 0, 1.0, math.radians(160), math.radians(380))
    ctx.close_path()
    ctx.restore()
    _sc(ctx, HAIR_BROWN)
    ctx.fill_preserve()
    _sc(ctx, BLACK)
    ctx.set_line_width(max(2, 12 * s))
    ctx.stroke()

    # 4 Hair Tufts / Spikes
    tufts = [
        [(hx - head_r - 10*s, hy - 50*s), (hx - head_r - 35*s, hy - 100*s), (hx - head_r + 15*s, hy - 120*s)],
        [(hx - 70*s, hy - head_r - 10*s), (hx - 40*s, hy - head_r - 45*s), (hx + 5*s, hy - head_r - 10*s)],
        [(hx + 30*s, hy - head_r - 10*s), (hx + 70*s, hy - head_r - 45*s), (hx + 105*s, hy - head_r - 10*s)],
        [(hx + head_r - 15*s, hy - 120*s), (hx + head_r + 35*s, hy - 100*s), (hx + head_r + 10*s, hy - 50*s)],
    ]
    for tf in tufts:
        ctx.move_to(*tf[0])
        ctx.line_to(*tf[1])
        ctx.line_to(*tf[2])
        ctx.close_path()
        _sc(ctx, HAIR_BROWN)
        ctx.fill_preserve()
        _sc(ctx, BLACK)
        ctx.set_line_width(max(1.5, 5 * s))
        ctx.stroke()

    # ── EYEBROWS ──
    brow_lw = max(2, 12 * s)
    brow_y = hy - 25 * s - pose.eyebrow * 12 * s
    _sc(ctx, BLACK)
    ctx.set_line_width(brow_lw)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(hx - 80 * s, brow_y)
    ctx.line_to(hx - 20 * s, brow_y - 10 * s)
    ctx.stroke()
    ctx.move_to(hx + 20 * s, brow_y - 10 * s)
    ctx.line_to(hx + 80 * s, brow_y)
    ctx.stroke()

    # ── EYES (Large Round with Blink Support) ──
    eye_rx = 20 * s
    eye_ry = 22.5 * s
    eye_y = hy + 20 * s
    look = pose.eye_look * 10 * s
    blink_scale = max(0.05, 1.0 - pose.blink)

    for side in [-1, 1]:
        ex = hx + side * 55 * s + look
        if blink_scale < 0.15:
            _sc(ctx, BLACK)
            ctx.set_line_width(max(2, 5 * s))
            ctx.move_to(ex - eye_rx, eye_y)
            ctx.line_to(ex + eye_rx, eye_y)
            ctx.stroke()
        else:
            ctx.save()
            ctx.translate(ex, eye_y)
            ctx.scale(eye_rx, eye_ry * blink_scale)
            ctx.arc(0, 0, 1.0, 0, 2 * math.pi)
            ctx.restore()
            _sc(ctx, BLACK)
            ctx.fill()

    # ── MOUTH (Expression / Audio-Reactive Lip Sync) ──
    my = hy + 95 * s
    mw = 60 * s
    mh = 35 * s
    mlw = max(2, 12 * s)
    e = pose.expression

    _sc(ctx, BLACK)
    ctx.set_line_width(mlw)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    if e == "smile":
        ctx.save()
        ctx.translate(hx, my)
        ctx.scale(mw, mh)
        ctx.arc(0, 0, 1.0, math.radians(10), math.radians(170))
        ctx.restore()
        ctx.stroke()
    elif e == "big_smile":
        ctx.save()
        ctx.translate(hx, my)
        ctx.scale(mw * 1.2, mh * 1.2)
        ctx.arc(0, 0, 1.0, math.radians(10), math.radians(170))
        ctx.restore()
        ctx.stroke()
    elif e == "neutral":
        ctx.move_to(hx - mw * 0.6, my)
        ctx.line_to(hx + mw * 0.6, my)
        ctx.stroke()
    elif e == "open":
        # Talking mouth: open oval with slight tongue/depth
        ctx.save()
        ctx.translate(hx, my)
        ctx.scale(mw * 0.65, mh * 0.85)
        ctx.arc(0, 0, 1.0, 0, 2 * math.pi)
        ctx.restore()
        _sc(ctx, (30, 20, 20))
        ctx.fill_preserve()
        _sc(ctx, BLACK)
        ctx.set_line_width(max(2, 8 * s))
        ctx.stroke()
    elif e == "surprised":
        ctx.save()
        ctx.translate(hx, my)
        ctx.scale(mw * 0.5, mh * 1.1)
        ctx.arc(0, 0, 1.0, 0, 2 * math.pi)
        ctx.restore()
        _sc(ctx, BLACK)
        ctx.stroke()
    elif e == "sad":
        ctx.save()
        ctx.translate(hx, my)
        ctx.scale(mw, mh)
        ctx.arc(0, 0, 1.0, math.radians(190), math.radians(350))
        ctx.restore()
        ctx.stroke()
    elif e == "thinking":
        ctx.move_to(hx - mw * 0.2, my)
        ctx.line_to(hx + mw * 0.6, my - mh * 0.3)
        ctx.stroke()
    elif e == "smirk":
        ctx.save()
        ctx.translate(hx + mw * 0.2, my)
        ctx.scale(mw * 0.5, mh * 0.6)
        ctx.arc(0, 0, 1.0, math.radians(10), math.radians(170))
        ctx.restore()
        ctx.stroke()


# ── Main Render API ───────────────────────────────────────────────────────────

def render_pose_cairo(pose, bg_color=(0, 0, 0, 0), canvas_w=1920, canvas_h=1080):
    """
    Renders the VERIFIED Sany Explain character onto a canvas of size (canvas_w, canvas_h).
    Defaults to 1920x1080 landscape for YouTube video pipeline.
    """
    cw = int(canvas_w)
    ch = int(canvas_h)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, cw, ch)
    ctx = cairo.Context(surface)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)

    # Transparent background
    if bg_color and any(c > 0 for c in bg_color[:3]):
        _sc(ctx, bg_color[:3], bg_color[3]/255 if len(bg_color) > 3 else 1.0)
        ctx.rectangle(0, 0, cw, ch)
        ctx.fill()
    else:
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.rectangle(0, 0, cw, ch)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)

    s = pose.scale
    cx = pose.cx
    cy = pose.cy + pose.bob

    _draw_sany_explain(ctx, cx, cy, s, pose)

    return cairo_surface_to_pil(surface)


# ── Secondary motion physics ──────────────────────────────────────────────────

def add_secondary_motion(poses, fps=30, breathing=True, hair_bounce=True):
    """Adds organic physics: subtle breathing sway + spring-damper head follow-through."""
    if not poses:
        return poses
    if breathing:
        for i, p in enumerate(poses):
            t = i / fps
            p.bob += 2.0 * math.sin(2 * math.pi * 0.3 * t)
    if hair_bounce and len(poses) > 1:
        velocity = 0.0
        damping = 0.85
        stiffness = 0.15
        for i in range(1, len(poses)):
            target = poses[i].head_tilt
            current = poses[i - 1].head_tilt
            force = (target - current) * stiffness
            velocity = (velocity + force) * damping
            poses[i].head_tilt = current + velocity
            poses[i].eye_look += velocity * 0.02
    return poses
