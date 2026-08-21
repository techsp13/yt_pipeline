"""
stickman_engine.py  v3
Animated presenter engine — walk + gesture sequences, narration-driven.
"""

import math, os, sys, random, shutil, tempfile, subprocess
from dataclasses import dataclass, field
from typing import List, Tuple
from PIL import Image, ImageDraw

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H   = 1080, 1920
FPS    = 30
SCALE2 = 1

def d2r(deg): return math.radians(deg)
def endpoint(x, y, angle_deg, length):
    r = d2r(angle_deg)
    return (x + length * math.sin(r), y + length * math.cos(r))
def lerp(a, b, t):   return a + (b - a) * t
def ease(t):          return t * t * (3 - 2 * t)

# ─────────────────────────────────────────────────────────────────────────────
# POSE
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Pose:
    cx:    float = 540.0
    cy:    float = 1380.0
    scale: float = 1.0
    torso_lean: float = 0.0
    bob:        float = 0.0
    l_shoulder: float = -20.0
    l_elbow:    float =  30.0
    r_shoulder: float = -20.0
    r_elbow:    float =  30.0
    l_hip:      float =   0.0
    l_knee:     float =   0.0
    l_ankle:    float =   0.0
    r_hip:      float =   0.0
    r_knee:     float =   0.0
    r_ankle:    float =   0.0
    head_tilt:  float =   0.0
    head_nod:   float =   0.0
    expression: str   = "smile"
    blink:      float =   0.0
    eye_look:   float =   0.0
    eyebrow:    float =   0.0
    cap:        bool  =   False
    cap_color:  str   =   "green"   # doodle cap color (green/red/blue/yellow/orange/purple/black)
    beard:      bool  =   False


def interp_pose(a: Pose, b: Pose, t: float, use_ease=True) -> Pose:
    e = ease(t) if use_ease else t
    kw = {}
    for k in Pose.__dataclass_fields__:
        va, vb = getattr(a, k), getattr(b, k)
        kw[k] = va if isinstance(va, str) else lerp(va, vb, e)
    return Pose(**kw)


# ─────────────────────────────────────────────────────────────────────────────
# RENDERER
# ─────────────────────────────────────────────────────────────────────────────
def _line(draw, p1, p2, color, w):
    draw.line([p1, p2], fill=color, width=w)
    r = w // 2
    for px, py in [p1, p2]:
        draw.ellipse([(px-r, py-r), (px+r, py+r)], fill=color)


def _dot(draw, p, r, color):
    px, py = p
    draw.ellipse([(px-r, py-r), (px+r, py+r)], fill=color)


# ── Doodle cap ────────────────────────────────────────────────────────────────
_CAP_COLORS = {
    "green":   (40, 175, 60, 255),
    "red":     (230, 45, 45, 255),
    "blue":    (35, 120, 230, 255),
    "yellow":  (250, 210, 40, 255),
    "orange":  (245, 130, 40, 255),
    "purple":  (150, 70, 200, 255),
    "black":   (30, 30, 30, 255),
}


def _draw_cap(draw, img, hcx, hcy, HR, pose, s=1.0):
    """Doodle-style baseball cap: flat fill, thick black outline, brim to the left.
    Drawn on its own layer so it rotates with head tilt, then composited over the head.
    The dome chord sits at the brow line and the brim stays left of the face, so
    both eyes and both eyebrows always remain fully visible.
    """
    if not pose.cap:
        return
    BLACK = (0, 0, 0, 255)
    fill  = _CAP_COLORS.get(str(pose.cap_color).lower(), _CAP_COLORS["green"])

    # Cap geometry is defined in head-local space (origin = head center, y down),
    # then stamped onto a dedicated layer so it can be rotated for head_tilt.
    LW    = int(HR * 4.2)          # layer width  (dome + long left brim)
    LH    = int(HR * 2.9)          # layer height
    HX    = LW * 0.5               # head-center x in layer coords
    HY    = HR * 1.45              # head-center y in layer coords
    layer = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    ld    = ImageDraw.Draw(layer)

    outline_w = max(2, int(4 * s))

    # 1. Dome — wide shallow half-ellipse; chord at 0.55·HR above center, well
    #    clear of the eyebrows (which sit at 0.47·HR above center).
    dome_w  = HR * 2.20            # full dome width — wider than the head
    dome_h  = HR * 0.85            # dome height above the chord
    chord_y = HY - HR * 0.55       # forehead line (cap rim)
    ld.pieslice([HX - dome_w / 2, chord_y - dome_h, HX + dome_w / 2, chord_y],
                180, 360, fill=fill, outline=BLACK, width=outline_w)

    # 2. Brim — chunky bill sweeping left; its right edge stays left of the
    #    left eyebrow (which spans from 0.59·HR to 0.05·HR left of center).
    brim = [
        (HX - HR * 0.75, chord_y),
        (HX - HR * 1.65, chord_y + HR * 0.20),
        (HX - HR * 1.48, chord_y + HR * 0.40),
        (HX - HR * 0.75, chord_y + HR * 0.23),
    ]
    ld.polygon(brim, fill=fill, outline=BLACK)

    # 3. Button on top
    btn_r = HR * 0.09
    btn_y = chord_y - dome_h + btn_r * 0.9
    ld.ellipse([HX - btn_r, btn_y - btn_r, HX + btn_r, btn_y + btn_r],
               fill=fill, outline=BLACK, width=max(2, int(2 * s)))

    # 4. Rotate with head tilt and composite over the head
    if pose.head_tilt:
        layer = layer.rotate(-pose.head_tilt, resample=Image.BICUBIC)
    img.alpha_composite(layer, (int(hcx - HX), int(hcy - HY)))


