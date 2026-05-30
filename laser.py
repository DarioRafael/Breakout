"""Paddle laser bolts."""
from __future__ import annotations

import pygame

import config as C
from utils import draw_glow


class Laser:
    __slots__ = ("x", "y", "dead")

    def __init__(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)
        self.dead = False

    def update(self, dt: float) -> None:
        self.y -= C.LASER_SPEED * dt
        if self.y < -20:
            self.dead = True

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 1), int(self.y - 4), 2, 8)

    def draw(self, surface: pygame.Surface) -> None:
        draw_glow(surface, (self.x, self.y), 4, C.NEON_ORANGE)
        surface.fill(C.NEON_YELLOW, self.rect)
        surface.fill(C.WHITE, (int(self.x), int(self.y - 4), 1, 8))
