import os
import math
import random
import shutil
from PIL import Image, ImageDraw
from scene_renderer import draw_background, HAIR_COL, BG_SKY, BG_GROUND, WHITE, BLACK

WIDTH, HEIGHT = 1280, 720
FPS = 24
DURATION_SEC = 3  # loop duration

def draw_stickman_animated(draw, cx, cy, scale=1.0,
                            pose="sad_sit", expression="sad",
                            frame=0, total_frames=72):
    """
    Draws a stickman with frame-by-frame animation offsets:
    - Breathing (torso/head bob)
    - Blinking
    - Hair micro-wobble
    """
    s = scale

    # ── Animation parameters ────────────────────────────────────────
    t = frame / total_frames  # 0.0 → 1.0 (loop progress)

    # Breathing: subtle sine wave offset for head and torso
    breathe_y = int(math.sin(t * 2 * math.pi) * 4 * s)

    # Blink: eyes shut for 3 frames every ~70 frames
    blink_cycle = frame % 70
    is_blinking = blink_cycle in (0, 1, 2)

    # Hair wobble: small random jitter on tips (deterministic per frame)
    hair_seed = frame * 7  # different per frame, same within a frame

    lw = max(3, int(6 * s))
    ow = max(3, int(5 * s))

    leg_len   = int(160 * s)
    torso_len = int(120 * s)
    arm_len   = int(90  * s)
    head_r    = int(65  * s)

    # ── Sitting pose ────────────────────────────────────────────────
    lf  = (int(cx - 130*s), cy)
    rf  = (int(cx + 130*s), cy)
    lk  = (int(cx - 70*s),  cy - int(leg_len*0.35))
    rk  = (int(cx + 70*s),  cy - int(leg_len*0.35))
    hip = (cx,               cy - int(leg_len*0.35))

    # Apply breathing offset to upper body only
    sh  = (cx,               hip[1] - torso_len + breathe_y)
    la  = (int(cx - 80*s),  hip[1] - int(torso_len*0.2) + breathe_y)
    ra  = (int(cx + 80*s),  hip[1] - int(torso_len*0.2) + breathe_y)
    hc  = (cx,               hip[1] - torso_len - head_r - int(5*s) + breathe_y)

    # Draw limbs
    draw.line([lf, lk, hip], fill=BLACK, width=lw, joint="curve")
    draw.line([rf, rk, hip], fill=BLACK, width=lw, joint="curve")
    draw.line([hip, sh],     fill=BLACK, width=lw)
    draw.line([sh, la],      fill=BLACK, width=lw)
    draw.line([sh, ra],      fill=BLACK, width=lw)

    # ── Head ────────────────────────────────────────────────────────
    draw.ellipse([hc[0]-head_r-ow, hc[1]-head_r-ow,
                  hc[0]+head_r+ow, hc[1]+head_r+ow], fill=BLACK)
    draw.ellipse([hc[0]-head_r, hc[1]-head_r,
                  hc[0]+head_r, hc[1]+head_r], fill=WHITE)

    # ── Hair wobble ─────────────────────────────────────────────────
    random.seed(hair_seed)
    num_strands = 22
    for i in range(num_strands):
        angle = math.pi + (i / (num_strands-1)) * math.pi
        base_x = hc[0] + int((head_r - 5) * math.cos(angle))
        base_y = hc[1] + int((head_r - 5) * math.sin(angle))
        # Wobble tip slightly per frame
        wobble_x = random.randint(-int(20*s), int(20*s))
        wobble_y = random.randint(-int(30*s), -int(10*s))
        tip_x = base_x + wobble_x
        tip_y = base_y + wobble_y
        draw.line([(base_x, base_y), (tip_x, tip_y)],
                  fill=HAIR_COL, width=max(2, int(4*s)))

    # ── Eyes (with blink) ───────────────────────────────────────────
    eye_r  = max(4, int(7*s))
    eye_ox = int(22*s)
    eye_oy = int(5*s)

    if is_blinking:
        # Draw closed eyes as thin horizontal lines
        draw.line([(hc[0]-eye_ox-eye_r, hc[1]+eye_oy),
                   (hc[0]-eye_ox+eye_r, hc[1]+eye_oy)],
                  fill=BLACK, width=max(2, int(4*s)))
        draw.line([(hc[0]+eye_ox-eye_r, hc[1]+eye_oy),
                   (hc[0]+eye_ox+eye_r, hc[1]+eye_oy)],
                  fill=BLACK, width=max(2, int(4*s)))
    else:
        draw.ellipse([hc[0]-eye_ox-eye_r, hc[1]+eye_oy-eye_r,
                      hc[0]-eye_ox+eye_r, hc[1]+eye_oy+eye_r], fill=BLACK)
        draw.ellipse([hc[0]+eye_ox-eye_r, hc[1]+eye_oy-eye_r,
                      hc[0]+eye_ox+eye_r, hc[1]+eye_oy+eye_r], fill=BLACK)

    # ── Sad eyebrows ────────────────────────────────────────────────
    brow_y = hc[1] + eye_oy - int(18*s)
    brow_w = int(20*s)
    brow_lw= max(2, int(4*s))
    draw.line([(hc[0]-eye_ox-brow_w//2, brow_y + int(4*s)),
               (hc[0]-eye_ox+brow_w//2, brow_y - int(4*s))],
              fill=BLACK, width=brow_lw)
    draw.line([(hc[0]+eye_ox-brow_w//2, brow_y - int(4*s)),
               (hc[0]+eye_ox+brow_w//2, brow_y + int(4*s))],
              fill=BLACK, width=brow_lw)

    # ── Frown ───────────────────────────────────────────────────────
    mouth_w  = int(28*s)
    mouth_y  = hc[1] + int(25*s)
    mouth_lw = max(2, int(4*s))
    draw.arc([hc[0]-mouth_w, mouth_y-int(14*s),
              hc[0]+mouth_w, mouth_y+int(14*s)],
             start=200, end=340, fill=BLACK, width=mouth_lw)


def draw_bones(draw, x, y, scale=1.0):
    """Draws a small pile of cartoon bones on the ground."""
    s = scale
    bh = int(12*s)
    col = (255, 255, 255)

    def bone(cx, cy, angle_deg=0, length=30):
        bw = int(length * s)
        r = math.radians(angle_deg)
        dx = int(bw * math.cos(r))
        dy = int(bw * math.sin(r))
        x1, y1 = cx - dx, cy - dy
        x2, y2 = cx + dx, cy + dy
        draw.line([(x1, y1), (x2, y2)], fill=col, width=bh)
        draw.line([(x1, y1), (x2, y2)], fill=BLACK, width=max(2, int(3*s)))
        er = bh // 2 + int(2*s)
        for px, py in [(x1, y1), (x2, y2)]:
            draw.ellipse([px-er-2, py-er-2, px+er+2, py+er+2], fill=BLACK)
            draw.ellipse([px-er+2, py-er+2, px+er-2, py+er-2], fill=col)

    bone(x,             y,          10, 32)
    bone(x + int(45*s), y - int(8*s), -15, 28)
    bone(x - int(28*s), y + int(5*s),  30, 22)


def render_animated_gif(output_gif_path):
    total_frames = FPS * DURATION_SEC  # 72 frames
    ground_y = int(HEIGHT * 0.78)
    frames = []

    print(f"Rendering {total_frames} frames...")
    for f in range(total_frames):
        img  = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
        draw = ImageDraw.Draw(img)

        draw_background(draw, sky=BG_SKY, ground=BG_GROUND, horizon=0.55)

        draw_stickman_animated(draw,
            cx=WIDTH//2 - 60, cy=ground_y,
            scale=1.25, pose="sad_sit", expression="sad",
            frame=f, total_frames=total_frames)

        draw_bones(draw, x=WIDTH//2 + 160, y=ground_y + 5, scale=1.1)

        # Convert to P mode for GIF
        frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))

        if (f+1) % 10 == 0:
            print(f"  Frame {f+1}/{total_frames}")

    # Save animated GIF (loop forever)
    frame_duration_ms = int(1000 / FPS)
    frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=frame_duration_ms,
        optimize=False
    )
    print(f"\nSaved animated GIF: {output_gif_path}")


if __name__ == "__main__":
    os.makedirs(r"C:\Users\ASUS\kokoro\images_test", exist_ok=True)
    local  = r"C:\Users\ASUS\kokoro\images_test\animated_stickman.gif"
    brain  = r"C:\Users\ASUS\.gemini\antigravity\brain\e8efb994-11f5-42d4-9b99-16f171d44f2c\animated_stickman.gif"
    render_animated_gif(local)
    shutil.copy(local, brain)
    print("Done.")
