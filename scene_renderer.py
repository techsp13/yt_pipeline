import os
import math
import random
from PIL import Image, ImageDraw, ImageFont

# ─── Canvas settings ───────────────────────────────────────────────
WIDTH, HEIGHT = 1280, 720

# ─── Color palette (matching reference exactly) ─────────────────────
BG_SKY      = (220, 140,  80)   # warm orange sky
BG_GROUND   = (230, 210, 160)   # sandy tan ground
BG_SPACE    = (20,  30,   50)   # dark space blue
BG_COLD     = (180, 210, 230)   # cold ice blue
BG_HOT      = (230, 100,  80)   # hot sun red
BG_GREEN    = (140, 190, 130)   # savannah green
BG_TEAL     = (90,  160, 160)   # medical teal
BG_DARK     = (50,  50,   55)   # dark gray

WHITE    = (255, 255, 255)
BLACK    = (20,  20,  20)
RED      = (220,  60,  60)
YELLOW   = (250, 210,  60)
BLUE     = (60,  120, 220)
GREEN    = (80,  170,  90)
HAIR_COL = (65,  35,  10)    # dark brown / near-black hair
WOOD_BROWN = (139, 69, 19)

def draw_background(draw, sky=BG_SKY, ground=BG_GROUND, horizon=0.55):
    """Draws a flat two-tone split background."""
    h_y = int(HEIGHT * horizon)
    draw.rectangle([0, 0, WIDTH, h_y], fill=sky)
    draw.rectangle([0, h_y, WIDTH, HEIGHT], fill=ground)
    draw.line([(0, h_y), (WIDTH, h_y)], fill=BLACK, width=3)

