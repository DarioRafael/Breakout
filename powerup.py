"""Falling power-up / power-down capsules and their metadata."""
from __future__ import annotations

import math
import random

import pygame

import config as C
from utils import darken, draw_glow, draw_text, lighten

# Metadata for every capsule type.
#   bad   -> harmful (power-down), drawn with a warning style
#   timed -> effect has a duration tracked in PlayState
POWERUP_TYPES: dict[str, dict] = {
    "MULTI":   {"label": "Multi-Ball", "letter": "M", "color": C.NEON_CYAN,   "bad": False, "timed": False},
    "EXPAND":  {"label": "Expand",     "letter": "E", "color": C.NEON_GREEN,  "bad": False, "timed": True},
    "SHRINK":  {"label": "Shrink",     "letter": "K", "color": C.NEON_RED,    "bad": True,  "timed": True},
    "SLOW":    {"label": "Slow Ball",  "letter": "S", "color": C.NEON_BLUE,   "bad": False, "timed": True},
    "FAST":    {"label": "Fast Ball",  "letter": "F", "color": C.NEON_ORANGE, "bad": True,  "timed": True},
    "LASER":   {"label": "Laser",      "letter": "L", "color": C.NEON_YELLOW, "bad": False, "timed": True},
    "LIFE":    {"label": "1-Up",       "letter": "+", "color": C.NEON_PINK,   "bad": False, "timed": False},
    "PIERCE":  {"label": "Pierce",     "letter": "P", "color": C.NEON_PURPLE, "bad": False, "timed": True},
    "CATCH":   {"label": "Catch",      "letter": "C", "color": C.NEON_GREEN,  "bad": False, "timed": True},
    "REVERSE": {"label": "Reverse",    "letter": "R", "color": C.NEON_RED,    "bad": True,  "timed": True},
}

_GOOD_WEIGHTS = {
    "MULTI": 5, "EXPAND": 4, "SLOW": 3, "LASER": 4,
    "PIERCE": 3, "CATCH": 3, "LIFE": 1,
}
_BAD_WEIGHTS = {"SHRINK": 3, "FAST": 3, "REVERSE": 2}


def choose_powerup_type() -> str:
    """Weighted random capsule type, occasionally a harmful one."""
    table = _BAD_WEIGHTS if random.random() < C.POWERDOWN_RATIO else _GOOD_WEIGHTS
    keys = list(table.keys())
    weights = list(table.values())
    return random.choices(keys, weights=weights, k=1)[0]


class PowerUp:
    def __init__(self, x: float, y: float, kind: str):
        self.kind = kind
        self.meta = POWERUP_TYPES[kind]
        self.size = C.POWERUP_SIZE
        self.x = float(x)
        self.y = float(y)
        self.vy = C.POWERUP_FALL_SPEED
        self.t = 0.0
        self.dead = False

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        return pygame.Rect(int(self.x - s / 2), int(self.y - s / 2), s, s)

    def update(self, dt: float) -> None:
        self.t += dt
        self.y += self.vy * dt
        if self.y - self.size > C.HEIGHT:
            self.dead = True

    def draw(self, surface: pygame.Surface) -> None:
        color = self.meta["color"]
        bad = self.meta["bad"]
        pulse = 0.5 + 0.5 * math.sin(self.t * 7.0)
        draw_glow(surface, (self.x, self.y), int(self.size * (0.55 + 0.25 * pulse)), color)

        rect = self.rect
        base = color
        top = lighten(color, 0.4)
        bottom = darken(color, 0.4)
        # Pixel capsule: outline, body, bevel.
        surface.fill(C.OUTLINE, rect)
        inner = rect.inflate(-2, -2)
        surface.fill(base, inner)
        surface.fill(top, (inner.left, inner.top, inner.width, 1))
        surface.fill(top, (inner.left, inner.top, 1, inner.height))
        surface.fill(bottom, (inner.left, inner.bottom - 1, inner.width, 1))
        surface.fill(bottom, (inner.right - 1, inner.top, 1, inner.height))
        # Cut corners for a rounded-pixel look.
        for cx, cy in ((rect.left, rect.top), (rect.right - 1, rect.top),
                       (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1)):
            surface.fill((0, 0, 0, 0), (cx, cy, 1, 1))

        if bad:
            # A blinking warning frame so power-downs read as risky.
            if int(self.t * 6) % 2 == 0:
                pygame.draw.rect(surface, C.WHITE, inner, width=1)

        draw_text(surface, self.meta["letter"], 1,
                  C.OUTLINE if not bad else C.WHITE, center=rect.center)
