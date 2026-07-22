import pygame, random, sys, os, json
pygame.init()

# ----------------------------------------------------------------------------
# DISPLAY SETUP
# ----------------------------------------------------------------------------
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption("THE RISE OF THE SINGULARITY")
W, H = screen.get_size()
clock = pygame.time.Clock()
# Gameplay (road/cars/effects) is drawn onto this surface first, then blitted
# to the real screen with a tiny random offset for the ambient speed-shake effect.
# HUD/buttons are drawn straight to the screen afterward so they never shake
# and stay perfectly tappable.
world_surface = pygame.Surface((W, H))
prev_world_surface = None  # last frame's world, reused for a subtle motion-blur ghost at high speed

# ----------------------------------------------------------------------------
# COLORS
# ----------------------------------------------------------------------------
GRAY = (70, 70, 70)
GREEN = (30, 150, 30)
WHITE = (255, 255, 255)
BLUE = (60, 120, 255)
RED = (230, 60, 60)
BLACK = (20, 20, 20)
YELLOW = (255, 220, 0)
ORANGE = (255, 140, 0)
DARK_ORANGE = (170, 90, 0)
CYAN = (70, 220, 220)
DARK_BLUE = (30, 60, 140)
PANEL = (0, 0, 0)

# ----------------------------------------------------------------------------
# ROAD SETUP
# ----------------------------------------------------------------------------
road_w = int(W * 0.62)
road_x = (W - road_w) // 2

font = pygame.font.SysFont(None, 42)
small_font = pygame.font.SysFont(None, 32)
big = pygame.font.SysFont(None, 80)
mid = pygame.font.SysFont(None, 54)

# ----------------------------------------------------------------------------
# GAME TITLE ("THE RISE OF THE SINGULARITY") — stylish two-line rendering,
# used on the start screen and the game over screen.
# ----------------------------------------------------------------------------
TITLE_TEXT_LINE1 = "THE RISE OF THE"
TITLE_TEXT_LINE2 = "SINGULARITY"
title_font_line1 = pygame.font.SysFont(None, 52, bold=True)
title_font_line2 = pygame.font.SysFont(None, 92, bold=True)
title_font_line1_small = pygame.font.SysFont(None, 34, bold=True)
title_font_line2_small = pygame.font.SysFont(None, 56, bold=True)

