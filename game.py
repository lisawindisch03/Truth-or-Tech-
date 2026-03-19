import pygame
import time
import smbus2
import RPi.GPIO as GPIO
import statistics
import os
import subprocess
import random
import math

print("--- INITIALISIERE HARDWARE ---")

# --- HARDWARE CONFIG ---
ADDRESS = 0x04
try:
    BUS = smbus2.SMBus(1)
except Exception as e:
    print(f"FEHLER: I2C Bus nicht gefunden: {e}")


    class DummyBus:
        def write_i2c_block_data(self, a, b, c): pass

        def read_i2c_block_data(self, a, b, c): return [0, 0, 0]


    BUS = DummyBus()

# BUTTON PINS
BTN_P1 = 4  # Weiss (Action)
BTN_P2_T = 23  # Weiss (Wahrheit)
BTN_P2_L = 24  # Pink (Lüge)
BTN_OFF = 7  # OFF Button

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for pin in [BTN_P1, BTN_P2_T, BTN_P2_L, BTN_OFF]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- DISPLAY CONFIG ---
os.environ['DISPLAY'] = ':0'
os.environ['SDL_VIDEODRIVER'] = 'x11'
os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
os.environ["SDL_RENDER_VSYNC"] = "1"

pygame.init()
pygame.mouse.set_visible(False)

SCREEN_W, SCREEN_H = 1600, 480
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.NOFRAME | pygame.DOUBLEBUF | pygame.HWSURFACE)

# --- STYLING ---
COLOR_BG = (5, 5, 15)
COLOR_PANEL_BG = (25, 25, 45)
COLOR_NEON_G = (50, 255, 50)
COLOR_NEON_P = (255, 50, 180)
COLOR_NEON_B = (50, 220, 255)
COLOR_WHITE = (220, 220, 220)
COLOR_RED = (255, 30, 30)
COLOR_BLACK = (10, 10, 10)  # For text on highlighted buttons

FONT_XL = pygame.font.SysFont("Arial Black", 70, bold=True)
FONT_L = pygame.font.SysFont("Arial Black", 45, bold=True)
FONT_M = pygame.font.SysFont("Arial Black", 28, bold=True)
FONT_S = pygame.font.SysFont("Arial Black", 18, bold=True)

# --- PRE-RENDER BACKGROUND ---
static_background = pygame.Surface((SCREEN_W, SCREEN_H))
static_background.fill(COLOR_BG)
grid_color = (15, 15, 35)
for x in range(0, SCREEN_W, 40):
    pygame.draw.line(static_background, grid_color, (x, 0), (x, SCREEN_H), 1)
for y in range(0, SCREEN_H, 40):
    pygame.draw.line(static_background, grid_color, (0, y), (SCREEN_W, y), 1)


# --- GSR LOGIC (Non-Blocking) ---
def get_gsr():
    try:
        BUS.write_i2c_block_data(ADDRESS, 1, [3, 0, 0, 0])
        time.sleep(0.005)
        data = BUS.read_i2c_block_data(ADDRESS, 1, 3)
        val = (data[1] * 256) + data[2]
        return val
    except Exception:
        return None


# --- VISUALS ---
gsr_history = []


def draw_panel(rect, color, highlight=False):
    """
    Draws a panel. If highlight is True, the box is filled with the 'color',
    otherwise it has a dark background and a colored border.
    """
    if highlight:
        # Fill completely with the neon color
        pygame.draw.rect(screen, color, rect)
    else:
        # Standard look
        pygame.draw.rect(screen, COLOR_PANEL_BG, rect)
        pygame.draw.rect(screen, color, rect, 3)