def render_pose(pose: Pose, bg_color=(0,0,0,0)) -> Image.Image:
    S  = SCALE2
    sw, sh = W * S, H * S
    img  = Image.new("RGBA", (sw, sh), bg_color)
    draw = ImageDraw.Draw(img)

    s   = pose.scale * 0.82 * S
    cx  = pose.cx  * S
    cy  = (pose.cy + pose.bob + 80) * S

    BLACK = (0, 0, 0, 255)
    WHITE = (255, 255, 255, 255)

    LIMB_W   = max(3, int(8  * s))
    TORSO_W  = max(3, int(9  * s))
    HEAD_R   = int(62 * s)
    NECK_LEN = int(12 * s)
    TORSO_H  = int(150 * s)
    UA_LEN   = int(85 * s)
    FA_LEN   = int(72 * s)
    TH_LEN   = int(110 * s)
    SH_LEN   = int(95 * s)

    def _curved_limb(P0, P1, P2, color, w, n_seg=14):
        pts = []
        for i in range(n_seg + 1):
            t = i / n_seg
            mt = 1.0 - t
            x = mt*mt*P0[0] + 2*mt*t*P1[0] + t*t*P2[0]
            y = mt*mt*P0[1] + 2*mt*t*P1[1] + t*t*P2[1]
            pts.append((x, y))
        for k in range(len(pts) - 1):
            _line(draw, pts[k], pts[k+1], color, w)

    lean = pose.torso_lean
    hip_x, hip_y = cx, cy
    sh_dx = TORSO_H * math.sin(d2r(lean))
    sh_dy = TORSO_H * math.cos(d2r(lean))
    torso_top_x = hip_x - sh_dx * 0.4
    torso_top_y = hip_y - sh_dy

    sh_cx, sh_cy = torso_top_x, torso_top_y
    _line(draw, (hip_x, hip_y), (sh_cx, sh_cy), BLACK, TORSO_W)

    l_sh_j  = (sh_cx, sh_cy)
    r_sh_j  = (sh_cx, sh_cy)
    l_hip_j = (hip_x, hip_y)
    r_hip_j = (hip_x, hip_y)

    def _draw_hand(hx, hy, side):
        hr = int(9 * s)
        draw.ellipse([(hx-hr, hy-hr), (hx+hr, hy+hr)], fill=BLACK)
        tx = hx + (side * hr * 0.6)
        ty = hy - hr * 1.2
        tr = int(4 * s)
        draw.ellipse([(tx-tr, ty-tr), (tx+tr, ty+tr)], fill=BLACK)
        draw.line([(hx, hy), (tx, ty)], fill=BLACK, width=int(5 * s))

    # Back limbs
    r_ua_end = endpoint(r_sh_j[0], r_sh_j[1], pose.r_shoulder + lean, UA_LEN)
    r_fa_end = endpoint(r_ua_end[0], r_ua_end[1], pose.r_shoulder + pose.r_elbow + lean, FA_LEN)
    _curved_limb(r_sh_j, r_ua_end, r_fa_end, BLACK, LIMB_W)
    _draw_hand(r_fa_end[0], r_fa_end[1], side=1)

    r_knee_pt  = endpoint(r_hip_j[0], r_hip_j[1], pose.r_hip + lean*0.5, TH_LEN)
    r_ankle_pt = endpoint(r_knee_pt[0], r_knee_pt[1], pose.r_hip + pose.r_knee + lean*0.3, SH_LEN)
    _curved_limb(r_hip_j, r_knee_pt, r_ankle_pt, BLACK, LIMB_W)

    # Front limbs
    l_ua_end = endpoint(l_sh_j[0], l_sh_j[1], pose.l_shoulder + lean, UA_LEN)
    l_fa_end = endpoint(l_ua_end[0], l_ua_end[1], pose.l_shoulder + pose.l_elbow + lean, FA_LEN)
    _curved_limb(l_sh_j, l_ua_end, l_fa_end, BLACK, LIMB_W)
    _draw_hand(l_fa_end[0], l_fa_end[1], side=-1)

    l_knee_pt  = endpoint(l_hip_j[0], l_hip_j[1], pose.l_hip + lean*0.5, TH_LEN)
    l_ankle_pt = endpoint(l_knee_pt[0], l_knee_pt[1], pose.l_hip + pose.l_knee + lean*0.3, SH_LEN)
    _curved_limb(l_hip_j, l_knee_pt, l_ankle_pt, BLACK, LIMB_W)

    # Head
    neck_end_x = sh_cx + NECK_LEN * math.sin(d2r(pose.head_tilt + lean))
    neck_end_y = sh_cy - NECK_LEN
    _line(draw, (sh_cx, sh_cy), (neck_end_x, neck_end_y), BLACK, LIMB_W)

    hcx = neck_end_x + HEAD_R * math.sin(d2r(pose.head_tilt * 0.5))
    hcy = neck_end_y - HEAD_R + HEAD_R * math.sin(d2r(pose.head_nod)) * 0.2

    draw.ellipse([(hcx-HEAD_R, hcy-HEAD_R), (hcx+HEAD_R, hcy+HEAD_R)],
                 fill=WHITE, outline=BLACK, width=max(2, int(7*s)))
    _draw_cap(draw, img, hcx, hcy, HEAD_R, pose, s)
    _draw_face(draw, img, hcx, hcy, HEAD_R, pose, s)

    out = img.resize((W, H), Image.LANCZOS)
    return out


def _draw_face(draw, img, hcx, hcy, HR, pose, s=1.0):
    BLACK = (0,0,0,255)
    eo    = HR * 0.32
    eye_y = hcy - HR * 0.12

    brow_y = eye_y - HR * 0.35
    brow_w = HR * 0.27
    blift  = pose.eyebrow * HR * 0.1
    for side in [-1, 1]:
        bx = hcx + side * eo
        if pose.eyebrow < -0.3:
            draw.line([(bx - brow_w*side*0.4, brow_y - blift + HR*0.08*side),
                       (bx + brow_w*side*0.4, brow_y - blift)],
                      fill=BLACK, width=max(2,int(4*s)))
        else:
            draw.line([(bx-brow_w, brow_y-blift), (bx+brow_w, brow_y-blift)],
                      fill=BLACK, width=max(2,int(4*s)))

    eye_r  = HR * 0.13
    look   = pose.eye_look * HR * 0.07
    blink_h = eye_r * (1.0 - pose.blink)
    for side in [-1, 1]:
        ex = hcx + side * eo + look
        if blink_h < 1:
            draw.line([(ex-eye_r, eye_y), (ex+eye_r, eye_y)],
                      fill=BLACK, width=max(2,int(3*s)))
        else:
            draw.ellipse([(ex-eye_r, eye_y-blink_h), (ex+eye_r, eye_y+blink_h)],
                         fill=BLACK)

    my = hcy + HR * 0.33
    mw = HR * 0.5
    e  = pose.expression
    lw = max(2, int(3*s))
    if e == "smile":
        draw.arc([(hcx-mw, my-mw*0.4), (hcx+mw, my+mw*0.4)], 0, 180, fill=BLACK, width=lw)
    elif e == "big_smile":
        draw.arc([(hcx-mw*1.1, my-mw*0.6), (hcx+mw*1.1, my+mw*0.6)], 0, 180, fill=BLACK, width=lw+1)
    elif e == "neutral":
        draw.line([(hcx-mw*0.55, my), (hcx+mw*0.55, my)], fill=BLACK, width=lw)
    elif e == "open":
        mh = HR * 0.17
        draw.ellipse([(hcx-mw*0.5, my-mh), (hcx+mw*0.5, my+mh)], fill=BLACK)
    elif e == "surprised":
        mh = HR * 0.22
        draw.ellipse([(hcx-mw*0.45, my-mh), (hcx+mw*0.45, my+mh)], outline=BLACK, width=lw)
    elif e == "sad":
        draw.arc([(hcx-mw, my-mw*0.4), (hcx+mw, my+mw*0.4)], 180, 360, fill=BLACK, width=lw)
    elif e == "thinking":
        draw.line([(hcx-mw*0.2, my), (hcx+mw*0.6, my-mw*0.18)], fill=BLACK, width=lw)
    elif e == "smirk":
        draw.arc([(hcx, my-mw*0.3), (hcx+mw, my+mw*0.3)], 0, 180, fill=BLACK, width=lw)

    # Beard & Hair — History Channel presenter
    # Rule: face stays 100% clear, beard hangs BELOW chin only
    if pose.beard:
        from PIL import ImageFilter

        def _bez(p0, p1, p2, n=20):
            pts = []
            for i in range(n + 1):
                t = i / n; mt = 1 - t
                pts.append((mt*mt*p0[0]+2*mt*t*p1[0]+t*t*p2[0],
                             mt*mt*p0[1]+2*mt*t*p1[1]+t*t*p2[1]))
            return pts

        beard_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(beard_layer)
        INK = (0, 0, 0, 255)

        # 1. Hair tufts — 3 short separated curves at top of head
        htop = hcy - HR * 0.95
        for ox in [-0.28, 0.0, 0.28]:
            bx = hcx + HR * ox
            bd.arc([(bx - HR*0.13, htop - HR*0.20),
                    (bx + HR*0.13, htop + HR*0.04)],
                   200, 340, fill=INK, width=max(3, int(4*s)))

        # 2. Mustache — thin neat arch just above the mouth, doesn't touch it
        mu_top = my - HR * 0.24
        bd.arc([(hcx - HR*0.42, mu_top),
                (hcx + HR*0.42, mu_top + HR*0.22)],
               200, 340, fill=INK, width=max(3, int(5*s)))

        # 3. Beard — hangs BELOW chin, face stays clear
        # Chin attach: bottom of head circle
        chin_y  = hcy + HR * 0.88          # where beard meets the head outline
        chin_lx = hcx - HR * 0.22          # left attach
        chin_rx = hcx + HR * 0.22          # right attach
        tip     = (hcx, hcy + HR * 2.10)   # long pointed tip below chin

        left_curve  = _bez((chin_lx, chin_y), (hcx - HR*0.55, hcy + HR*1.40), tip)
        right_curve = _bez((chin_rx, chin_y), (hcx + HR*0.55, hcy + HR*1.40), tip)
        top_line    = [(chin_lx, chin_y), (hcx, chin_y - HR*0.05), (chin_rx, chin_y)]

        poly = top_line + right_curve[::-1][1:] + left_curve[::-1][1:]
        bd.polygon(poly, fill=INK)

        # Soft edges only
        beard_layer = beard_layer.filter(ImageFilter.GaussianBlur(radius=max(1, int(2*s))))
        img.alpha_composite(beard_layer)


