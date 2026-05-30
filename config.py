"""Central configuration for Breakout — Neon Pixel Edition.

The whole game is authored in a small *virtual* resolution (320x240) and then
scaled up with nearest-neighbour to the window, giving a crisp, chunky pixel-art
look.  Every coordinate, size and speed below is expressed in **virtual pixels**.

Nothing here imports pygame, so it's safe to import anywhere.
"""

# --------------------------------------------------------------------------- #
#  Resolution / scaling
# --------------------------------------------------------------------------- #
TITLE = "BREAKOUT — Neon Pixel Edition"

VIRTUAL_WIDTH = 320            # the low-res canvas everything is drawn on
VIRTUAL_HEIGHT = 240
PIXEL_SCALE = 3               # integer upscale factor -> 960x720 window

# Logical play-field == virtual canvas (all gameplay maths use these).
WIDTH = VIRTUAL_WIDTH
HEIGHT = VIRTUAL_HEIGHT

# Actual window size.
WINDOW_WIDTH = VIRTUAL_WIDTH * PIXEL_SCALE
WINDOW_HEIGHT = VIRTUAL_HEIGHT * PIXEL_SCALE

FPS = 120                     # render cap; physics is delta-time based
HUD_HEIGHT = 28               # reserved space at the top for the HUD bar

MAX_DT = 1 / 30.0             # clamp delta-time so lag spikes can't tunnel the ball
BALL_SUBSTEP_PX = 2           # ball never advances more than this between checks

# CRT / pixel post-processing.
CRT_ENABLED = True
CRT_SCANLINE_ALPHA = 42       # darkness of every scaled scanline (0-255)
CRT_VIGNETTE_ALPHA = 60       # corner darkening strength

# --------------------------------------------------------------------------- #
#  Palette  (cohesive, limited neon set)
# --------------------------------------------------------------------------- #
BLACK = (10, 8, 20)
WHITE = (238, 244, 255)
GREY = (120, 130, 158)
DARK = (24, 22, 44)
OUTLINE = (12, 10, 22)         # near-black used for pixel outlines/shadows
UI_BG = (20, 18, 40)

BG_TOP = (28, 18, 58)
BG_MID = (14, 12, 38)
BG_BOTTOM = (6, 6, 18)

NEON_BLUE = (40, 190, 255)
NEON_PINK = (255, 70, 165)
NEON_GREEN = (90, 255, 150)
NEON_YELLOW = (255, 220, 70)
NEON_PURPLE = (185, 110, 255)
NEON_ORANGE = (255, 145, 55)
NEON_RED = (255, 80, 80)
NEON_CYAN = (70, 255, 230)

# --------------------------------------------------------------------------- #
#  Paddle
# --------------------------------------------------------------------------- #
PADDLE_WIDTH = 44
PADDLE_HEIGHT = 6
PADDLE_Y_OFFSET = 18           # distance of paddle centre from bottom edge
PADDLE_SPEED = 260             # px/s for keyboard control
PADDLE_WIDTH_EXPAND = 68
PADDLE_WIDTH_SHRINK = 26
PADDLE_RESIZE_SPEED = 210      # px/s the paddle visually grows/shrinks
PADDLE_MOUSE_SMOOTH = 24.0     # higher = snappier mouse following
PADDLE_MAX_BOUNCE_ANGLE = 60   # degrees away from vertical at the paddle edge
PADDLE_COLOR = NEON_BLUE

# --------------------------------------------------------------------------- #
#  Ball
# --------------------------------------------------------------------------- #
BALL_RADIUS = 3
BALL_BASE_SPEED = 122.0
BALL_SPEED_PER_LEVEL = 5.0
BALL_MAX_SPEED = 256.0
BALL_MIN_DIR_Y = 0.30          # keep the ball from getting stuck near-horizontal
BALL_TRAIL_LEN = 10
MAX_BALLS = 14
BALL_COLOR = WHITE

SLOW_MULT = 0.62               # SLOW power-up speed multiplier
FAST_MULT = 1.45               # FAST power-down speed multiplier

# --------------------------------------------------------------------------- #
#  Blocks
# --------------------------------------------------------------------------- #
BLOCK_COLS = 11
BLOCK_ROWS_MAX = 9
BLOCK_GAP = 2
BLOCK_TOP_MARGIN = HUD_HEIGHT + 8
BLOCK_SIDE_MARGIN = 10
BLOCK_HEIGHT = 9
BLOCK_MAX_HP = 5

# --------------------------------------------------------------------------- #
#  Lives & scoring
# --------------------------------------------------------------------------- #
START_LIVES = 3
MAX_LIVES = 6
SCORE_PER_HIT = 10             # awarded per brick hit (even if not destroyed)
SCORE_PER_BLOCK = 100          # awarded when a brick is destroyed
COMBO_STEP = 25                # extra points per combo level
LEVEL_CLEAR_BONUS = 1000

# --------------------------------------------------------------------------- #
#  Power-ups
# --------------------------------------------------------------------------- #
POWERUP_DROP_CHANCE = 0.23     # chance a destroyed brick drops a capsule
POWERUP_FALL_SPEED = 62
POWERUP_SIZE = 11
POWERDOWN_RATIO = 0.27         # fraction of drops that are harmful

# Duration (seconds) of timed effects.
EFFECT_DURATION = {
    "EXPAND": 16.0,
    "SHRINK": 12.0,
    "SLOW": 15.0,
    "FAST": 12.0,
    "LASER": 15.0,
    "PIERCE": 9.0,
    "CATCH": 16.0,
    "REVERSE": 10.0,
}

LASER_COOLDOWN = 0.26          # seconds between laser volleys
LASER_SPEED = 280

# --------------------------------------------------------------------------- #
#  Progression / misc
# --------------------------------------------------------------------------- #
MAX_LEVEL = 50                 # reaching this triggers the Victory screen
HIGHSCORE_FILE = "highscore.json"

# Screen-shake trauma added by various events (0..1, accumulates, decays).
SHAKE_BLOCK = 0.18
SHAKE_HARD = 0.10
SHAKE_LIFE = 0.6
SHAKE_LEVEL = 0.4
SHAKE_MAX_PIXELS = 5           # max shake displacement in *virtual* pixels