def draw_title(surface, center_x, top_y, large=True):
    """Draw the stylish two-line game title, centered at center_x, starting at top_y.
    Returns the total pixel height used, so callers can stack content below it."""
    f1 = title_font_line1 if large else title_font_line1_small
    f2 = title_font_line2 if large else title_font_line2_small

    line1 = f1.render(TITLE_TEXT_LINE1, True, WHITE)
    line2 = f2.render(TITLE_TEXT_LINE2, True, CYAN)
    # Soft glow behind line 2 (a darker, slightly offset duplicate) for a stylish sci-fi look.
    glow = f2.render(TITLE_TEXT_LINE2, True, (10, 70, 80))

    line1_pos = (center_x - line1.get_width() // 2, top_y)
    line2_y = top_y + line1.get_height() + (10 if large else 4)
    glow_pos = (center_x - glow.get_width() // 2 + 3, line2_y + 3)
    line2_pos = (center_x - line2.get_width() // 2, line2_y)

    surface.blit(line1, line1_pos)
    surface.blit(glow, glow_pos)
    surface.blit(line2, line2_pos)

    return (line2_y + line2.get_height()) - top_y

# ----------------------------------------------------------------------------
# CAR GRAPHICS — a small stylized car drawn with Pygame primitives, used for
# both the player and the enemies (with different colors/facing direction).
# ----------------------------------------------------------------------------
def draw_car(surface, rect, body_color, facing="up"):
    """
    Draw a stylized car: rounded body, roof, windshield, headlights, tail
    lights, wheels, and a soft ground shadow.
    facing: "up" puts the headlights at the top (used for the player, who
    drives "forward" up the screen); "down" puts them at the bottom (used
    for oncoming enemy traffic).
    """
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    # --- ground shadow ---
    shadow_surf = pygame.Surface((w + 16, h + 16), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0, 0, 0, 80), (8, 12, w, h), border_radius=18)
    surface.blit(shadow_surf, (x - 8, y - 4))

    # --- wheels (drawn under the body so only the outer edge peeks out) ---
    wheel_color = (18, 18, 18)
    wheel_w, wheel_h = 14, int(h * 0.20)
    wheel_ys = [y + h * 0.18, y + h * 0.62]
    for wy in wheel_ys:
        pygame.draw.rect(surface, wheel_color, (x - wheel_w // 2 + 3, int(wy), wheel_w, wheel_h), border_radius=6)
        pygame.draw.rect(surface, wheel_color, (x + w - wheel_w // 2 - 3, int(wy), wheel_w, wheel_h), border_radius=6)

    # --- body ---
    pygame.draw.rect(surface, body_color, rect, border_radius=20)
    darker = tuple(max(0, c - 45) for c in body_color)
    pygame.draw.rect(surface, darker, rect, width=3, border_radius=20)

    # --- roof (inset, shifted toward the rear half of the car) ---
    roof_w, roof_h = int(w * 0.60), int(h * 0.32)
    roof_x = x + (w - roof_w) // 2
    roof_y = y + int(h * (0.30 if facing == "up" else 0.38))
    roof_color = tuple(max(0, c - 60) for c in body_color)
    pygame.draw.rect(surface, roof_color, (roof_x, roof_y, roof_w, roof_h), border_radius=10)

    # --- windshield (toward the front) and rear window (toward the back) ---
    glass_w = int(w * 0.54)
    glass_x = x + (w - glass_w) // 2
    windshield_h = int(h * 0.13)
    rear_h = int(h * 0.09)
    if facing == "up":
        windshield_y = roof_y - windshield_h - 2
        rear_y = roof_y + roof_h + 2
    else:
        windshield_y = roof_y + roof_h + 2
        rear_y = roof_y - rear_h - 2
    pygame.draw.rect(surface, (150, 212, 235), (glass_x, windshield_y, glass_w, windshield_h), border_radius=6)
    pygame.draw.rect(surface, (105, 165, 190), (glass_x, rear_y, glass_w, rear_h), border_radius=6)

    # --- headlights (front edge) ---
    hl_w, hl_h = int(w * 0.18), 10
    hl_y = y + 6 if facing == "up" else y + h - 6 - hl_h
    pygame.draw.rect(surface, (255, 248, 200), (x + 8, hl_y, hl_w, hl_h), border_radius=4)
    pygame.draw.rect(surface, (255, 248, 200), (x + w - 8 - hl_w, hl_y, hl_w, hl_h), border_radius=4)

    # --- tail lights (rear edge) ---
    tl_w, tl_h = int(w * 0.16), 8
    tl_y = y + h - 6 - tl_h if facing == "up" else y + 6
    pygame.draw.rect(surface, (225, 40, 40), (x + 8, tl_y, tl_w, tl_h), border_radius=4)
    pygame.draw.rect(surface, (225, 40, 40), (x + w - 8 - tl_w, tl_y, tl_w, tl_h), border_radius=4)

# ----------------------------------------------------------------------------
# PLAYER
# ----------------------------------------------------------------------------
player = pygame.Rect(W // 2 - 40, H - 220, 80, 140)
MOVE_SPEED = 20  # steering speed, always constant now (no nitro boost to steering)

# ----------------------------------------------------------------------------
# PLAYER SPRITE (assets/player_car.png) — replaces the old drawn car as the
# player's visual. If the PNG can't be loaded for any reason, the game
# automatically falls back to the original drawn car instead of crashing.
# ----------------------------------------------------------------------------
def load_player_sprite():
    try:
        sprite = pygame.image.load("assets/player_car.png").convert_alpha()
        print("PLAYER PNG LOADED")
        return sprite
    except Exception:
        print("PLAYER PNG FAILED")
        return None

player_sprite_original = load_player_sprite()

def draw_player(surface, rect):
    """
    Draw the player: assets/player_car.png scaled to fit the current player
    Rect size (rect.width x rect.height) and drawn at (rect.x, rect.y), so it
    stays perfectly aligned with the collision box. If the PNG never loaded,
    falls back to the original drawn car sprite so the game never crashes.
    """
    if player_sprite_original is not None:
        scaled_sprite = pygame.transform.smoothscale(player_sprite_original, (rect.width, rect.height))
        surface.blit(scaled_sprite, (rect.x, rect.y))
    else:
        draw_car(surface, rect, RED, facing="up")

# ----------------------------------------------------------------------------
# HIGH SCORE PERSISTENCE (local file, safe for Android/Pydroid)
# ----------------------------------------------------------------------------
HS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

def load_high_score():
    try:
        with open(HS_PATH, "r") as f:
            data = json.load(f)
            return int(data.get("high_score", 0))
    except Exception:
        return 0

def save_high_score(value):
    try:
        with open(HS_PATH, "w") as f:
            json.dump({"high_score": int(value)}, f)
    except Exception:
        pass  # fail silently if storage isn't writable (e.g. restricted Android storage)

high_score = load_high_score()

# ----------------------------------------------------------------------------
# ENEMY / LANE SYSTEM
# ----------------------------------------------------------------------------
ENEMY_W, ENEMY_H = 80, 140
LANE_COUNT = 3
LANE_W = road_w / LANE_COUNT

# Shared color palette so enemy cars come in varied colors wherever they spawn.
ENEMY_COLORS = [
    (35, 35, 38),     # near-black
    (30, 60, 140),    # dark blue
    (150, 45, 45),    # dark red
    (40, 110, 45),    # dark green
    (150, 130, 20),   # amber
    (110, 55, 150),   # purple
]

def lane_center_x(lane_index):
    """Return the x (left edge) for an enemy centered in the given lane."""
    center = road_x + LANE_W * (lane_index + 0.5)
    return int(center - ENEMY_W / 2)

# ----------------------------------------------------------------------------
# FAIR LANE SELECTION (fixes the "one lane stays permanently empty" exploit)
# ----------------------------------------------------------------------------
# Every lane must have an equal chance of being chosen, but the SAME lane is
# never allowed to be picked more than 2 times in a row — this guarantees no
# lane can ever become a permanently safe parking spot, without ever creating
# an impossible dodge (there's always at least one legal lane to pick from).
last_main_lane = None
lane_repeat_streak = 0

def choose_next_lane():
    """Pick the next enemy lane with equal probability per lane, forbidding a 3rd consecutive repeat."""
    global last_main_lane, lane_repeat_streak

    candidates = list(range(LANE_COUNT))
    if last_main_lane is not None and lane_repeat_streak >= 2 and len(candidates) > 1:
        candidates.remove(last_main_lane)  # block a 3rd consecutive spawn in the same lane

    lane = random.choice(candidates)

    if lane == last_main_lane:
        lane_repeat_streak += 1
    else:
        lane_repeat_streak = 1
    last_main_lane = lane

    return lane

# --- Speed is defined in KM/H first, then converted to pixels/frame, so the
# --- speedometer always matches what's actually happening on screen. ---
# PX_PER_KMH is calibrated so the starting speed (60 KM/H) scrolls at ~29 px/frame,
# which is ~20% faster than the old flat 24 px/frame baseline (better sense of speed).
PX_PER_KMH = 29 / 60

def speed_kmh_to_px(kmh):
    """Convert a KM/H value into the matching pixels-per-frame scroll/move speed."""
    return kmh * PX_PER_KMH

BASE_ENEMY_SPEED = int(round(speed_kmh_to_px(60)))  # pixel speed at the starting 60 KM/H
MIN_VERTICAL_GAP = 250  # minimum vertical gap between enemies to guarantee no overlap

# Extra vertical offset added whenever the single enemy car respawns, so it
# doesn't reappear the instant it leaves the screen. Combined with
# REACTION_GAP_SECONDS below, this guarantees the player always gets a full,
# fair reaction window before the next car arrives — at any speed.
SPAWN_RATE_REDUCTION = 0.4
BASE_SPAWN_EXTRA_GAP = int(H * SPAWN_RATE_REDUCTION)

# Minimum time (in seconds, at the CURRENT road speed) the player is guaranteed
# to have with an empty road before the next single enemy car appears on
# screen. This is what keeps one-steering-move dodging always fair, even as
# top speed climbs toward MAX_SPEED_KMH.
REACTION_GAP_SECONDS = 1.4

def make_enemy(speed, existing, min_y_offset=0, lane=None):
    """
    Create a new enemy placed in a lane chosen by the fair lane-selection
    system (equal chance per lane, never 3-in-a-row), spawned high enough
    above the screen that it never overlaps another enemy already in that lane.
    """
    if lane is None:
        lane = choose_next_lane()
    x = lane_center_x(lane)
    spawn_y = -ENEMY_H - min_y_offset

    # Push spawn_y higher if another enemy in the same lane is too close.
    for other in existing:
        if other["rect"].x == x:
            if other["rect"].y - spawn_y < MIN_VERTICAL_GAP:
                spawn_y = other["rect"].y - MIN_VERTICAL_GAP

    return {
        "rect": pygame.Rect(x, spawn_y, ENEMY_W, ENEMY_H),
        "speed": speed,
        "color": random.choice(ENEMY_COLORS),
    }

enemies = []
INITIAL_ENEMY_COUNT = 1  # single-obstacle traffic system: exactly one enemy car, ever

for _ in range(INITIAL_ENEMY_COUNT):
    enemies.append(make_enemy(BASE_ENEMY_SPEED, enemies, min_y_offset=random.randint(0, 900)))

# ----------------------------------------------------------------------------
# OCCASIONAL TWO-CAR EVENTS (rare, always with a guaranteed free lane)
# ----------------------------------------------------------------------------
# Normal gameplay always has exactly ONE enemy car. Every so often (roughly
# once every 20-30 seconds) a second car is added alongside it as a brief,
# clearly-telegraphed pair. The pair only ever occupies 2 of the 3 lanes, so
# one lane is ALWAYS guaranteed free — the situation is never unavoidable and
# never requires the Gun, just a single steering move into the open lane.
DOUBLE_SPAWN_MIN_GAP = 20.0   # seconds, minimum time between two-car events
DOUBLE_SPAWN_MAX_GAP = 30.0   # seconds, maximum time between two-car events
DOUBLE_SPAWN_HEAD_START_MULT = 1.6  # extra vertical head start so the pair is easy to see coming

last_double_spawn_time = 0.0  # run_time at which the last two-car event started
next_double_spawn_gap = random.uniform(DOUBLE_SPAWN_MIN_GAP, DOUBLE_SPAWN_MAX_GAP)

# ----------------------------------------------------------------------------
# GAME STATE
# ----------------------------------------------------------------------------
left_pressed = False
right_pressed = False
started = False
game_over = False
score = 0
line = 0
new_high_score = False
run_time = 0.0  # seconds since the current run started (used for the easy-start window)

# ----------------------------------------------------------------------------
# AMBIENT "NITRO-STYLE" VISUAL EFFECTS (always on, no button, no cooldown)
# ----------------------------------------------------------------------------
# These effects are purely cosmetic and scale automatically with the current
# road speed (KM/H). The car itself always drives at its normal, balanced
# speed — only the visuals (trail / road lines / glow / shake) ramp up.
SPEED_KMH_MIN = 60    # intensity 0.0 at this speed
SPEED_KMH_MAX = 230   # intensity 1.0 at this speed (matches MAX_SPEED_KMH, the hard speed cap)

ROAD_LINE_MAX_MULTIPLIER = 1.6   # road markings scroll up to 60% faster at max intensity
TRAIL_MAX_EXTRA_PARTICLES = 3    # up to +3 extra trail particles per frame at max intensity
TRAIL_BASE_PARTICLES = 1         # always at least 1 particle per frame while driving
GLOW_MAX_RADIUS_BONUS = 14       # glow ring grows up to this many extra px at max intensity
GLOW_MAX_ALPHA = 160             # glow ring's peak opacity at max intensity
CAMERA_SHAKE_MAX_STRENGTH = 1    # extremely subtle — at most 1px jitter at max intensity

trail_particles = []  # blue speed-trail particles spawned behind the car

def speed_intensity(kmh):
    """0.0 .. 1.0 ramp based on current road speed, used to scale all ambient effects."""
    span = SPEED_KMH_MAX - SPEED_KMH_MIN
    if span <= 0:
        return 0.0
    t = (kmh - SPEED_KMH_MIN) / span
    return max(0.0, min(1.0, t))

# ----------------------------------------------------------------------------
# EMERGENCY GUN SYSTEM (the only special ability — one charge, long cooldown)
# ----------------------------------------------------------------------------
GUN_COOLDOWN = 25.0  # seconds (within the requested 20-30s range)

gun_charges = 1          # starts with one charge ready
gun_cooldown_left = 0.0  # counts down after firing; charge returns to 1 at 0

explosions = []  # active explosion animations: {"pos", "timer", "max_timer"}

def gun_ready():
    return gun_charges >= 1 and gun_cooldown_left <= 0

def fire_gun():
    """
    Destroy the nearest enemy directly ahead of the player (same lane / x-overlap
    preferred, otherwise the closest enemy overall), play an explosion, respawn
    a fresh enemy from the top, and award +1 score.
    """
    global gun_charges, gun_cooldown_left, score

    if not enemies or not gun_ready():
        return

    # Prefer enemies that overlap the player's x-range (i.e. directly ahead).
    ahead = [en for en in enemies if en["rect"].right > player.left and en["rect"].left < player.right]
    candidates = ahead if ahead else enemies

    target = min(candidates, key=lambda en: abs(en["rect"].centery - player.centery))

    # Explosion animation at the destroyed car's position.
    explosions.append({"pos": target["rect"].center, "timer": 0.35, "max_timer": 0.35})

    # Safely remove and respawn a new enemy from the top.
    others = [en for en in enemies if en is not target]
    fresh = make_enemy(target["speed"], others, min_y_offset=BASE_SPAWN_EXTRA_GAP)
    target["rect"] = fresh["rect"]
    target["color"] = fresh["color"]

    score += 1
    gun_charges = 0
    gun_cooldown_left = GUN_COOLDOWN

# ----------------------------------------------------------------------------
# EASY-START WINDOW
# ----------------------------------------------------------------------------
EASY_START_SECONDS = 10.0  # difficulty is held at its easiest during this window

# ----------------------------------------------------------------------------
# TOUCH CONTROLS (Nitro button removed — only steering + gun remain)
# ----------------------------------------------------------------------------
lb = pygame.Rect(40, H - 180, 140, 140)
rb = pygame.Rect(W - 180, H - 180, 140, 140)
gun_btn = pygame.Rect(40, H - 360, 140, 140)  # above the left (move) button

def reset_game():
    """Reset all round-specific state for a fresh run."""
    global score, player, enemies, new_high_score, run_time
    global trail_particles
    global gun_charges, gun_cooldown_left, explosions
    global last_double_spawn_time, next_double_spawn_gap
    global last_main_lane, lane_repeat_streak
    score = 0
    run_time = 0.0
    new_high_score = False
    player.centerx = W // 2
    enemies = []
    for _ in range(INITIAL_ENEMY_COUNT):
        enemies.append(make_enemy(BASE_ENEMY_SPEED, enemies, min_y_offset=random.randint(0, 900)))
    trail_particles = []
    gun_charges = 1
    gun_cooldown_left = 0.0
    explosions = []
    last_double_spawn_time = 0.0
    next_double_spawn_gap = random.uniform(DOUBLE_SPAWN_MIN_GAP, DOUBLE_SPAWN_MAX_GAP)
    last_main_lane = None
    lane_repeat_streak = 0

MAX_SPEED_KMH = 230  # hard speed ceiling — once reached, speed stops increasing entirely

def current_speed_kmh(score_value):
    """
    Road/traffic speed in KM/H, scaling with score. This is the only lever
    used to raise difficulty at high scores — traffic stays single-car the
    whole game. Speed climbs in gentle stages and is hard-capped at
    MAX_SPEED_KMH so the game never becomes unfair, only faster.
    60 -> 80 (10) -> 100 (20) -> 120 (40) -> 140 (70) -> 160..230 (100+, capped)
    """
    if score_value >= 100:
        extra_stages = (score_value - 100) // 25
        return min(MAX_SPEED_KMH, 160 + extra_stages * 5)  # keeps climbing gradually, then caps
    elif score_value >= 70:
        return 140
    elif score_value >= 40:
        return 120
    elif score_value >= 20:
        return 100
    elif score_value >= 10:
        return 80
    return 60

# ----------------------------------------------------------------------------
# MAIN LOOP
# ----------------------------------------------------------------------------
while True:
    dt = clock.tick(60) / 1000.0  # delta time in seconds, for gun/effect timers
    shake_x, shake_y = 0, 0  # ambient camera shake offset, extremely subtle at high speed

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if e.type == pygame.MOUSEBUTTONDOWN:
            if not started:
                started = True
            elif game_over:
                # Tap anywhere (except the buttons) restarts the run
                game_over = False
                reset_game()

            if lb.collidepoint(e.pos):
                left_pressed = True
            if rb.collidepoint(e.pos):
                right_pressed = True
            if gun_btn.collidepoint(e.pos) and started and not game_over:
                fire_gun()

        if e.type == pygame.MOUSEBUTTONUP:
            left_pressed = False
            right_pressed = False

    # --------------------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------------------
    intensity = 0.0  # ambient effect intensity for this frame (0 while not driving)

    if started and not game_over:
        run_time += dt

        # --- smooth left/right movement (always the normal, balanced speed) ---
        if left_pressed:
            player.x -= MOVE_SPEED
        if right_pressed:
            player.x += MOVE_SPEED

        # --- boundary check ---
        if player.left < road_x - 12 or player.right > road_x + road_w + 12:
            game_over = True

        # --- gun cooldown / recharge ---
        if gun_charges < 1:
            gun_cooldown_left -= dt
            if gun_cooldown_left <= 0:
                gun_cooldown_left = 0
                gun_charges = 1  # recharged and ready

        # --- explosion animations (from the emergency gun) ---
        for ex in explosions:
            ex["timer"] -= dt
        explosions = [ex for ex in explosions if ex["timer"] > 0]

        # --- difficulty scaling: KM/H stage table (held at the starting 60 KM/H
        # --- for the first EASY_START_SECONDS so the run opens gently) ---
        if run_time < EASY_START_SECONDS:
            speed_kmh = 60
        else:
            speed_kmh = current_speed_kmh(score)

        # Actual pixels/frame the road and traffic move at — enemies always match
        # the road exactly, which is what keeps the speedometer honest.
        target_speed = int(round(speed_kmh_to_px(speed_kmh)))

        # Ambient visual intensity always tracks current road speed automatically —
        # no button, no timer, just a smooth ramp from 0 to 1 as speed climbs.
        intensity = speed_intensity(speed_kmh)

        # --- how far above the screen the single enemy should respawn ---
        # Scales with current speed (px/frame * 60 frames/sec * reaction seconds)
        # so the player always gets the same real-world reaction time before
        # the next car appears, no matter how fast the road is moving.
        reaction_gap_px = int(target_speed * 60 * REACTION_GAP_SECONDS)
        spawn_extra_gap = max(BASE_SPAWN_EXTRA_GAP, reaction_gap_px)

        # --- move every current enemy (normally just one; briefly two during a two-car event) ---
        for enemy in enemies:
            enemy["speed"] = target_speed
            enemy["rect"].y += enemy["speed"]

        # --- figure out which enemies left the screen this frame ---
        extra_present = any(en.get("extra") for en in enemies)
        main_enemy = None
        leaving_extra = []
        for enemy in enemies:
            if enemy["rect"].top > H:
                score += 1
                if enemy.get("extra"):
                    leaving_extra.append(enemy)  # the temporary second car just leaves — never replaced
                else:
                    main_enemy = enemy  # the one persistent car — always gets recycled

        for en in leaving_extra:
            enemies.remove(en)

        if main_enemy is not None:
            others = [en for en in enemies if en is not main_enemy]

            # A two-car event may trigger here: only when traffic is back to a
            # single car, the easy-start window has passed, and enough time has
            # elapsed since the last one (roughly every 20-30 seconds).
            double_due = (
                not extra_present
                and len(others) == 0
                and run_time >= EASY_START_SECONDS
                and (run_time - last_double_spawn_time) >= next_double_spawn_gap
            )

            if double_due:
                # The main car's lane is chosen through the SAME fair lane
                # system as normal spawns (equal chance, no 3-in-a-row). The
                # second car then takes one of the two remaining lanes, so
                # together they only ever occupy 2 of the 3 lanes — the third
                # lane is mathematically guaranteed to stay empty.
                paired_lanes = [choose_next_lane()]
                remaining_lanes = [l for l in range(LANE_COUNT) if l != paired_lanes[0]]
                paired_lanes.append(random.choice(remaining_lanes))
                spawn_y = -ENEMY_H - int(spawn_extra_gap * DOUBLE_SPAWN_HEAD_START_MULT)

                main_enemy["rect"] = pygame.Rect(lane_center_x(paired_lanes[0]), spawn_y, ENEMY_W, ENEMY_H)
                main_enemy["color"] = random.choice(ENEMY_COLORS)

                enemies.append({
                    "rect": pygame.Rect(lane_center_x(paired_lanes[1]), spawn_y, ENEMY_W, ENEMY_H),
                    "speed": target_speed,
                    "color": random.choice(ENEMY_COLORS),
                    "extra": True,
                })

                last_double_spawn_time = run_time
                next_double_spawn_gap = random.uniform(DOUBLE_SPAWN_MIN_GAP, DOUBLE_SPAWN_MAX_GAP)
            else:
                new_enemy = make_enemy(target_speed, others, min_y_offset=spawn_extra_gap)
                main_enemy["rect"] = new_enemy["rect"]
                main_enemy["color"] = new_enemy["color"]

        # --- collision detection (slightly tighter hitbox for fairness) ---
        player_hitbox = player.inflate(-18, -10)
        for enemy in enemies:
            if player_hitbox.colliderect(enemy["rect"].inflate(-18, -10)):
                game_over = True
                if score > high_score:
                    high_score = score
                    new_high_score = True
                    save_high_score(high_score)
                break

        # --- blue speed-trail particles (spawned behind the car, always active,
        # --- density/size scale automatically with current speed intensity) ---
        particles_this_frame = TRAIL_BASE_PARTICLES + round(intensity * TRAIL_MAX_EXTRA_PARTICLES)
        for _ in range(particles_this_frame):
            trail_particles.append({
                "x": player.centerx + random.randint(-16, 16),
                "y": player.bottom - 6,
                "alpha": int(140 + intensity * 60),
                "size": random.randint(10 + int(intensity * 4), 16 + int(intensity * 8)),
            })
        for p in trail_particles:
            p["y"] += 10 + intensity * 8
            p["alpha"] -= 14
        trail_particles = [p for p in trail_particles if p["alpha"] > 0 and p["y"] < H]

        # --- animated lane markings scroll with current speed, automatically
        # --- getting faster as speed intensity rises (no nitro button needed) ---
        line_multiplier = 1.0 + intensity * (ROAD_LINE_MAX_MULTIPLIER - 1.0)
        line_speed = target_speed * line_multiplier
        line = (line + int(line_speed)) % 120

        # --- extremely subtle ambient camera shake, scaling with speed intensity ---
        shake_amount = CAMERA_SHAKE_MAX_STRENGTH * intensity
        if shake_amount >= 0.5:
            shake_x = random.randint(-int(round(shake_amount)), int(round(shake_amount)))
            shake_y = random.randint(-int(round(shake_amount)), int(round(shake_amount)))
        else:
            shake_x, shake_y = 0, 0

    # --------------------------------------------------------------------
    # DRAW (gameplay world first, onto world_surface, then HUD onto screen)
    # --------------------------------------------------------------------
    world_surface.fill(GREEN)
    pygame.draw.rect(world_surface, GRAY, (road_x, 0, road_w, H))

    y = -120 + line
    while y < H:
        pygame.draw.rect(world_surface, WHITE, (W // 2 - 8, y, 16, 70))
        y += 120

    if not started:
        title_bottom = H // 3
        used_h = draw_title(world_surface, W // 2, title_bottom, large=True)
        s = font.render("Tap Anywhere To Start", True, WHITE)
        hs = small_font.render(f"High Score: {high_score}", True, CYAN)
        world_surface.blit(s, (W // 2 - s.get_width() // 2, title_bottom + used_h + 30))
        world_surface.blit(hs, (W // 2 - hs.get_width() // 2, title_bottom + used_h + 90))
    else:
        # --- blue speed-trail particles (drawn behind the car) ---
        for p in trail_particles:
            trail_surf = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (60, 160, 255, max(0, p["alpha"])),
                                (p["size"], p["size"]), p["size"])
            world_surface.blit(trail_surf, (p["x"] - p["size"], p["y"] - p["size"]))

        # enemies (oncoming traffic — headlights face down, toward the player)
        for enemy in enemies:
            draw_car(world_surface, enemy["rect"], enemy["color"], facing="down")

        # --- soft glow around the player car, intensifying automatically with speed ---
        if not game_over and intensity > 0.01:
            glow_radius = max(player.width, player.height) // 2 + int(GLOW_MAX_RADIUS_BONUS * intensity)
            glow_alpha = int(GLOW_MAX_ALPHA * intensity)
            glow_size = glow_radius * 2
            glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (70, 200, 255, glow_alpha), (glow_radius, glow_radius), glow_radius)
            world_surface.blit(glow_surf, (player.centerx - glow_radius, player.centery - glow_radius),
                                special_flags=pygame.BLEND_RGBA_ADD)

        # player (headlights face up, toward the direction of travel) —
        # uses assets/player_car.png if it loaded, else falls back to the drawn car
        draw_player(world_surface, player)

        # --- explosion animations (from the emergency gun) ---
        for ex in explosions:
            progress = 1 - (ex["timer"] / ex["max_timer"])  # 0 -> 1 over the explosion's life
            radius = int(20 + progress * 60)
            alpha = max(0, int(255 * (1 - progress)))
            exp_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(exp_surf, (255, 180, 30, alpha), (radius, radius), radius)
            pygame.draw.circle(exp_surf, (255, 240, 150, alpha), (radius, radius), max(1, radius // 2))
            world_surface.blit(exp_surf, (ex["pos"][0] - radius, ex["pos"][1] - radius))

    # Blit the gameplay world with the (extremely subtle) ambient shake offset.
    screen.fill(BLACK)
    if intensity > 0.5 and prev_world_surface is not None:
        # Faint motion-blur "road blur" ghost at higher speeds, to sell a
        # stronger sense of speed without any button press required.
        ghost = prev_world_surface.copy()
        ghost.set_alpha(int(40 * intensity))
        screen.blit(ghost, (shake_x, shake_y + 4))
    screen.blit(world_surface, (shake_x, shake_y))
    prev_world_surface = world_surface.copy()

    # --------------------------------------------------------------------
    # HUD / BUTTONS (drawn directly to the screen — never shakes)
    # --------------------------------------------------------------------
    if started:
        # --- movement buttons ---
        pygame.draw.rect(screen, BLUE, lb, border_radius=20)
        pygame.draw.rect(screen, BLUE, rb, border_radius=20)
        screen.blit(font.render("<", True, WHITE), (lb.centerx - 10, lb.centery - 20))
        screen.blit(font.render(">", True, WHITE), (rb.centerx - 10, rb.centery - 20))

        # --- emergency gun button (the only special ability) ---
        if gun_ready():
            g_color = ORANGE
        else:
            g_color = DARK_ORANGE
        pygame.draw.rect(screen, g_color, gun_btn, border_radius=20)
        screen.blit(small_font.render("GUN", True, WHITE), (gun_btn.centerx - 28, gun_btn.centery - 12))
        if not gun_ready():
            cd_text = small_font.render(f"{gun_cooldown_left:0.0f}", True, WHITE)
            screen.blit(cd_text, (gun_btn.centerx - cd_text.get_width() // 2, gun_btn.bottom + 6))

        # --- score / speed / high score readout ---
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (20, 20))

        if not game_over:
            speed_display = 60 if run_time < EASY_START_SECONDS else current_speed_kmh(score)
        else:
            speed_display = current_speed_kmh(score)
        speed_text = small_font.render(f"{speed_display} KM/H", True, CYAN)
        screen.blit(speed_text, (20, 70))

        hs_text = small_font.render(f"High Score: {high_score}", True, YELLOW)
        screen.blit(hs_text, (W - hs_text.get_width() - 20, 20))

        # --- game over overlay ---
        if game_over:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            title_top = int(H * 0.10)
            title_used_h = draw_title(screen, W // 2, title_top, large=False)

            go_y = title_top + title_used_h + 30
            go_text = big.render("GAME OVER", True, RED)
            screen.blit(go_text, (W // 2 - go_text.get_width() // 2, go_y))

            final_score_text = mid.render(f"Score: {score}", True, WHITE)
            screen.blit(final_score_text, (W // 2 - final_score_text.get_width() // 2, go_y + 90))

            if new_high_score:
                nhs_text = mid.render("New High Score!", True, YELLOW)
                screen.blit(nhs_text, (W // 2 - nhs_text.get_width() // 2, go_y + 150))
            else:
                hs_text2 = font.render(f"High Score: {high_score}", True, CYAN)
                screen.blit(hs_text2, (W // 2 - hs_text2.get_width() // 2, go_y + 150))

            restart_text = font.render("Tap Anywhere To Restart", True, WHITE)
            screen.blit(restart_text, (W // 2 - restart_text.get_width() // 2, go_y + 220))

    pygame.display.flip()