# ─────────────────────────────────────────────────────────────────────────────
# KEYFRAME SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Keyframe:
    frames: int
    pose:   Pose
    easing: bool = True


def bake_keyframes(keyframes: List[Keyframe], loop: int = 1) -> List[Pose]:
    kf = keyframes * loop
    result = []
    for i in range(len(kf)):
        a = kf[i]
        b = kf[(i+1) % len(kf)]
        for f in range(a.frames):
            t = f / max(a.frames - 1, 1)
            result.append(interp_pose(a.pose, b.pose, t, a.easing))
    return result


def render_animation(keyframes: List[Keyframe], loop=1, bg_color=(0,0,0,0)) -> List[Image.Image]:
    return [render_pose(p, bg_color) for p in bake_keyframes(keyframes, loop)]


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATION PRESETS  (all angles: 0=down, +=right/clockwise, -=left/counter-cw)
# ─────────────────────────────────────────────────────────────────────────────
def _p(cx=540, cy=1380, s=1.0, **kw) -> Pose:
    return Pose(cx=cx, cy=cy, scale=s, **kw)


def anim_idle(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-28, r_shoulder=28, l_elbow=-20, r_elbow=20,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [Keyframe(18, Pose(**b, bob=0)), Keyframe(18, Pose(**b, bob=-7))]


def anim_walk(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", torso_lean=3)
    return [
        Keyframe(8, Pose(**b, l_hip=-28, l_knee=-10, l_ankle=-5, r_hip=24, r_knee=25, r_ankle=10,
                          l_shoulder=22, l_elbow=18, r_shoulder=-28, r_elbow=-18, bob=-5, head_nod=2)),
        Keyframe(7, Pose(**b, l_hip=-12, l_knee=-5, l_ankle=0, r_hip=12, r_knee=10, r_ankle=5,
                          l_shoulder=-12, l_elbow=-20, r_shoulder=12, r_elbow=20, bob=0, head_nod=0)),
        Keyframe(8, Pose(**b, l_hip=24, l_knee=25, l_ankle=10, r_hip=-28, r_knee=-10, r_ankle=-5,
                          l_shoulder=-28, l_elbow=-18, r_shoulder=22, r_elbow=18, bob=-5, head_nod=2)),
        Keyframe(7, Pose(**b, l_hip=12, l_knee=10, l_ankle=5, r_hip=-12, r_knee=-5, r_ankle=0,
                          l_shoulder=12, l_elbow=20, r_shoulder=-12, r_elbow=-20, bob=0, head_nod=0)),
    ]


def anim_run(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", torso_lean=15)
    return [
        Keyframe(5, Pose(**b, l_hip=-40, l_knee=-12, l_ankle=-8, r_hip=35, r_knee=45, r_ankle=15,
                          l_shoulder=40, l_elbow=45, r_shoulder=-45, r_elbow=-45, bob=-15)),
        Keyframe(5, Pose(**b, l_hip=35, l_knee=45, l_ankle=15, r_hip=-40, r_knee=-12, r_ankle=-8,
                          l_shoulder=-45, l_elbow=-45, r_shoulder=40, r_elbow=45, bob=-15)),
    ]


def anim_walk_fast(cx=540, cy=1380, s=1.0):
    """Faster walk cycle — 4+3 frames (half the normal speed)."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", torso_lean=4)
    return [
        Keyframe(4, Pose(**b, l_hip=-28, l_knee=-10, l_ankle=-5, r_hip=24, r_knee=25, r_ankle=10,
                          l_shoulder=22, l_elbow=18, r_shoulder=-28, r_elbow=-18, bob=-6, head_nod=2)),
        Keyframe(3, Pose(**b, l_hip=-10, l_knee=-4, l_ankle=0, r_hip=10, r_knee=8, r_ankle=3,
                          l_shoulder=-10, l_elbow=-16, r_shoulder=10, r_elbow=16, bob=0)),
        Keyframe(4, Pose(**b, l_hip=24, l_knee=25, l_ankle=10, r_hip=-28, r_knee=-10, r_ankle=-5,
                          l_shoulder=-28, l_elbow=-18, r_shoulder=22, r_elbow=18, bob=-6, head_nod=2)),
        Keyframe(3, Pose(**b, l_hip=10, l_knee=8, l_ankle=3, r_hip=-10, r_knee=-4, r_ankle=0,
                          l_shoulder=10, l_elbow=16, r_shoulder=-10, r_elbow=-16, bob=0)),
    ]


def anim_wave(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile",
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, r_shoulder=75, r_elbow=35)),
        Keyframe(10, Pose(**b, r_shoulder=80, r_elbow=65)),
        Keyframe(10, Pose(**b, r_shoulder=75, r_elbow=25)),
        Keyframe(10, Pose(**b, r_shoulder=80, r_elbow=60)),
    ]


def anim_point(cx=540, cy=1380, s=1.0):
    """Point right (at something to the right of screen)."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral",
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8,  Pose(**b, r_shoulder=28, r_elbow=20)),
        Keyframe(10, Pose(**b, r_shoulder=85, r_elbow=5, torso_lean=5)),
        Keyframe(15, Pose(**b, r_shoulder=85, r_elbow=5, torso_lean=5)),
        Keyframe(8,  Pose(**b, r_shoulder=28, r_elbow=20)),
    ]


def anim_point_left(cx=540, cy=1380, s=1.0):
    """Point left."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral",
             r_shoulder=28, r_elbow=20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8,  Pose(**b, l_shoulder=-28, l_elbow=-20)),
        Keyframe(10, Pose(**b, l_shoulder=-85, l_elbow=-5, torso_lean=-5)),
        Keyframe(15, Pose(**b, l_shoulder=-85, l_elbow=-5, torso_lean=-5)),
        Keyframe(8,  Pose(**b, l_shoulder=-28, l_elbow=-20)),
    ]


def anim_point_up(cx=540, cy=1380, s=1.0):
    """Point upward — emphasize something above."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", eyebrow=0.5,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8,  Pose(**b, r_shoulder=10, r_elbow=15)),
        Keyframe(10, Pose(**b, r_shoulder=-75, r_elbow=-10, torso_lean=-5, head_nod=-10)),
        Keyframe(15, Pose(**b, r_shoulder=-75, r_elbow=-10, torso_lean=-5, head_nod=-10)),
        Keyframe(8,  Pose(**b, r_shoulder=10, r_elbow=15)),
    ]


