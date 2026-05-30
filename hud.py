# Heads-up display: top bar, hearts, combo, effect chips.
from __future__ import annotations

import pygame

import config as C
from powerup import POWERUP_TYPES
from utils import clamp, darken, draw_text, scale_color

# Heart sprite ('#' = lit)
_HEART = [
    ".##.##.",
    "#######",
    "#######",
    ".#####.",
    "..###..",
    "...#...",
]


def _draw_heart(surface, x, y, color, filled=True):
    col = color if filled else darken(color, 0.62)
    for ry, row in enumerate(_HEART):
        for cx, c in enumerate(row):
            if c == "#":
                surface.fill(col, (x + cx, y + ry, 1, 1))
    if not filled:
        for ry, row in enumerate(_HEART):
            for cx, c in enumerate(row):
                if c == "#" and 1 <= cx <= 5 and 1 <= ry <= 3:
                    surface.fill(C.OUTLINE, (x + cx, y + ry, 1, 1))


class HUD:
    def draw(self, surface, score, high, lives, level, level_name,
             combo, effects, t):
        # Top bar
        surface.fill(C.UI_BG, (0, 0, C.WIDTH, C.HUD_HEIGHT))
        surface.fill(darken(C.UI_BG, 0.4), (0, 0, C.WIDTH, 1))
        surface.fill(C.NEON_BLUE, (0, C.HUD_HEIGHT - 1, C.WIDTH, 1))

        # Score (left)
        draw_text(surface, "SCORE", 1, C.GREY, topleft=(5, 4))
        draw_text(surface, f"{score:,}", 2, C.WHITE, topleft=(5, 12))

        # Best + level (centre)
        draw_text(surface, "BEST", 1, C.GREY, midtop=(C.WIDTH // 2, 4))
        best = max(score, high)
        bc = C.NEON_YELLOW if (score >= high and high > 0) else C.WHITE
        draw_text(surface, f"{best:,}", 1, bc, midtop=(C.WIDTH // 2, 13))
        draw_text(surface, f"LV {level}", 1, C.NEON_PURPLE, midtop=(C.WIDTH // 2, 21))

        # Lives (right)
        draw_text(surface, "LIVES", 1, C.GREY, topright=(C.WIDTH - 5, 4))
        hx = C.WIDTH - 5 - 7
        slots = max(C.START_LIVES, max(lives, 0))
        for i in range(slots):
            _draw_heart(surface, hx, 13, C.NEON_PINK, filled=(i < lives))
            hx -= 9

        # Combo (below the bar)
        if combo >= 2:
            col = C.NEON_ORANGE if int(t * 12) % 2 == 0 else C.NEON_YELLOW
            draw_text(surface, f"COMBO X{combo}", 1, col,
                      topleft=(5, C.HUD_HEIGHT + 1))

        self._draw_effects(surface, effects, t)

    def _draw_effects(self, surface, effects, t):
        if not effects:
            return
        chip_w = 46
        x = 4
        y = C.HEIGHT - 9
        for kind, remaining in effects:
            meta = POWERUP_TYPES.get(kind)
            if meta is None:
                continue
            total = C.EFFECT_DURATION.get(kind, 1.0)
            frac = clamp(remaining / total, 0.0, 1.0)
            color = meta["color"]
            chip = pygame.Rect(x, y, chip_w, 8)

            surface.fill(C.OUTLINE, chip.inflate(2, 2))
            surface.fill(darken(C.UI_BG, 0.2), chip)
            surface.fill(scale_color(color, 0.5),
                         (chip.left, chip.top, int(chip_w * frac), chip.height))
            pygame.draw.rect(surface, color, chip, width=1)

            label_col = C.WHITE
            if remaining < 3.0 and int(t * 6) % 2 == 0:
                label_col = color
            draw_text(surface, f"{meta['letter']}:{meta['label'][:5]}", 1, label_col,
                      midleft=(chip.left + 2, chip.centery))
            x += chip_w + 4
            if x > C.WIDTH - chip_w:
                x = 4
                y -= 11
