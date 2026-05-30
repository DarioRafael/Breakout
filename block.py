"""Destructible and unbreakable bricks.

Brick sprites are comparatively expensive to draw (gradient + bevel + cracks)
so each unique appearance is rendered once and cached.
"""
from __future__ import annotations

import random

import pygame

import config as C
from utils import darken, draw_glow, lighten

# Cache: (w, h, color, hp, max_hp, unbreakable) -> Surface
_surface_cache: dict[tuple, pygame.Surface] = {}


def _build_surface(w: int, h: int, color, hp: int, max_hp: int,
                   unbreakable: bool) -> pygame.Surface:
    """Render a single chunky pixel brick (hard edges, bevel, dither damage)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)

    if unbreakable:
        base = (104, 110, 130)
        top = lighten(base, 0.32)
        bottom = darken(base, 0.34)
        outline = (52, 56, 72)
    else:
        # Darken the brick as it loses health for clear damage feedback.
        damage = 0 if max_hp <= 1 else (max_hp - hp) / (max_hp - 1)
        shade = 0.42 * damage
        base = darken(color, shade)
        top = lighten(base, 0.42)
        bottom = darken(base, 0.34)
        outline = C.OUTLINE

    # Flat body.
    surf.fill(base)
    # 1px bevel: bright top + left, dark bottom + right.
    surf.fill(top, (0, 0, w, 1))
    surf.fill(top, (0, 0, 1, h))
    surf.fill(bottom, (0, h - 1, w, 1))
    surf.fill(bottom, (w - 1, 0, 1, h))
    # Hard outline, with the corner pixels cut for a rounded-pixel silhouette.
    pygame.draw.rect(surf, outline, surf.get_rect(), width=1)
    for cx, cy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        surf.fill((0, 0, 0, 0), (cx, cy, 1, 1))

    if unbreakable:
        # Rivets in each corner to signal "indestructible".
        for rx, ry in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
            surf.fill((60, 64, 82), (rx, ry, 1, 1))
            surf.fill(lighten(base, 0.5), (rx, ry - 0 if ry < 3 else ry, 1, 1))
    elif hp < max_hp:
        # Deterministic dither "cracks" — scattered dark pixels.
        rng = random.Random(hash((w, h, hp, max_hp)) & 0xFFFFFFFF)
        dots = (max_hp - hp) * max(2, (w * h) // 30)
        crack = darken(base, 0.5)
        for _ in range(dots):
            x = rng.randint(2, w - 3)
            y = rng.randint(2, h - 3)
            surf.fill(crack, (x, y, 1, 1))
    return surf


class Block:
    __slots__ = ("col", "row", "rect", "color", "hp", "max_hp",
                 "unbreakable", "hit_flash")

    def __init__(self, col: int, row: int, rect: pygame.Rect, color,
                 hp: int = 1, unbreakable: bool = False):
        self.col = col
        self.row = row
        self.rect = rect
        self.color = color
        self.hp = hp
        self.max_hp = hp
        self.unbreakable = unbreakable
        self.hit_flash = 0.0

    @property
    def breakable(self) -> bool:
        return not self.unbreakable

    @property
    def center(self):
        return self.rect.center

    def hit(self) -> bool:
        """Apply one hit. Returns True if the brick was destroyed."""
        self.hit_flash = 1.0
        if self.unbreakable:
            return False
        self.hp -= 1
        return self.hp <= 0

    def update(self, dt: float) -> None:
        if self.hit_flash > 0.0:
            self.hit_flash = max(0.0, self.hit_flash - dt * 5.0)

    def draw(self, surface: pygame.Surface) -> None:
        key = (self.rect.width, self.rect.height, self.color,
               self.hp, self.max_hp, self.unbreakable)
        sprite = _surface_cache.get(key)
        if sprite is None:
            sprite = _build_surface(*key)
            _surface_cache[key] = sprite
        surface.blit(sprite, self.rect.topleft)

        if self.hit_flash > 0.0:
            glow_col = C.WHITE if self.unbreakable else lighten(self.color, 0.3)
            draw_glow(surface, self.rect.center,
                      int(self.rect.height * (0.6 + self.hit_flash)), glow_col)
            flash = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            a = int(150 * self.hit_flash)
            flash.fill((255, 255, 255, a))
            surface.blit(flash, self.rect.topleft)