def anim_open_arms(cx=540, cy=1380, s=1.0):
    """Open arms wide — welcoming or showing something big."""
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile",
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, l_shoulder=-20, r_shoulder=20, l_elbow=-25, r_elbow=25)),
        Keyframe(12, Pose(**b, l_shoulder=-75, r_shoulder=75, l_elbow=-30, r_elbow=30)),
        Keyframe(14, Pose(**b, l_shoulder=-75, r_shoulder=75, l_elbow=-30, r_elbow=30)),
        Keyframe(10, Pose(**b, l_shoulder=-20, r_shoulder=20, l_elbow=-25, r_elbow=25)),
    ]


def anim_explain_two_hands(cx=540, cy=1380, s=1.0):
    """Compare two ideas with both hands alternating."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral",
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, l_shoulder=-50, l_elbow=-60, r_shoulder=20, r_elbow=25,
                          head_tilt=-8, eye_look=-0.5)),
        Keyframe(10, Pose(**b, l_shoulder=-20, l_elbow=-25, r_shoulder=50, r_elbow=60,
                          head_tilt=8, eye_look=0.5)),
        Keyframe(10, Pose(**b, l_shoulder=-50, l_elbow=-60, r_shoulder=20, r_elbow=25,
                          head_tilt=-8, eye_look=-0.5)),
        Keyframe(10, Pose(**b, l_shoulder=-20, l_elbow=-25, r_shoulder=50, r_elbow=60,
                          head_tilt=8, eye_look=0.5)),
    ]


def anim_count_fingers(cx=540, cy=1380, s=1.0):
    """Raise right hand and count — 1, 2, 3."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral",
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8,  Pose(**b, r_shoulder=-55, r_elbow=-10, head_nod=5)),
        Keyframe(8,  Pose(**b, r_shoulder=-62, r_elbow=-25, head_nod=5)),
        Keyframe(8,  Pose(**b, r_shoulder=-58, r_elbow=-15, head_nod=3)),
        Keyframe(8,  Pose(**b, r_shoulder=-65, r_elbow=-30, head_nod=5)),
        Keyframe(8,  Pose(**b, r_shoulder=-60, r_elbow=-20, head_nod=4)),
        Keyframe(8,  Pose(**b, r_shoulder=-70, r_elbow=-35, head_nod=5)),
    ]