def draw_stickman(draw, cx, cy, scale=1.0,
                  pose="stand",       # stand | sit | sad_sit | point | shiver | point_head
                  expression="neutral",  # neutral | sad | happy | surprised
                  hand_up=False):
    """
    Draws a reference-accurate stickman.
    cx, cy = centre of the character's feet / ground contact point.
    """
    s = scale
    lw = max(3, int(6 * s))   # limb line width
    ow = max(3, int(5 * s))   # outline width

    leg_len   = int(160 * s)
    torso_len = int(120 * s)
    arm_len   = int(90  * s)
    head_r    = int(65  * s)

    # Base coordinates
    hip = (cx, cy - leg_len)
    sh = (cx, cy - leg_len - torso_len)
    hc = (cx, cy - leg_len - torso_len - head_r - int(5*s))

    # Pose logic
    if pose == "stand":
        lf = (int(cx - 28*s), cy)
        rf = (int(cx + 28*s), cy)
        draw.line([lf, hip], fill=BLACK, width=lw)
        draw.line([rf, hip], fill=BLACK, width=lw)
        draw.line([hip, sh], fill=BLACK, width=lw)
        
        la = (int(cx - arm_len), cy - leg_len - int(torso_len*0.6))
        ra = (int(cx + arm_len), cy - leg_len - int(torso_len*0.6))
        draw.line([sh, la], fill=BLACK, width=lw)
        draw.line([sh, ra], fill=BLACK, width=lw)

    elif pose == "point":
        lf = (int(cx - 28*s), cy)
        rf = (int(cx + 28*s), cy)
        draw.line([lf, hip], fill=BLACK, width=lw)
        draw.line([rf, hip], fill=BLACK, width=lw)
        draw.line([hip, sh], fill=BLACK, width=lw)
        
        la = (int(cx - arm_len), cy - leg_len - int(torso_len*0.6))
        # pointing up-right
        ra = (int(cx + arm_len * 0.8), cy - leg_len - torso_len - int(40*s))
        draw.line([sh, la], fill=BLACK, width=lw)
        draw.line([sh, ra], fill=BLACK, width=lw)

    elif pose == "point_head":
        lf = (int(cx - 28*s), cy)
        rf = (int(cx + 28*s), cy)
        draw.line([lf, hip], fill=BLACK, width=lw)
        draw.line([rf, hip], fill=BLACK, width=lw)
        draw.line([hip, sh], fill=BLACK, width=lw)
        
        la = (int(cx - arm_len), cy - leg_len - int(torso_len*0.6))
        # touching/pointing to own head
        ra_elbow = (int(cx + arm_len*0.5), cy - leg_len - torso_len)
        ra_hand = (int(hc[0] + head_r * 0.8), hc[1])
        draw.line([sh, ra_elbow, ra_hand], fill=BLACK, width=lw, joint="curve")
        draw.line([sh, la], fill=BLACK, width=lw)

    elif pose == "shiver":
        # Wobbly shivering legs and arms
        lf = (int(cx - 35*s), cy)
        rf = (int(cx + 35*s), cy)
        lk_wobble = (int(cx - 20*s + math.sin(cy)*10), cy - int(leg_len*0.5))
        rk_wobble = (int(cx + 20*s - math.sin(cy)*10), cy - int(leg_len*0.5))
        draw.line([lf, lk_wobble, hip], fill=BLACK, width=lw, joint="curve")
        draw.line([rf, rk_wobble, hip], fill=BLACK, width=lw, joint="curve")
        draw.line([hip, sh], fill=BLACK, width=lw)
        
        la = (int(cx - arm_len + 8*s), cy - leg_len - int(torso_len*0.4))
        ra = (int(cx + arm_len - 8*s), cy - leg_len - int(torso_len*0.4))
        draw.line([sh, la], fill=BLACK, width=lw)
        draw.line([sh, ra], fill=BLACK, width=lw)

    elif pose in ("sit", "sad_sit"):
        lf = (int(cx - 130*s), cy)
        rf = (int(cx + 130*s), cy)
        lk = (int(cx - 70*s),  cy - int(leg_len*0.35))
        rk = (int(cx + 70*s),  cy - int(leg_len*0.35))
        hip_sit = (cx, cy - int(leg_len*0.35))
        sh = (cx, cy - int(leg_len*0.35) - torso_len)
        hc = (cx, cy - int(leg_len*0.35) - torso_len - head_r - int(5*s))

        draw.line([lf, lk, hip_sit], fill=BLACK, width=lw, joint="curve")
        draw.line([rf, rk, hip_sit], fill=BLACK, width=lw, joint="curve")
        draw.line([hip_sit, sh], fill=BLACK, width=lw)

        if pose == "sad_sit":
            la = (int(cx - 80*s), cy - int(leg_len*0.2))
            ra = (int(cx + 80*s), cy - int(leg_len*0.2))
        else:
            la = (int(cx - arm_len), cy - int(leg_len*0.35) - int(torso_len*0.6))
            ra = (int(cx + arm_len), cy - int(leg_len*0.35) - int(torso_len*0.6))
        
        draw.line([sh, la], fill=BLACK, width=lw)
        draw.line([sh, ra], fill=BLACK, width=lw)

    # ── Head ────────────────────────────────────────────────────────
    draw.ellipse([hc[0]-head_r-ow, hc[1]-head_r-ow,
                  hc[0]+head_r+ow, hc[1]+head_r+ow], fill=BLACK)
    draw.ellipse([hc[0]-head_r, hc[1]-head_r,
                  hc[0]+head_r, hc[1]+head_r], fill=WHITE)

    # ── Hair ────────────────────────────────────────────────────────
    random.seed(42)
    num_strands = 22
    for i in range(num_strands):
        angle = math.pi + (i / (num_strands-1)) * math.pi
        base_x = hc[0] + int((head_r - 5) * math.cos(angle))
        base_y = hc[1] + int((head_r - 5) * math.sin(angle))
        tip_x = base_x + random.randint(-int(18*s), int(18*s))
        tip_y = base_y + random.randint(-int(28*s), -int(10*s))
        draw.line([(base_x, base_y), (tip_x, tip_y)], fill=HAIR_COL, width=max(2, int(4*s)))

    # ── Face ────────────────────────────────────────────────────────
    eye_r  = max(4, int(7*s))
    eye_ox = int(22*s)
    eye_oy = int(5*s)

    if expression == "surprised":
        draw.ellipse([hc[0]-eye_ox-eye_r*1.5, hc[1]+eye_oy-eye_r*1.5,
                      hc[0]-eye_ox+eye_r*1.5, hc[1]+eye_oy+eye_r*1.5], fill=BLACK)
        draw.ellipse([hc[0]+eye_ox-eye_r*1.5, hc[1]+eye_oy-eye_r*1.5,
                      hc[0]+eye_ox+eye_r*1.5, hc[1]+eye_oy+eye_r*1.5], fill=BLACK)
    else:
        draw.ellipse([hc[0]-eye_ox-eye_r, hc[1]+eye_oy-eye_r,
                      hc[0]-eye_ox+eye_r, hc[1]+eye_oy+eye_r], fill=BLACK)
        draw.ellipse([hc[0]+eye_ox-eye_r, hc[1]+eye_oy-eye_r,
                      hc[0]+eye_ox+eye_r, hc[1]+eye_oy+eye_r], fill=BLACK)

    # Eyebrows
    brow_y = hc[1] + eye_oy - int(18*s)
    brow_w = int(20*s)
    brow_lw= max(2, int(4*s))
    if expression == "sad":
        draw.line([(hc[0]-eye_ox-brow_w//2, brow_y + int(4*s)), (hc[0]-eye_ox+brow_w//2, brow_y - int(4*s))], fill=BLACK, width=brow_lw)
        draw.line([(hc[0]+eye_ox-brow_w//2, brow_y - int(4*s)), (hc[0]+eye_ox+brow_w//2, brow_y + int(4*s))], fill=BLACK, width=brow_lw)
    else:
        draw.line([(hc[0]-eye_ox-brow_w//2, brow_y), (hc[0]-eye_ox+brow_w//2, brow_y)], fill=BLACK, width=brow_lw)
        draw.line([(hc[0]+eye_ox-brow_w//2, brow_y), (hc[0]+eye_ox+brow_w//2, brow_y)], fill=BLACK, width=brow_lw)

    # Mouth
    mouth_w = int(28*s)
    mouth_y = hc[1] + int(25*s)
    mouth_lw= max(2, int(4*s))
    if expression == "sad":
        draw.arc([hc[0]-mouth_w, mouth_y-int(14*s), hc[0]+mouth_w, mouth_y+int(14*s)], start=200, end=340, fill=BLACK, width=mouth_lw)
    elif expression == "happy":
        draw.arc([hc[0]-mouth_w, mouth_y-int(14*s), hc[0]+mouth_w, mouth_y+int(14*s)], start=20, end=160, fill=BLACK, width=mouth_lw)
    elif expression == "surprised":
        draw.ellipse([hc[0]-int(12*s), mouth_y-int(8*s), hc[0]+int(12*s), mouth_y+int(12*s)], fill=BLACK)
    else:
        draw.line([(hc[0]-mouth_w//2, mouth_y), (hc[0]+mouth_w//2, mouth_y)], fill=BLACK, width=mouth_lw)

def draw_question_mark(draw, x, y, scale=1.0):
    """Draws a simple thick red question mark."""
    s = scale
    draw.arc([x-int(40*s), y-int(60*s), x+int(40*s), y], start=180, end=380, fill=RED, width=int(12*s))
    draw.line([(x+int(38*s), y-int(2*s)), (x, y+int(40*s))], fill=RED, width=int(12*s))
    draw.ellipse([x-int(6*s), y+int(60*s), x+int(6*s), y+int(72*s)], fill=RED)

def draw_dna(draw, x, y, length=400, scale=1.0):
    """Draws a vertical DNA double helix."""
    s = scale
    steps = 12
    amplitude = int(40 * s)
    wavelength = 80
    for i in range(steps):
        y1 = y + i * 30
        y2 = y1 + 15
        
        x1_a = x + int(math.sin(y1 / 20.0) * amplitude)
        x1_b = x - int(math.sin(y1 / 20.0) * amplitude)
        
        # Draw base pairs (horizontal bars)
        if i % 2 == 0:
            draw.line([(x1_a, y1), (x1_b, y1)], fill=BLACK, width=int(4*s))
            
        draw.ellipse([x1_a-5, y1-5, x1_a+5, y1+5], fill=BLUE)
        draw.ellipse([x1_b-5, y1-5, x1_b+5, y1+5], fill=RED)

def draw_animals(draw, x, y):
    """Draws simple stick/doodle style animals (Lion, Elephant, Giraffe)."""
    # 1. Giraffe (Right)
    draw.ellipse([x+200, y-100, x+280, y-50], fill=(240, 200, 80)) # Body
    draw.line([x+260, y-80, x+280, y-220], fill=BLACK, width=12) # Long neck
    draw.ellipse([x+270, y-230, x+300, y-210], fill=(240, 200, 80)) # Head
    for lx in [x+210, x+230, x+250, x+270]:
        draw.line([lx, y-60, lx, y+50], fill=BLACK, width=6) # Legs

    # 2. Elephant (Center)
    draw.ellipse([x-100, y-80, x+80, y+40], fill=(160, 170, 180)) # Large grey body
    draw.ellipse([x-150, y-100, x-80, y-30], fill=(160, 170, 180)) # Head
    draw.line([x-130, y-50, x-160, y+10], fill=BLACK, width=10) # Trunk
    for lx in [x-80, x-40, x, x+40]:
        draw.line([lx, y+20, lx, y+100], fill=BLACK, width=16) # Thick legs

    # 3. Lion (Left)
    draw.ellipse([x-250, y-50, x-180, y], fill=(210, 150, 70)) # Body
    # Mane (large circle behind face)
    draw.ellipse([x-280, y-100, x-220, y-40], fill=HAIR_COL)
    draw.ellipse([x-270, y-90, x-230, y-50], fill=(210, 150, 70)) # Head
    for lx in [x-245, x-230, x-205, x-190]:
        draw.line([lx, y-10, lx, y+60], fill=BLACK, width=5) # Legs

def draw_campfire(draw, x, y, scale=1.0):
    """Draws logs and a cartoon flame."""
    s = scale
    # Logs
    draw.line([(x-int(50*s), y+int(10*s)), (x+int(50*s), y-int(10*s))], fill=WOOD_BROWN, width=int(14*s))
    draw.line([(x+int(50*s), y+int(10*s)), (x-int(50*s), y-int(10*s))], fill=WOOD_BROWN, width=int(14*s))
    # Flame (layered triangles)
    draw.polygon([(x, y-int(70*s)), (x-int(30*s), y+int(10*s)), (x+int(30*s), y+int(10*s))], fill=RED)
    draw.polygon([(x, y-int(50*s)), (x-int(20*s), y+int(10*s)), (x+int(20*s), y+int(10*s))], fill=YELLOW)

def draw_honeycomb(draw, x, y, size=30):
    """Draws a small honeycomb grid."""
    for dy in [-size, 0, size]:
        for dx in [-size*1.5, 0, size*1.5]:
            px = x + dx
            py = y + dy + (size/2 if dx == 0 else 0)
            # Hexagon points
            points = []
            for i in range(6):
                angle = math.radians(i * 60)
                points.append((px + size*0.8 * math.cos(angle), py + size*0.8 * math.sin(angle)))
            draw.polygon(points, outline=BLACK, fill=YELLOW, width=3)

def draw_steak(draw, x, y):
    """Draws a cartoon plate and steak with steam."""
    # Plate
    draw.ellipse([x-100, y-20, x+100, y+40], fill=WHITE, outline=BLACK, width=4)
    # Steak
    draw.polygon([(x-60, y-5), (x-20, y-15), (x+40, y-5), (x+50, y+15), (x-30, y+20)], fill=(120, 50, 40), outline=BLACK, width=4)
    # Bone in steak
    draw.ellipse([x-20, y, x-10, y+10], fill=WHITE)
    # Steam lines
    for sx in [x-30, x, x+30]:
        draw.arc([sx-10, y-50, sx+10, y-20], start=100, end=270, fill=WHITE, width=3)

def draw_digestive_tract(draw, cx, cy, scale=1.0):
    """Draws digestive tract outline on top of a stickman torso."""
    s = scale
    y_start = cy - int(100*s)
    # Stomach
    draw.ellipse([cx-int(15*s), y_start, cx+int(15*s), y_start+int(25*s)], fill=RED, outline=BLACK, width=2)
    # Winding intestines
    draw.line([(cx, y_start+int(25*s)), (cx-int(10*s), y_start+int(35*s)), 
               (cx+int(10*s), y_start+int(45*s)), (cx, y_start+int(60*s))], fill=YELLOW, width=int(8*s))

def draw_skull(draw, x, y, scale=1.0):
    """Draws a clean white cartoon skull."""
    s = scale
    r = int(50*s)
    # Head sphere
    draw.ellipse([x-r, y-r, x+r, y+r], fill=WHITE, outline=BLACK, width=5)
    # Jaw
    draw.rectangle([x-int(25*s), y+int(10*s), x+int(25*s), y+int(60*s)], fill=WHITE, outline=BLACK, width=5)
    # Eye sockets
    draw.ellipse([x-int(22*s), y-int(10*s), x-int(6*s), y+int(10*s)], fill=BLACK)
    draw.ellipse([x+int(6*s), y-int(10*s), x+int(22*s), y+int(10*s)], fill=BLACK)
    # Nose cavity
    draw.polygon([(x, y+int(15*s)), (x-int(6*s), y+int(25*s)), (x+int(6*s), y+int(25*s))], fill=BLACK)
    # Teeth marks
    for tx in [x-int(15*s), x, x+int(15*s)]:
        draw.line([(tx, y+int(35*s)), (tx, y+int(50*s))], fill=BLACK, width=3)

def draw_brain(draw, x, y, scale=1.0, glow=True):
    """Draws a cartoon brain silhouette."""
    s = scale
    r = int(60*s)
    if glow:
        # Radial yellow glow ring
        draw.ellipse([x-r-30, y-r-20, x+r+30, y+r+20], fill=YELLOW)
    
    # Left lobe
    draw.ellipse([x-int(65*s), y-int(40*s), x, y+int(30*s)], fill=(240, 160, 180), outline=BLACK, width=4)
    # Right lobe
    draw.ellipse([x, y-int(40*s), x+int(65*s), y+int(30*s)], fill=(240, 160, 180), outline=BLACK, width=4)
    # Bottom details (cerebellum)
    draw.ellipse([x-int(40*s), y+int(15*s), x+int(40*s), y+int(50*s)], fill=(240, 130, 150), outline=BLACK, width=4)

def draw_city_skyline(draw, ground_y):
    """Draws a silhouette of a city skyline with simple lit window dots."""
    # Hill
    draw.arc([WIDTH//2-800, ground_y-100, WIDTH//2+800, ground_y+300], start=180, end=360, fill=BG_GROUND)
    # Buildings in background
    random.seed(1234)
    start_x = WIDTH//2
    for i in range(12):
        w = random.randint(40, 80)
        h = random.randint(100, 240)
        bx = start_x + i * 60
        by = ground_y - h - 10
        draw.rectangle([bx, by, bx+w, ground_y], fill=BLACK)
        # Windows
        if w > 50:
            for wx in [bx+15, bx+w-25]:
                for wy in range(by+20, ground_y-20, 40):
                    draw.ellipse([wx, wy, wx+6, wy+6], fill=YELLOW)

# ─── Main Render Handler ───────────────────────────────────────────
def render_scene(scene_num, output_path):
    img  = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)
    ground_y = int(HEIGHT * 0.78)

    if scene_num == 1:
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND)
        draw_stickman(draw, cx=WIDTH//2, cy=ground_y, scale=1.2, pose="stand", expression="surprised")
        draw_question_mark(draw, x=WIDTH//2, y=HEIGHT//2 - 190, scale=1.2)

    elif scene_num == 2:
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND)
        draw_stickman(draw, cx=WIDTH//2 - 150, cy=ground_y, scale=1.2, pose="point", expression="neutral")
        draw_dna(draw, x=WIDTH//2 + 150, y=HEIGHT//2 - 180, length=300, scale=1.3)

    elif scene_num == 3:
        draw_background(draw, sky=BG_GREEN, ground=BG_GROUND, horizon=0.6)
        draw_stickman(draw, cx=WIDTH//2 - 280, cy=ground_y, scale=1.2, pose="stand", expression="happy")
        draw_animals(draw, x=WIDTH//2 + 80, y=ground_y - 80)

    elif scene_num == 4:
        # Split background: Cold blue on left, Hot red on right
        draw.rectangle([0, 0, WIDTH//2, HEIGHT], fill=BG_COLD)
        draw.rectangle([WIDTH//2, 0, WIDTH, HEIGHT], fill=BG_HOT)
        draw.line([(WIDTH//2, 0), (WIDTH//2, HEIGHT)], fill=BLACK, width=4)
        # Shivering guy on left
        draw_stickman(draw, cx=WIDTH//4, cy=ground_y, scale=1.1, pose="shiver", expression="sad")
        # Sunburned guy on right
        draw_stickman(draw, cx=WIDTH*3//4, cy=ground_y, scale=1.1, pose="stand", expression="sad")
        # Hot Sun on right sky
        draw.ellipse([WIDTH*3//4 + 100, 80, WIDTH*3//4 + 200, 180], fill=YELLOW, outline=BLACK, width=3)

    elif scene_num == 5:
        # Space background with stars
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=BG_SPACE)
        for i in range(40):
            rx = random.randint(10, WIDTH-10)
            ry = random.randint(10, HEIGHT-10)
            draw.ellipse([rx, ry, rx+3, ry+3], fill=WHITE)
        # Earth globe
        earth_r = 160
        draw.ellipse([WIDTH//2-earth_r, HEIGHT//2-50, WIDTH//2+earth_r, HEIGHT//2+270], fill=BLUE, outline=BLACK, width=5)
        # Simple green continents
        draw.ellipse([WIDTH//2-60, HEIGHT//2, WIDTH//2+30, HEIGHT//2+100], fill=GREEN)
        draw.ellipse([WIDTH//2+20, HEIGHT//2+60, WIDTH//2+100, HEIGHT//2+180], fill=GREEN)
        # Stickman on top of globe
        draw_stickman(draw, cx=WIDTH//2, cy=HEIGHT//2-50, scale=0.9, pose="stand", expression="happy")

    elif scene_num == 6:
        draw_background(draw, sky=BG_DARK, ground=BG_GROUND, horizon=0.6)
        # Wood logs
        draw_campfire(draw, WIDTH//2, ground_y - 20, scale=0.8)
        # Falling spark
        draw.ellipse([WIDTH//2, HEIGHT//3, WIDTH//2+15, HEIGHT//3+15], fill=YELLOW)
        draw.line([(WIDTH//2+7, HEIGHT//3+7), (WIDTH//2+7, HEIGHT//2)], fill=YELLOW, width=3)

    elif scene_num == 7:
        draw_background(draw, sky=BG_SPACE, ground=BG_GROUND, horizon=0.6)
        # Stars in night sky
        for i in range(20):
            rx = random.randint(10, WIDTH-10)
            ry = random.randint(10, HEIGHT//2)
            draw.ellipse([rx, ry, rx+2, ry+2], fill=WHITE)
        # Campfire center
        draw_campfire(draw, WIDTH//2, ground_y - 20, scale=1.1)
        # Multiple stickmen around campfire
        draw_stickman(draw, cx=WIDTH//2 - 180, cy=ground_y, scale=1.1, pose="sit", expression="happy")
        draw_stickman(draw, cx=WIDTH//2 + 180, cy=ground_y, scale=1.1, pose="sit", expression="happy")

    elif scene_num == 8:
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND)
        # Stickman holding honeycomb
        draw_stickman(draw, cx=WIDTH//2 - 100, cy=ground_y, scale=1.2, pose="stand", expression="happy")
        draw_honeycomb(draw, x=WIDTH//2 + 150, y=HEIGHT//2 - 40, size=35)

    elif scene_num == 9:
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND)
        draw_stickman(draw, cx=WIDTH//2 - 180, cy=ground_y, scale=1.2, pose="stand", expression="happy")
        # Steak on plate
        draw_steak(draw, x=WIDTH//2 + 150, y=ground_y - 30)

    elif scene_num == 10:
        draw_background(draw, sky=BG_TEAL, ground=BG_GROUND)
        # Highlighted digestive tract on stickman
        draw_stickman(draw, cx=WIDTH//2, cy=ground_y, scale=1.3, pose="stand", expression="neutral")
        draw_digestive_tract(draw, cx=WIDTH//2, cy=ground_y, scale=1.3)

    elif scene_num == 11:
        draw_background(draw, sky=BG_DARK, ground=BG_GROUND)
        draw_stickman(draw, cx=WIDTH//2 - 200, cy=ground_y, scale=1.2, pose="point", expression="neutral")
        # Skull next to it
        draw_skull(draw, x=WIDTH//2 + 180, y=HEIGHT//2, scale=1.3)

    elif scene_num == 12:
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND)
        draw_stickman(draw, cx=WIDTH//2 - 200, cy=ground_y, scale=1.2, pose="point", expression="surprised")
        # Glowing Brain
        draw_brain(draw, x=WIDTH//2 + 180, y=HEIGHT//2 - 50, scale=1.3, glow=True)

    elif scene_num == 13:
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND)
        # Pointing to head with brain inside
        draw_stickman(draw, cx=WIDTH//2, cy=ground_y, scale=1.3, pose="point_head", expression="happy")
        # Small brain outline offset inside the head circle
        hc = (WIDTH//2, ground_y - int(160*1.3) - int(120*1.3) - int(65*1.3) - int(5*1.3))
        draw_brain(draw, x=hc[0], y=hc[1] + 10, scale=0.4, glow=False)

    elif scene_num == 14:
        # Same campfire setup as Scene 7 (repeats campfire narrative)
        draw_background(draw, sky=BG_SPACE, ground=BG_GROUND, horizon=0.6)
        for i in range(20):
            rx = random.randint(10, WIDTH-10)
            ry = random.randint(10, HEIGHT//2)
            draw.ellipse([rx, ry, rx+2, ry+2], fill=WHITE)
        draw_campfire(draw, WIDTH//2, ground_y - 20, scale=1.1)
        draw_stickman(draw, cx=WIDTH//2 - 180, cy=ground_y, scale=1.1, pose="sit", expression="happy")
        draw_stickman(draw, cx=WIDTH//2 + 180, cy=ground_y, scale=1.1, pose="sit", expression="happy")

    elif scene_num == 15:
        # Sunset background
        draw_background(draw, sky=BG_SKY, ground=BG_GROUND, horizon=0.6)
        # City skyline
        draw_city_skyline(draw, ground_y)
        # Stickman on left hill looking at city
        draw_stickman(draw, cx=WIDTH//4 - 50, cy=ground_y - 20, scale=1.1, pose="stand", expression="happy")

    img.save(output_path)
    print(f"Rendered programmatically scene {scene_num} to {output_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        num = int(sys.argv[1])
        out = sys.argv[2]
        render_scene(num, out)
    else:
        # Render a quick test for all 15 scenes
        os.makedirs(r"C:\Users\ASUS\kokoro\images_test", exist_ok=True)
        for i in range(1, 16):
            render_scene(i, f"C:\\Users\\ASUS\\kokoro\\images_test\\scene_{i}.png")
