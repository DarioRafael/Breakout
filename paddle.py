"""The player paddle: keyboard + mouse control, smooth resize, neon look."""
from __future__ import annotations

import math

import pygame

import config as C
from utils import clamp, darken, draw_glow, lighten, move_toward


class Paddle:
    def __init__(self):
        self.width = float(C.PADDLE_WIDTH)
        self.target_width = float(C.PADDLE_WIDTH)
        self.height = C.PADDLE_HEIGHT
        self.x = C.WIDTH / 2.0                          # centre x
        self.y = C.HEIGHT - C.PADDLE_Y_OFFSET          # centre y
        self.color = C.PADDLE_COLOR
        self.reversed = False                          # REVERSE power-down
        self._flash = 0.0                              # brief glow on ball hit

    # ------------------------------------------------------------------ #
    #  Geometry
    # ------------------------------------------------------------------ #
    @property
    def left(self) -> float:
        return self.x - self.width / 2.0

    @property
    def right(self) -> float:
        return self.x + self.width / 2.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - self.width / 2), int(self.y - self.height / 2),
                           int(self.width), self.height)

    def set_width(self, width: float) -> None:
        self.target_width = clamp(width, C.PADDLE_WIDTH_SHRINK, C.PADDLE_WIDTH_EXPAND)

    def offset_for(self, x: float) -> float:
        """Return the normalised [-1, 1] hit offset for a world x position."""
        return clamp((x - self.x) / (self.width / 2.0), -1.0, 1.0)

    def flash(self) -> None:
        self._flash = 1.0

    # ------------------------------------------------------------------ #
    #  Update
    # ------------------------------------------------------------------ #
    def update(self, dt: float, keys, mouse_x, use_mouse: bool) -> None:
        # Smoothly animate width changes from power-ups.
        self.width = move_toward(self.width, self.target_width, C.PADDLE_RESIZE_SPEED * dt)

        direction = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction += 1
        if self.reversed:
            direction = -direction

        if direction != 0:
            self.x += direction * C.PADDLE_SPEED * dt
        elif use_mouse and mouse_x is not None:
            target = mouse_x
            if self.reversed:
                target = C.WIDTH - mouse_x
            # Exponential smoothing toward the cursor for a fluid feel.
            f = 1.0 - math.exp(-C.PADDLE_MOUSE_SMOOTH * dt)
            self.x += (target - self.x) * f

        half = self.width / 2.0
        self.x = clamp(self.x, half, C.WIDTH - half)

        if self._flash > 0.0:
            self._flash = max(0.0, self._flash - dt * 3.5)

    # ------------------------------------------------------------------ #
    #  Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, laser_active: bool, t: float) -> None:
        rect = self.rect
        col = C.NEON_YELLOW if laser_active else self.color

        glow_r = int(self.height + 3 + self._flash * 7)
        draw_glow(surface, (rect.centerx, rect.centery), glow_r,
                  lighten(col, 0.1 + 0.25 * self._flash))

        # Hard pixel body: dark outline, bright top row, body, shadow row.
        body = lighten(col, 0.05)
        top = lighten(col, 0.45)
        bottom = darken(col, 0.4)
        surface.fill(C.OUTLINE, rect)
        inner = rect.inflate(-2, 0)
        surface.fill(body, inner)
        surface.fill(top, (inner.left, inner.top, inner.width, 1))            # top highlight
        surface.fill(bottom, (inner.left, inner.bottom - 1, inner.width, 1))  # bottom shadow
        # Bevelled end caps (clip the very corners for a rounded pixel feel).
        for cx in (rect.left, rect.right - 1):
            surface.fill(C.OUTLINE, (cx, rect.top, 1, 1))
            surface.fill(C.OUTLINE, (cx, rect.bottom - 1, 1, 1))
        # Bright glint pixels along the core.
        gy = rect.centery - 1
        for gx in range(inner.left + 2, inner.right - 2, 4):
            surface.fill(C.WHITE, (gx, gy, 1, 1))

        if laser_active:
            for sx in (rect.left + 3, rect.right - 4):
                surface.fill(C.NEON_ORANGE, (int(sx), rect.top - 3, 2, 4))
                surface.fill(C.WHITE, (int(sx), rect.top - 3, 1, 1))
                draw_glow(surface, (sx + 1, rect.top - 2), 4, C.NEON_ORANGE)