def anim_lean_forward(cx=540, cy=1380, s=1.0):
    """Lean toward viewer — curiosity or emphasis."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", eyebrow=0.7,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, torso_lean=0, l_shoulder=-28, r_shoulder=28,
                          l_elbow=-20, r_elbow=20, head_nod=0)),
        Keyframe(14, Pose(**b, torso_lean=12, l_shoulder=-35, r_shoulder=40,
                          l_elbow=-25, r_elbow=15, head_nod=8, bob=-5)),
        Keyframe(14, Pose(**b, torso_lean=12, l_shoulder=-35, r_shoulder=40,
                          l_elbow=-25, r_elbow=15, head_nod=8, bob=-5)),
        Keyframe(12, Pose(**b, torso_lean=0, l_shoulder=-28, r_shoulder=28,
                          l_elbow=-20, r_elbow=20, head_nod=0)),
    ]


def anim_shrug(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="thinking",
             head_tilt=12, eyebrow=0.9, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, l_shoulder=-28, r_shoulder=28, l_elbow=-20, r_elbow=20)),
        Keyframe(12, Pose(**b, l_shoulder=-68, r_shoulder=68, l_elbow=-65, r_elbow=65, bob=-10)),
        Keyframe(14, Pose(**b, l_shoulder=-68, r_shoulder=68, l_elbow=-65, r_elbow=65, bob=-10)),
        Keyframe(10, Pose(**b, l_shoulder=-28, r_shoulder=28, l_elbow=-20, r_elbow=20)),
    ]


def anim_clap(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile",
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(7, Pose(**b, l_shoulder=-55, r_shoulder=55, l_elbow=65, r_elbow=-65)),
        Keyframe(7, Pose(**b, l_shoulder=-25, r_shoulder=25, l_elbow=85, r_elbow=-85)),
        Keyframe(7, Pose(**b, l_shoulder=-55, r_shoulder=55, l_elbow=65, r_elbow=-65)),
        Keyframe(7, Pose(**b, l_shoulder=-25, r_shoulder=25, l_elbow=85, r_elbow=-85)),
    ]


def anim_celebrate(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile")
    return [
        Keyframe(8, Pose(**b, l_shoulder=-85, r_shoulder=85, l_elbow=-30, r_elbow=30,
                          bob=-12, l_hip=-15, r_hip=15, l_knee=-12, r_knee=12)),
        Keyframe(8, Pose(**b, l_shoulder=-75, r_shoulder=75, l_elbow=-55, r_elbow=55,
                          bob=-5, l_hip=-10, r_hip=10, l_knee=-8, r_knee=8)),
        Keyframe(8, Pose(**b, l_shoulder=-90, r_shoulder=90, l_elbow=-20, r_elbow=20,
                          bob=-18, l_hip=-15, r_hip=15, l_knee=-12, r_knee=12)),
        Keyframe(8, Pose(**b, l_shoulder=-75, r_shoulder=75, l_elbow=-55, r_elbow=55,
                          bob=-5, l_hip=-10, r_hip=10, l_knee=-8, r_knee=8)),
    ]


def anim_talk(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, l_shoulder=-32, l_elbow=-22,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(5, Pose(**b, r_shoulder=28, r_elbow=20, expression="neutral", head_nod=0)),
        Keyframe(5, Pose(**b, r_shoulder=28, r_elbow=20, expression="open",    head_nod=6)),
        Keyframe(5, Pose(**b, r_shoulder=28, r_elbow=20, expression="neutral", head_nod=0)),
        Keyframe(5, Pose(**b, r_shoulder=28, r_elbow=20, expression="open",    head_nod=9)),
        Keyframe(5, Pose(**b, r_shoulder=42, r_elbow=25, expression="smile",   head_nod=4)),
        Keyframe(5, Pose(**b, r_shoulder=28, r_elbow=20, expression="open",    head_nod=6)),
    ]


def anim_talk_energetic(cx=540, cy=1380, s=1.0):
    """Animated two-hand talking — energetic explanation."""
    b = dict(cx=cx, cy=cy, scale=s, expression="open",
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(6, Pose(**b, l_shoulder=-45, l_elbow=-50, r_shoulder=40, r_elbow=30, head_nod=5)),
        Keyframe(6, Pose(**b, l_shoulder=-30, l_elbow=-30, r_shoulder=55, r_elbow=45, head_nod=8)),
        Keyframe(6, Pose(**b, l_shoulder=-55, l_elbow=-60, r_shoulder=30, r_elbow=20, head_nod=4)),
        Keyframe(6, Pose(**b, l_shoulder=-35, l_elbow=-40, r_shoulder=48, r_elbow=35, head_nod=7)),
    ]


def anim_think(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="thinking",
             head_tilt=-15, head_nod=12, eyebrow=0.6,
             l_shoulder=-28, l_elbow=-20,
             r_shoulder=48, r_elbow=-82,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(20, Pose(**b, eye_look=-0.6)),
        Keyframe(20, Pose(**b, eye_look=0.6)),
    ]


def anim_surprise(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="surprised", eyebrow=1.0)
    return [
        Keyframe(5,  Pose(**b, bob=0,   l_shoulder=-28, r_shoulder=28, l_hip=-12, r_hip=12)),
        Keyframe(7,  Pose(**b, bob=-22, l_shoulder=-65, r_shoulder=65, l_elbow=-32, r_elbow=32,
                          l_hip=-15, r_hip=15)),
        Keyframe(18, Pose(**b, bob=-18, l_shoulder=-60, r_shoulder=60, l_elbow=-28, r_elbow=28,
                          l_hip=-15, r_hip=15)),
        Keyframe(8,  Pose(**b, bob=0,   l_shoulder=-28, r_shoulder=28, l_hip=-12, r_hip=12)),
    ]


def anim_sad(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="sad",
             head_nod=22, eyebrow=-0.6, torso_lean=8,
             l_shoulder=-18, r_shoulder=18, l_elbow=-12, r_elbow=12,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [Keyframe(20, Pose(**b, bob=0)), Keyframe(20, Pose(**b, bob=-4))]


def anim_nod(cx=540, cy=1380, s=1.0):
    """Confident nod — agreement."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-28, r_shoulder=28, l_elbow=-20, r_elbow=20,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8, Pose(**b, head_nod=0)),
        Keyframe(6, Pose(**b, head_nod=18)),
        Keyframe(8, Pose(**b, head_nod=0)),
        Keyframe(6, Pose(**b, head_nod=15)),
        Keyframe(8, Pose(**b, head_nod=0)),
    ]


def anim_blink(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-28, r_shoulder=28, l_elbow=-20, r_elbow=20,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(28, Pose(**b, blink=0.0)),
        Keyframe(3,  Pose(**b, blink=1.0)),
        Keyframe(3,  Pose(**b, blink=0.0)),
    ]


def anim_crossed_arms(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral",
             l_shoulder=-48, r_shoulder=48, l_elbow=85, r_elbow=-85,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [Keyframe(18, Pose(**b, bob=0)), Keyframe(18, Pose(**b, bob=-4))]


def anim_hands_hips(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-58, r_shoulder=58, l_elbow=-82, r_elbow=82,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [Keyframe(18, Pose(**b, bob=0)), Keyframe(18, Pose(**b, bob=-6))]


def anim_confident_stance(cx=540, cy=1380, s=1.0):
    """Confident presenter — chest out, direct gaze."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-35, r_shoulder=38, l_elbow=-28, r_elbow=22,
             l_hip=-15, r_hip=15, l_knee=-7, r_knee=7, torso_lean=-3)
    return [
        Keyframe(20, Pose(**b, bob=0, head_nod=-3)),
        Keyframe(20, Pose(**b, bob=-5, head_nod=2)),
    ]


def anim_palm_up(cx=540, cy=1380, s=1.0):
    """Present idea palm-up — offering a concept."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, r_shoulder=32, r_elbow=-45)),
        Keyframe(12, Pose(**b, r_shoulder=40, r_elbow=-60, head_nod=5)),
        Keyframe(12, Pose(**b, r_shoulder=36, r_elbow=-50, head_nod=3)),
        Keyframe(10, Pose(**b, r_shoulder=32, r_elbow=-45)),
    ]


def anim_frustrated(cx=540, cy=1380, s=1.0):
    b = dict(cx=cx, cy=cy, scale=s, expression="sad", eyebrow=-0.8,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, l_shoulder=-55, r_shoulder=55, l_elbow=70, r_elbow=-70,
                          head_nod=8, head_tilt=-5)),
        Keyframe(10, Pose(**b, l_shoulder=-50, r_shoulder=50, l_elbow=60, r_elbow=-60,
                          head_nod=12, head_tilt=5)),
        Keyframe(10, Pose(**b, l_shoulder=-55, r_shoulder=55, l_elbow=70, r_elbow=-70,
                          head_nod=8, head_tilt=-5)),
        Keyframe(10, Pose(**b, l_shoulder=-50, r_shoulder=50, l_elbow=60, r_elbow=-60,
                          head_nod=12, head_tilt=5)),
    ]


def anim_facepalm(cx=540, cy=1380, s=1.0):
    """Facepalm — hand on forehead in disbelief."""
    b = dict(cx=cx, cy=cy, scale=s, expression="sad", head_tilt=8, head_nod=15, eyebrow=-0.9,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, r_shoulder=65, r_elbow=-125, torso_lean=5)),
        Keyframe(12, Pose(**b, r_shoulder=70, r_elbow=-130, torso_lean=8)),
    ]


def anim_mind_blown(cx=540, cy=1380, s=1.0):
    """Mind blown — hands exploding out from head."""
    b = dict(cx=cx, cy=cy, scale=s, expression="surprised", eyebrow=1.0,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8,  Pose(**b, l_shoulder=-60, r_shoulder=60, l_elbow=-90, r_elbow=90, head_nod=-5)),
        Keyframe(10, Pose(**b, l_shoulder=-88, r_shoulder=88, l_elbow=-20, r_elbow=20, head_nod=-15, bob=-10)),
        Keyframe(12, Pose(**b, l_shoulder=-95, r_shoulder=95, l_elbow=-10, r_elbow=10, head_nod=-12, bob=-5)),
    ]