def draw_waveform(val, x, y, w, h, color):
    rect = pygame.Rect(x, y, w, h)

    # 1. Background
    pygame.draw.rect(screen, COLOR_PANEL_BG, rect)

    # 2. Clip
    clip_rect = rect.inflate(-8, -8)
    screen.set_clip(clip_rect)

    # 3. Calculate Points
    min_expected = 200
    max_expected = 800
    clamped_val = max(min_expected, min(val, max_expected))
    normalized = (clamped_val - min_expected) / (max_expected - min_expected)

    draw_h = clip_rect.height
    draw_y_start = clip_rect.top
    height_scaled = int(draw_h * (1.0 - normalized))
    gsr_history.append(height_scaled)

    spacing = 4
    max_points = clip_rect.width // spacing
    while len(gsr_history) > max_points:
        gsr_history.pop(0)

    points = []
    start_x = clip_rect.right

    for i, v in enumerate(reversed(gsr_history)):
        px = start_x - (i * spacing)
        py = draw_y_start + v
        points.append((int(px), int(py)))

    # 4. Draw Line
    if len(points) > 1:
        pygame.draw.lines(screen, (color[0] // 3, color[1] // 3, color[2] // 3), False, points, 6)
        pygame.draw.lines(screen, color, False, points, 3)

    # 5. Border
    screen.set_clip(None)
    pygame.draw.rect(screen, color, rect, 3)


def draw_text(text, font, color, x, y, align="center", relative_to_rect=None):
    surf = font.render(text, True, color)
    if relative_to_rect:
        cx, cy = relative_to_rect.center
        rect = surf.get_rect(center=(cx + x, cy + y))
    elif align == "center":
        rect = surf.get_rect(center=(x, y))
    elif align == "left":
        rect = surf.get_rect(topleft=(x, y))
    screen.blit(surf, rect)


def draw_smooth_heart(x, y, scale=3.5, color=COLOR_NEON_P):
    points = []
    for t in range(0, 628, 5):
        t_rad = t / 100.0
        px = 16 * math.sin(t_rad) ** 3
        py = 13 * math.cos(t_rad) - 5 * math.cos(2 * t_rad) - 2 * math.cos(3 * t_rad) - math.cos(4 * t_rad)
        points.append((x + px * scale, y - py * scale))
    pygame.draw.polygon(screen, color, points)


def draw_robot(x, y, size=70):
    pygame.draw.rect(screen, COLOR_NEON_B, (x - 35, y - 35, 70, 70))
    pygame.draw.rect(screen, COLOR_NEON_B, (x - 35, y - 35, 70, 70), 3)
    pygame.draw.rect(screen, COLOR_BG, (x - 25, y - 15, 15, 15))
    pygame.draw.rect(screen, COLOR_BG, (x + 10, y - 15, 15, 15))
    for i in range(3):
        pygame.draw.line(screen, COLOR_BG, (x - 20 + (i * 20), y + 10), (x - 20 + (i * 20), y + 30), 3)
    pygame.draw.line(screen, COLOR_BG, (x - 25, y + 20), (x + 25, y + 20), 3)


# --- GAME STATE ---
class GameState:
    MENU, SETUP, ASSIGN, TELLING, GUESSING, SUSPENSE, WINNER, SCOREBOARD = 0, 1, 2, 3, 4, 5, 6, 7
    current = MENU
    p1_instructions = []
    current_story_idx = 0
    guessing_idx = 0
    p2_choices = []
    gsr_variances = []
    current_gsr_stream = []
    shutdown_timer = 0
    winner_text = ""
    winner_icon = ""

    debounce_end = 0

    # NEW: For Guessing Visual Feedback
    selected_choice = None  # "WAHRHEIT" or "LÜGE"
    feedback_end = 0  # Timer for the highlight animation


game = GameState()


def reset_round():
    game.p1_instructions = ["WAHRHEIT", "WAHRHEIT", "LÜGE"]
    random.shuffle(game.p1_instructions)
    game.current_story_idx = 0
    game.guessing_idx = 0
    game.p2_choices = []
    game.gsr_variances = []
    game.current_gsr_stream = []
    game.selected_choice = None
    game.feedback_end = 0
    global gsr_history
    gsr_history = []


# --- MAIN LOOP ---
clock = pygame.time.Clock()
running = True
start_ticks = pygame.time.get_ticks()

last_gsr_read = 0
current_val = 0

reset_round()
LEFT_C, RIGHT_C = 400, 1200
print("--- SPIEL STARTET ---")

while running:
    current_time = pygame.time.get_ticks()

    # 1. SENSOR
    if current_time - last_gsr_read > 100:
        new_val = get_gsr()
        if new_val is not None:
            current_val = new_val
        last_gsr_read = current_time

    # 2. INPUTS
    pygame.event.pump()
    p1_act = GPIO.input(BTN_P1) == 0
    p2_t = GPIO.input(BTN_P2_T) == 0
    p2_l = GPIO.input(BTN_P2_L) == 0
    btn_off = GPIO.input(BTN_OFF) == 0

    input_allowed = current_time > game.debounce_end

    # 3. SHUTDOWN
    if btn_off:
        game.shutdown_timer += 1
        if game.shutdown_timer > 60:
            screen.blit(static_background, (0, 0))
            panel = pygame.Rect(SCREEN_W // 2 - 200, SCREEN_H // 2 - 100, 400, 200)
            draw_panel(panel, COLOR_RED)
            draw_text("SYSTEM OFF", FONT_XL, COLOR_RED, 0, 0, relative_to_rect=panel)
            pygame.display.flip()
            time.sleep(1)
            subprocess.call(['sudo', 'poweroff'])
            running = False
    else:
        game.shutdown_timer = 0

    # Data Collection
    if current_val is not None and game.current == GameState.TELLING and current_time % 100 < 20:
        game.current_gsr_stream.append(current_val)

    # 4. DRAWING
    screen.blit(static_background, (0, 0))

    if game.current == GameState.MENU:
        draw_text("TRUTH OR TECH", FONT_L, COLOR_NEON_G, LEFT_C, 150)
        btn_rect = pygame.Rect(LEFT_C - 160, 280, 320, 70)
        draw_panel(btn_rect, COLOR_WHITE)
        draw_text("KNOPF DRÜCKEN", FONT_M, COLOR_WHITE, 0, 0, relative_to_rect=btn_rect)

        draw_text("TRUTH OR TECH", FONT_L, COLOR_NEON_B, RIGHT_C, 150)
        draw_text("INITIALISIERUNG...", FONT_M, COLOR_NEON_B, RIGHT_C, 315)

        if p1_act and input_allowed:
            game.current = GameState.SETUP
            game.debounce_end = current_time + 500

    elif game.current == GameState.SETUP:
        draw_text("SCHRITT 1: SETUP", FONT_M, COLOR_NEON_B, LEFT_C, 60)
        draw_text("SENSOREN ANLEGEN", FONT_L, COLOR_WHITE, LEFT_C, 130)
        draw_text("Zeige- & Mittelfinger", FONT_S, COLOR_WHITE, LEFT_C, 180)
        if current_val: draw_waveform(current_val, LEFT_C - 220, 220, 440, 120, COLOR_NEON_G)
        draw_text("Signal-Test", FONT_S, COLOR_NEON_G, LEFT_C, 360)

        btn_rect = pygame.Rect(LEFT_C - 160, 400, 320, 60)
        draw_panel(btn_rect, COLOR_NEON_G)
        draw_text("BESTÄTIGEN", FONT_S, COLOR_NEON_G, 0, 0, relative_to_rect=btn_rect)

        draw_text("WARTE AUF BIO-SIGNAL", FONT_M, COLOR_NEON_B, RIGHT_C, 240)
        if p1_act and input_allowed:
            game.current = GameState.ASSIGN
            game.debounce_end = current_time + 500

    elif game.current == GameState.ASSIGN:
        instr = game.p1_instructions[game.current_story_idx]
        draw_text(f"RUNDE {game.current_story_idx + 1} / 3", FONT_M, COLOR_WHITE, LEFT_C, 60)

        task_panel = pygame.Rect(LEFT_C - 260, 120, 520, 200)
        clr = COLOR_NEON_P if instr == "LÜGE" else COLOR_NEON_G
        draw_panel(task_panel, clr)
        draw_text("DEINE AUFGABE:", FONT_S, COLOR_WHITE, 0, -40, relative_to_rect=task_panel)
        draw_text(instr, FONT_XL, clr, 0, 20, relative_to_rect=task_panel)

        btn_rect = pygame.Rect(LEFT_C - 200, 380, 400, 60)
        draw_panel(btn_rect, COLOR_WHITE)
        draw_text("AUFNAHME STARTEN", FONT_S, COLOR_WHITE, 0, 0, relative_to_rect=btn_rect)

        blind_panel = pygame.Rect(RIGHT_C - 300, 180, 600, 140)
        draw_panel(blind_panel, COLOR_RED)
        draw_text("SIGNAL VERSCHLÜSSELT", FONT_L, COLOR_RED, 0, -20, relative_to_rect=blind_panel)
        draw_text("Gleich gehts los", FONT_S, COLOR_WHITE, 0, 30, relative_to_rect=blind_panel)
        if p1_act and input_allowed:
            game.current = GameState.TELLING
            game.current_gsr_stream = []
            gsr_history = []
            game.debounce_end = current_time + 500

    elif game.current == GameState.TELLING:
        draw_text("AUFNAHME LÄUFT", FONT_M, COLOR_RED, LEFT_C, 60)
        if current_val: draw_waveform(current_val, LEFT_C - 360, 100, 720, 280, COLOR_RED)

        btn_rect = pygame.Rect(LEFT_C - 200, 400, 400, 60)
        draw_panel(btn_rect, COLOR_WHITE)
        draw_text("GESCHICHTE BEENDEN", FONT_S, COLOR_WHITE, 0, 0, relative_to_rect=btn_rect)

        draw_text("FREUND*IN SPRICHT...", FONT_L, COLOR_WHITE, RIGHT_C, 200)
        draw_text("Verhalten analysieren.", FONT_M, COLOR_NEON_B, RIGHT_C, 260)
        if p1_act and input_allowed:
            var = statistics.variance(game.current_gsr_stream) if len(game.current_gsr_stream) > 1 else 0
            game.gsr_variances.append(var)

            game.current_story_idx += 1
            if game.current_story_idx < 3:
                game.current = GameState.ASSIGN
            else:
                game.current = GameState.GUESSING
                game.guessing_idx = 0

            game.debounce_end = current_time + 500

    elif game.current == GameState.GUESSING:
        draw_text("URTEIL ABWARTEN", FONT_L, COLOR_WHITE, LEFT_C, 240)

        draw_text(f"GESCHICHTE {game.guessing_idx + 1}", FONT_M, COLOR_NEON_B, RIGHT_C, 80)
        draw_text("WAR DAS EINE LÜGE?", FONT_L, COLOR_WHITE, RIGHT_C, 160)

        # LOGIC FOR VISUAL FEEDBACK
        is_highlight_active = (game.selected_choice is not None) and (current_time < game.feedback_end)

        # If highlighting is done, move to next step
        if (game.selected_choice is not None) and (not is_highlight_active):
            # Save the choice that was highlighted
            game.p2_choices.append(game.selected_choice)
            game.selected_choice = None  # Reset
            game.guessing_idx += 1

            if game.guessing_idx >= 3:
                game.current = GameState.SUSPENSE
                start_ticks = current_time
            # else: loop continues and updates the UI number

        # If not highlighting, check for new input
        if (not is_highlight_active) and input_allowed:
            if p2_t:
                game.selected_choice = "WAHRHEIT"
                game.feedback_end = current_time + 500  # 500ms Highlight
            elif p2_l:
                game.selected_choice = "LÜGE"
                game.feedback_end = current_time + 500

        # DRAW BUTTONS (Highlight if selected)
        btn_t_rect = pygame.Rect(RIGHT_C - 320, 250, 300, 120)
        highlight_t = (game.selected_choice == "WAHRHEIT")
        draw_panel(btn_t_rect, COLOR_WHITE, highlight=highlight_t)

        # Text color flips if highlighted
        txt_col_t = COLOR_BLACK if highlight_t else COLOR_WHITE
        draw_text("WAHRHEIT", FONT_L, txt_col_t, 0, -20, relative_to_rect=btn_t_rect)
        draw_text("(Weisser Knopf)", FONT_S, txt_col_t, 0, 25, relative_to_rect=btn_t_rect)

        btn_l_rect = pygame.Rect(RIGHT_C + 20, 250, 300, 120)
        highlight_l = (game.selected_choice == "LÜGE")
        draw_panel(btn_l_rect, COLOR_NEON_P, highlight=highlight_l)

        txt_col_l = COLOR_BLACK if highlight_l else COLOR_NEON_P
        draw_text("LÜGE", FONT_L, txt_col_l, 0, -20, relative_to_rect=btn_l_rect)
        draw_text("(Pinker Knopf)", FONT_S, txt_col_l, 0, 25, relative_to_rect=btn_l_rect)

    elif game.current == GameState.SUSPENSE:
        elapsed = (current_time - start_ticks) / 1000
        dots = "." * (int(elapsed * 3) % 4)
        for offset, color in [(LEFT_C, COLOR_NEON_G), (RIGHT_C, COLOR_NEON_B)]:
            draw_text("BIO-DATEN ANALYSE", FONT_M, color, offset, 200)
            draw_text("VERARBEITUNG" + dots, FONT_L, COLOR_WHITE, offset, 260)

        if elapsed > 3.5:
            if game.gsr_variances:
                ai_lie_idx = game.gsr_variances.index(max(game.gsr_variances))
            else:
                ai_lie_idx = 0

            p2_score = 0;
            ai_score = 0
            for i in range(3):
                real = game.p1_instructions[i]
                p2_guess = game.p2_choices[i]
                ai_guess = "LÜGE" if i == ai_lie_idx else "WAHRHEIT"
                if p2_guess == real: p2_score += 1
                if ai_guess == real: ai_score += 1

            if p2_score > ai_score:
                game.winner_text = "FREUNDSCHAFT GEWINNT!"
                game.winner_icon = "HEART"
                color = COLOR_NEON_P
            elif ai_score > p2_score:
                game.winner_text = "COMPUTER GEWINNT!"
                game.winner_icon = "ROBOT"
                color = COLOR_NEON_B
            else:
                game.winner_text = "UNENTSCHIEDEN."
                game.winner_icon = "NONE"
                color = COLOR_WHITE

            game.current = GameState.WINNER
            start_ticks = current_time

    elif game.current == GameState.WINNER:
        elapsed = (current_time - start_ticks) / 1000
        color = COLOR_NEON_P if game.winner_icon == "HEART" else (
            COLOR_NEON_B if game.winner_icon == "ROBOT" else COLOR_WHITE)
        for offset in [LEFT_C, RIGHT_C]:
            draw_text(game.winner_text, FONT_XL, color, offset, 180)
            if game.winner_icon == "HEART":
                draw_smooth_heart(offset, 320, 3.5, color)
            elif game.winner_icon == "ROBOT":
                draw_robot(offset, 320, 120)

        if elapsed > 4:
            game.current = GameState.SCOREBOARD
            start_ticks = current_time

    elif game.current == GameState.SCOREBOARD:
        elapsed = (current_time - start_ticks) / 1000
        if game.gsr_variances:
            ai_lie_idx = game.gsr_variances.index(max(game.gsr_variances))
        else:
            ai_lie_idx = 0

        for offset in [LEFT_C, RIGHT_C]:
            draw_text("MISSIONSBERICHT", FONT_L, COLOR_WHITE, offset, 50)
            panel_rect = pygame.Rect(offset - 380, 100, 760, 300)
            draw_panel(panel_rect, COLOR_NEON_B)

            draw_text("GESCHICHTE", FONT_S, COLOR_NEON_B, -250, -110, relative_to_rect=panel_rect)
            draw_text("FREUND*IN", FONT_S, COLOR_NEON_B, 0, -110, relative_to_rect=panel_rect)
            draw_text("COMPUTER", FONT_S, COLOR_NEON_B, 250, -110, relative_to_rect=panel_rect)

            for i in range(3):
                y_off = -40 + (i * 70)
                real = game.p1_instructions[i]
                p2_guess = game.p2_choices[i]
                ai_guess = "LÜGE" if i == ai_lie_idx else "WAHRHEIT"
                clr_task = COLOR_NEON_P if real == "LÜGE" else COLOR_NEON_G
                draw_text(f"{i + 1}: {real}", FONT_M, clr_task, -250, y_off, relative_to_rect=panel_rect)
                clr_p2 = COLOR_NEON_G if p2_guess == real else COLOR_RED
                draw_text(p2_guess, FONT_M, clr_p2, 0, y_off, relative_to_rect=panel_rect)
                clr_ai = COLOR_NEON_G if ai_guess == real else COLOR_RED
                draw_text(ai_guess, FONT_M, clr_ai, 250, y_off, relative_to_rect=panel_rect)

            countdown = 15 - int(elapsed)
            draw_text(f"NEUSTART IN {countdown}...", FONT_S, (100, 100, 100), offset, 440)
            draw_text("KNOPF DRÜCKEN ZUM ÜBERSPRINGEN", FONT_S, COLOR_WHITE, offset, 465)

        if countdown <= 0 or (p1_act and input_allowed):
            reset_round()
            game.current = GameState.MENU
            game.debounce_end = current_time + 500

    pygame.display.flip()
    clock.tick_busy_loop(30)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        # ESCAPE KEY KILL SWITCH
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

GPIO.cleanup()
pygame.quit()
