"""The Ball entity.

The ball is modelled as a unit *direction* plus a scalar *speed*.  Keeping
them separate makes the SLOW / FAST power-ups trivial (just change ``speed``)
while reflections only ever touch the direction.
"""
from __future__ import annotations

import math
import random

import pygame

import config as C
from utils import clamp, draw_glow, normalize, scale_color


class Ball:
    def __init__(self, x: float, y: float, speed: float,
                 dir_x: float = 0.0, dir_y: float = -1.0, color=C.BALL_COLOR):
        self.x = float(x)
        self.y = float(y)
        self.radius = C.BALL_RADIUS
        self.speed = float(speed)
        self.color = color
        self.dir_x, self.dir_y = normalize(dir_x, dir_y)
        self._enforce_min_y()

        # When stuck the ball rides the paddle until launched (serve / CATCH).
        self.stuck = True
        self.stuck_offset = 0.0
        self.pierce = False           # set by PlayState while PIERCE is active
        self.trail: list[tuple[float, float]] = []
        self._spin = random.uniform(0, math.tau)

    # ------------------------------------------------------------------ #
    #  Direction helpers
    # ------------------------------------------------------------------ #
    def _enforce_min_y(self) -> None:
        """Stop the ball settling into a near-horizontal rut."""
        if abs(self.dir_y) < C.BALL_MIN_DIR_Y:
            sy = -1.0 if self.dir_y <= 0 else 1.0
            self.dir_y = C.BALL_MIN_DIR_Y * sy
            sx = 1.0 if self.dir_x >= 0 else -1.0
            if abs(self.dir_x) < 1e-6:
                sx = random.choice((-1.0, 1.0))
            self.dir_x = sx * math.sqrt(max(0.0, 1.0 - C.BALL_MIN_DIR_Y ** 2))
        self.dir_x, self.dir_y = normalize(self.dir_x, self.dir_y)

    def set_direction(self, dx: float, dy: float) -> None:
        self.dir_x, self.dir_y = normalize(dx, dy)
        self._enforce_min_y()

    def reflect(self, nx: float, ny: float) -> None:
        """Reflect the direction about the surface normal (nx, ny)."""
        dot = self.dir_x * nx + self.dir_y * ny
        self.dir_x -= 2.0 * dot * nx
        self.dir_y -= 2.0 * dot * ny
        self._enforce_min_y()

    def launch_from_paddle(self, offset: float) -> None:
        """Send the ball upward at an angle set by where it left the paddle.

        *offset* is in [-1, 1] (left edge .. right edge).
        """
        angle = math.radians(C.PADDLE_MAX_BOUNCE_ANGLE) * clamp(offset, -1.0, 1.0)
        self.dir_x = math.sin(angle)
        self.dir_y = -math.cos(angle)
        self._enforce_min_y()
        self.stuck = False

    # ------------------------------------------------------------------ #
    #  Movement & rendering
    # ------------------------------------------------------------------ #
    @property
    def vx(self) -> float:
        return self.dir_x * self.speed

    @property
    def vy(self) -> float:
        return self.dir_y * self.speed

    def step(self, dt: float) -> None:
        """Advance the position by one (sub-)step of *dt* seconds."""
        self.x += self.dir_x * self.speed * dt
        self.y += self.dir_y * self.speed * dt

    def push_trail(self) -> None:
        self.trail.append((self.x, self.y))
        if len(self.trail) > C.BALL_TRAIL_LEN:
            self.trail.pop(0)

    @property
    def rect(self) -> pygame.Rect:
        r = self.radius
        return pygame.Rect(int(self.x - r), int(self.y - r), r * 2, r * 2)

    def draw(self, surface: pygame.Surface, t: float) -> None:
        glow_col = C.NEON_PURPLE if self.pierce else self.color

        # Fading motion trail as little additive blooms + hard pixels.
        n = len(self.trail)
        for i, (tx, ty) in enumerate(self.trail):
            f = (i + 1) / max(1, n)
            draw_glow(surface, (tx, ty), max(1, int(self.radius * (0.4 + 0.7 * f))),
                      (int(glow_col[0] * 0.16 * f),
                       int(glow_col[1] * 0.16 * f),
                       int(glow_col[2] * 0.18 * f)))
            if i >= n - 3:
                surface.fill(scale_color(glow_col, 0.5 * f), (int(tx), int(ty), 1, 1))

        # Soft pixel halo, then the crisp ball.
        draw_glow(surface, (self.x, self.y), self.radius * 2, glow_col)
        cx, cy = int(round(self.x)), int(round(self.y))
        pygame.draw.circle(surface, C.OUTLINE, (cx, cy), self.radius + 1)
        pygame.draw.circle(surface, glow_col, (cx, cy), self.radius)
        # Single-pixel specular highlight.
        surface.fill(C.WHITE, (cx - 1, cy - 1, 1, 1))