def anim_whisper(cx=540, cy=1380, s=1.0):
    """Whisper secret — leaning in with hand near mouth."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smirk", torso_lean=12, head_tilt=-10,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, r_shoulder=55, r_elbow=-110, eye_look=0.8)),
        Keyframe(12, Pose(**b, r_shoulder=60, r_elbow=-115, eye_look=0.8)),
    ]


def anim_angry(cx=540, cy=1380, s=1.0):
    """Angry stance — fists up, torso forward."""
    b = dict(cx=cx, cy=cy, scale=s, expression="sad", eyebrow=-1.0, torso_lean=6,
             l_hip=-15, r_hip=15, l_knee=-10, r_knee=10)
    return [
        Keyframe(8, Pose(**b, l_shoulder=-48, r_shoulder=48, l_elbow=-75, r_elbow=75, bob=-4)),
        Keyframe(8, Pose(**b, l_shoulder=-52, r_shoulder=52, l_elbow=-80, r_elbow=80, bob=-8)),
    ]


def anim_writing_board(cx=540, cy=1380, s=1.0):
    """Writing / drawing on air board."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral",
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8, Pose(**b, r_shoulder=75, r_elbow=40, head_tilt=5)),
        Keyframe(8, Pose(**b, r_shoulder=85, r_elbow=20, head_tilt=-5)),
        Keyframe(8, Pose(**b, r_shoulder=65, r_elbow=50, head_tilt=5)),
    ]


def anim_flexing(cx=540, cy=1380, s=1.0):
    """Bicep flex — strength pose."""
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile", torso_lean=-4,
             l_hip=-18, r_hip=18, l_knee=-8, r_knee=8)
    return [
        Keyframe(10, Pose(**b, l_shoulder=-75, r_shoulder=75, l_elbow=-130, r_elbow=130, bob=-6)),
        Keyframe(10, Pose(**b, l_shoulder=-80, r_shoulder=80, l_elbow=-135, r_elbow=135, bob=-10)),
    ]


def anim_salute(cx=540, cy=1380, s=1.0):
    """Military salute."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile", torso_lean=-2,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, r_shoulder=75, r_elbow=-135, head_nod=-4)),
        Keyframe(15, Pose(**b, r_shoulder=75, r_elbow=-135, head_nod=-4)),
    ]


def anim_detective_magnify(cx=540, cy=1380, s=1.0):
    """Inspecting closely — detective pose."""
    b = dict(cx=cx, cy=cy, scale=s, expression="thinking", torso_lean=16, eyebrow=0.8,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, r_shoulder=65, r_elbow=-75, head_nod=12, eye_look=0.7)),
        Keyframe(12, Pose(**b, r_shoulder=70, r_elbow=-80, head_nod=15, eye_look=0.7)),
    ]


def anim_money_rain(cx=540, cy=1380, s=1.0):
    """Catching falling money / rain."""
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile", head_nod=-15,
             l_hip=-15, r_hip=15, l_knee=-8, r_knee=8)
    return [
        Keyframe(10, Pose(**b, l_shoulder=-80, r_shoulder=80, l_elbow=-40, r_elbow=40, bob=-10)),
        Keyframe(10, Pose(**b, l_shoulder=-85, r_shoulder=85, l_elbow=-25, r_elbow=25, bob=-5)),
    ]


def anim_scared_shield(cx=540, cy=1380, s=1.0):
    """Scared / shielding face."""
    b = dict(cx=cx, cy=cy, scale=s, expression="surprised", torso_lean=-12, eyebrow=-0.8,
             l_hip=-15, r_hip=15, l_knee=-18, r_knee=18)
    return [
        Keyframe(8, Pose(**b, l_shoulder=-60, r_shoulder=60, l_elbow=80, r_elbow=-80, bob=-20)),
        Keyframe(8, Pose(**b, l_shoulder=-65, r_shoulder=65, l_elbow=85, r_elbow=-85, bob=-25)),
    ]


def anim_sleeping_droop(cx=540, cy=1380, s=1.0):
    """Drowsy / sleeping stance."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", blink=1.0, head_nod=25, torso_lean=8,
             l_shoulder=-18, r_shoulder=18, l_elbow=-10, r_elbow=10,
             l_hip=-10, r_hip=10, l_knee=-5, r_knee=5)
    return [
        Keyframe(20, Pose(**b, bob=0)),
        Keyframe(20, Pose(**b, bob=-6)),
    ]


def anim_laughing_hysterically(cx=540, cy=1380, s=1.0):
    """Laughing hysterically holding stomach."""
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile", head_nod=18, torso_lean=10,
             l_hip=-15, r_hip=15, l_knee=-12, r_knee=12)
    return [
        Keyframe(6, Pose(**b, l_shoulder=-48, r_shoulder=48, l_elbow=75, r_elbow=-75, bob=-10)),
        Keyframe(6, Pose(**b, l_shoulder=-40, r_shoulder=40, l_elbow=65, r_elbow=-65, bob=-2)),
    ]


def anim_thumbs_up(cx=540, cy=1380, s=1.0):
    """Thumbs up pose."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, r_shoulder=65, r_elbow=-45, head_nod=4)),
        Keyframe(12, Pose(**b, r_shoulder=70, r_elbow=-50, head_nod=6)),
    ]


def anim_looking_far(cx=540, cy=1380, s=1.0):
    """Hand over eyes looking into the distance."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", torso_lean=6, eyebrow=0.6,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, r_shoulder=75, r_elbow=-125, eye_look=0.9)),
        Keyframe(12, Pose(**b, r_shoulder=78, r_elbow=-128, eye_look=0.9)),
    ]


def anim_reading_book(cx=540, cy=1380, s=1.0):
    """Holding and reading a book/tablet."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", head_nod=15,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, l_shoulder=-45, r_shoulder=45, l_elbow=55, r_elbow=-55, eye_look=0.3)),
        Keyframe(12, Pose(**b, l_shoulder=-48, r_shoulder=48, l_elbow=58, r_elbow=-58, eye_look=-0.3)),
    ]


def anim_mic_drop(cx=540, cy=1380, s=1.0):
    """Mic drop pose — extend arm and drop."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smirk", torso_lean=-4,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(8,  Pose(**b, r_shoulder=80, r_elbow=10)),
        Keyframe(10, Pose(**b, r_shoulder=60, r_elbow=40, head_nod=8)),
    ]


def anim_heart_hands(cx=540, cy=1380, s=1.0):
    """Forming heart hands at chest."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, l_shoulder=-40, r_shoulder=40, l_elbow=75, r_elbow=-75)),
        Keyframe(12, Pose(**b, l_shoulder=-42, r_shoulder=42, l_elbow=78, r_elbow=-78)),
    ]


def anim_stop_hand(cx=540, cy=1380, s=1.0):
    """Stop gesture — palm out."""
    b = dict(cx=cx, cy=cy, scale=s, expression="neutral", eyebrow=-0.5,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, r_shoulder=85, r_elbow=5, torso_lean=-4)),
        Keyframe(12, Pose(**b, r_shoulder=88, r_elbow=5, torso_lean=-4)),
    ]


def anim_bowing(cx=540, cy=1380, s=1.0):
    """Respectful bow forward."""
    b = dict(cx=cx, cy=cy, scale=s, expression="smile",
             l_shoulder=-20, r_shoulder=20, l_elbow=-15, r_elbow=15,
             l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(12, Pose(**b, torso_lean=28, head_nod=15, bob=-10)),
        Keyframe(12, Pose(**b, torso_lean=0, head_nod=0, bob=0)),
    ]


def anim_peace_sign(cx=540, cy=1380, s=1.0):
    """Peace / Victory V sign pose."""
    b = dict(cx=cx, cy=cy, scale=s, expression="big_smile", head_tilt=-6,
             l_shoulder=-28, l_elbow=-20, l_hip=-12, r_hip=12, l_knee=-5, r_knee=5)
    return [
        Keyframe(10, Pose(**b, r_shoulder=75, r_elbow=-65)),
        Keyframe(12, Pose(**b, r_shoulder=78, r_elbow=-70)),
    ]


# ── Registry ──────────────────────────────────────────────────────────────────
ANIMATIONS = {
    "idle":               anim_idle,
    "walk":               anim_walk,
    "run":                anim_run,
    "wave":               anim_wave,
    "point":              anim_point,
    "point_left":         anim_point_left,
    "point_up":           anim_point_up,
    "open_arms":          anim_open_arms,
    "explain_two_hands":  anim_explain_two_hands,
    "count_fingers":      anim_count_fingers,
    "lean_forward":       anim_lean_forward,
    "shrug":              anim_shrug,
    "clap":               anim_clap,
    "celebrate":          anim_celebrate,
    "talk":               anim_talk,
    "talk_energetic":     anim_talk_energetic,
    "think":              anim_think,
    "surprise":           anim_surprise,
    "sad":                anim_sad,
    "nod":                anim_nod,
    "blink":              anim_blink,
    "crossed_arms":       anim_crossed_arms,
    "hands_hips":         anim_hands_hips,
    "confident_stance":   anim_confident_stance,
    "palm_up":            anim_palm_up,
    "frustrated":         anim_frustrated,
    "facepalm":           anim_facepalm,
    "mind_blown":         anim_mind_blown,
    "whisper":            anim_whisper,
    "angry":              anim_angry,
    "writing_board":      anim_writing_board,
    "flexing":            anim_flexing,
    "salute":             anim_salute,
    "detective_magnify":  anim_detective_magnify,
    "money_rain":         anim_money_rain,
    "scared_shield":      anim_scared_shield,
    "sleeping_droop":     anim_sleeping_droop,
    "laughing_hysterically": anim_laughing_hysterically,
    "thumbs_up":          anim_thumbs_up,
    "looking_far":        anim_looking_far,
    "reading_book":       anim_reading_book,
    "mic_drop":           anim_mic_drop,
    "heart_hands":        anim_heart_hands,
    "stop_hand":          anim_stop_hand,
    "bowing":             anim_bowing,
    "peace_sign":         anim_peace_sign,
}


# ─────────────────────────────────────────────────────────────────────────────
# PRESENTER SEQUENCE BUILDER
# Builds a scene-length sequence:  walk-in → gesture → [walk mid] → gesture → walk-out
# ─────────────────────────────────────────────────────────────────────────────

# Keyword → mood mapping
_MOOD_MAP = {
    "exciting":    "energetic",   "amazing":  "energetic",  "wow":       "energetic",
    "incredible":  "energetic",   "shocking": "surprise",   "surprise":  "surprise",
    "mindblown":   "mind_blown",  "unbelievable": "mind_blown", "crazy":   "mind_blown",
    "unexpected":  "surprise",    "truth":    "serious",    "warning":   "serious",
    "important":   "serious",     "caution":  "serious",    "danger":    "serious",
    "stop":        "stop",        "halt":     "stop",       "never":     "stop",
    "sad":         "sad",         "loss":     "sad",        "fail":      "sad",
    "disaster":    "facepalm",    "mistake":  "facepalm",   "stupid":    "facepalm",
    "bad":         "sad",         "wrong":    "sad",        "problem":   "sad",
    "think":       "thinking",    "why":      "thinking",   "question":  "thinking",
    "secret":      "whisper",     "hidden":   "whisper",    "quiet":     "whisper",
    "angry":       "angry",       "mad":      "angry",      "furious":   "angry",
    "detective":   "investigate", "search":   "investigate","look":      "investigate",
    "how":         "thinking",    "wonder":   "thinking",   "mystery":   "thinking",
    "happy":       "positive",    "great":    "positive",   "good":      "positive",
    "success":     "positive",    "win":      "positive",   "profit":    "positive",
    "money":       "wealth",      "rich":     "wealth",     "cash":      "wealth",
    "strong":      "flex",        "power":    "flex",       "victory":   "flex",
    "compare":     "compare",     "versus":   "compare",    "vs":        "compare",
    "different":   "compare",     "both":     "compare",    "either":    "compare",
    "step":        "teaching",    "first":    "teaching",   "second":    "teaching",
    "third":       "teaching",    "next":     "teaching",   "finally":   "teaching",
    "remember":    "teaching",    "fact":     "teaching",   "write":     "teaching",
    "confused":    "confused",    "lost":     "confused",   "complex":   "confused",
    "love":        "heart",       "like":     "heart",      "favorite":  "heart",
    "thanks":      "respect",     "respect":  "respect",    "honesty":   "respect",
}

# Mood → gesture candidates (picked randomly for each scene)
# Note: 'celebrate', 'hands_hips', 'money_rain', 'open_arms' have been removed per user preference.
_MOOD_GESTURES = {
    "energetic": ["talk_energetic", "clap", "wave", "peace_sign", "mic_drop"],
    "surprise":  ["surprise", "mind_blown", "shrug", "point_up"],
    "mind_blown":["mind_blown", "surprise", "head_nod"],
    "serious":   ["point", "point_up", "confident_stance", "crossed_arms", "lean_forward", "stop_hand"],
    "stop":      ["stop_hand", "crossed_arms", "point"],
    "sad":       ["sad", "frustrated", "facepalm", "shrug", "crossed_arms"],
    "facepalm":  ["facepalm", "frustrated", "sad", "shrug"],
    "thinking":  ["think", "detective_magnify", "reading_book", "shrug", "lean_forward"],
    "whisper":   ["whisper", "think", "lean_forward"],
    "angry":     ["angry", "frustrated", "stop_hand"],
    "investigate":["detective_magnify", "looking_far", "think", "reading_book"],
    "positive":  ["nod", "thumbs_up", "palm_up", "confident_stance", "wave", "peace_sign"],
    "wealth":    ["thumbs_up", "palm_up", "confident_stance", "explain_two_hands"],
    "flex":      ["flexing", "thumbs_up", "peace_sign"],
    "compare":   ["explain_two_hands", "point_left", "point", "count_fingers"],
    "teaching":  ["count_fingers", "writing_board", "point_up", "explain_two_hands", "palm_up", "point"],
    "confused":  ["shrug", "facepalm", "think", "lean_forward"],
    "heart":     ["heart_hands", "thumbs_up", "smile"],
    "respect":   ["salute", "bowing", "nod", "thumbs_up"],
    "neutral":   ["talk", "nod", "thumbs_up", "palm_up", "confident_stance", "point", "point_left", "blink", "looking_far"],
}

# Walking positions
_WALK_ZONES = [300, 430, 540, 650, 780]  # cx values in stickman canvas (0–1080)

_EXCLUDED_GESTURES = {"celebrate", "hands_hips", "money_rain", "open_arms"}

def _pick_mood(text: str) -> str:
    words = text.lower().split()
    for w in words:
        w_clean = w.strip(".,!?:;\"'")
        if w_clean in _MOOD_MAP:
            return _MOOD_MAP[w_clean]
    return "neutral"


def _pick_gesture(mood: str, exclude: str = None) -> str:
    candidates = _MOOD_GESTURES.get(mood, _MOOD_GESTURES["neutral"])
    # Filter out excluded gestures
    valid_candidates = [c for c in candidates if c not in _EXCLUDED_GESTURES]
    if not valid_candidates:
        valid_candidates = [c for c in _MOOD_GESTURES["neutral"] if c not in _EXCLUDED_GESTURES]
    if exclude and len(valid_candidates) > 1:
        valid_candidates = [c for c in valid_candidates if c != exclude]
    return random.choice(valid_candidates)


def _apply_talking(poses: List[Pose]) -> List[Pose]:
    """Overlay talking mouth on baked poses — open/neutral every 8 frames."""
    for i, p in enumerate(poses):
        # Only override neutral-ish expressions so dramatic emotions are preserved
        if p.expression in ("neutral", "smile", "smirk"):
            p.expression = "open" if (i % 10) < 5 else "neutral"
    return poses


def build_presenter_sequence(
    narration: str,
    total_frames: int,
    scene_index: int = 0,
    cy: float = 1380.0,
    s: float = 1.0,
    bg_color=(0, 0, 0, 0),
    last_gesture: str = None,
    last_cx: float = None,
    beard: bool = False,
    cap: bool = False,
    cap_color: str = "green",
) -> List[Image.Image]:
    """
    Build a presenter animation for one scene.

    Structure:
      1. Fast walk-in (~10% of frames) — character arrives at position
      2. Stand + gesture (~90% of frames) — character presents with talking mouth
    """
    rng = random.Random(scene_index * 7 + 13)

    mood     = _pick_mood(narration)
    gesture  = _pick_gesture(mood, exclude=last_gesture)

    # Start position (where character was last scene)
    zones = _WALK_ZONES
    if last_cx is None:
        start_cx = zones[scene_index % len(zones)]
    else:
        start_cx = float(last_cx)

    # Pick a different end position (where character stands during this scene)
    end_options = [z for z in zones if abs(z - start_cx) > 80]
    end_cx = rng.choice(end_options) if end_options else rng.choice(zones)

    # Frame budget: brief walk-in, then all gesture
    f_walk = max(10, int(total_frames * 0.10))
    f_gest = total_frames - f_walk

    all_poses = []

    # 1. Fast walk from start_cx to end_cx
    walk_cycle = anim_walk_fast(cx=start_cx, cy=cy, s=s)
    cycle_len  = sum(k.frames for k in walk_cycle)
    walk_poses = bake_keyframes(walk_cycle, loop=max(1, f_walk // cycle_len + 1))[:f_walk]
    for i, p in enumerate(walk_poses):
        p.cx = lerp(start_cx, end_cx, ease(i / max(f_walk - 1, 1)))
        if beard: p.beard = True
        if cap: p.cap, p.cap_color = True, cap_color
    all_poses.extend(walk_poses)

    # 2. Gesture at end_cx with speaking mouth
    g_fn   = ANIMATIONS.get(gesture, anim_talk)
    g_kfs  = g_fn(cx=end_cx, cy=cy, s=s)
    g_len  = max(sum(k.frames for k in g_kfs), 1)
    g_poses = bake_keyframes(g_kfs, loop=max(1, f_gest // g_len + 1))[:f_gest]
    for p in g_poses:
        p.cx = end_cx
        if beard: p.beard = True
        if cap: p.cap, p.cap_color = True, cap_color
    _apply_talking(g_poses)
    all_poses.extend(g_poses)

    # Pad if needed
    while len(all_poses) < total_frames:
        p_last = all_poses[-1]
        if beard: p_last.beard = True
        if cap: p_last.cap, p_last.cap_color = True, cap_color
        all_poses.append(p_last)

    frames = [render_pose(p, bg_color) for p in all_poses[:total_frames]]
    return frames, gesture, end_cx


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API (unchanged signatures for backward compat)
# ─────────────────────────────────────────────────────────────────────────────
def get_animation_frames(name: str, loops=1, cx=540, cy=1380, s=1.0,
                         bg_color=(0,0,0,0), cap=False, cap_color="green") -> List[Image.Image]:
    fn = ANIMATIONS.get(name)
    if not fn:
        raise ValueError(f"Unknown animation '{name}'. Available: {list(ANIMATIONS)}")
    poses = bake_keyframes(fn(cx=cx, cy=cy, s=s), loop=loops)
    if cap:
        for p in poses:
            p.cap, p.cap_color = True, cap_color
    return [render_pose(p, bg_color) for p in poses]


def get_moving_animation_frames(name: str, start_cx: float, end_cx: float,
                                 start_cy: float = 1380.0, end_cy: float = 1380.0,
                                 loops: int = 4, s: float = 1.0,
                                 bg_color=(0,0,0,0), cap=False, cap_color="green") -> List[Image.Image]:
    fn = ANIMATIONS.get(name)
    if not fn:
        raise ValueError(f"Unknown animation '{name}'. Available: {list(ANIMATIONS)}")
    kfs = fn(cx=start_cx, cy=start_cy, s=s)
    poses = bake_keyframes(kfs, loop=loops)
    n = len(poses)
    for i, p in enumerate(poses):
        t = i / max(n - 1, 1)
        p.cx = lerp(start_cx, end_cx, t)
        p.cy = lerp(start_cy, end_cy, t)
        if cap:
            p.cap, p.cap_color = True, cap_color
    return [render_pose(p, bg_color) for p in poses]


# ── FFmpeg export ─────────────────────────────────────────────────────────────
def frames_to_mp4(frames: List[Image.Image], out_path: str, fps: int = FPS) -> bool:
    import imageio_ffmpeg
    tmp = tempfile.mkdtemp()
    for i, img in enumerate(frames):
        img.convert("RGB").save(os.path.join(tmp, f"{i:06d}.png"))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-framerate", str(fps),
           "-i", os.path.join(tmp, "%06d.png"),
           "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-pix_fmt", "yuv420p", f"-vf", f"scale={W}:{H}", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        print("[FFmpeg ERROR]", r.stderr[-400:])
        return False
    return True
