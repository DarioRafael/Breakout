# Particle system: explosions, sparks, trails, confetti.
from __future__ import annotations

import math
import random

import pygame

import config as C
from utils import draw_glow


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size",
                 "color", "gravity", "drag", "glow")

    def __init__(self, x, y, vx, vy, life, size, color,
                 gravity=900.0, drag=0.92, glow=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = size
        self.color = color
        self.gravity = gravity
        self.drag = drag
        self.glow = glow


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def __len__(self) -> int:
        return len(self.particles)

    def update(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            d = p.drag ** (dt * 60.0)
            p.vx *= d
            p.vy *= d
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            f = max(0.0, p.life / p.max_life)
            size = max(1, int(p.size * f))
            x, y = int(p.x), int(p.y)
            if p.glow:
                col = (int(p.color[0] * f), int(p.color[1] * f), int(p.color[2] * f))
                draw_glow(surface, (x, y), max(1, size + 1), col)
            if size <= 1:
                surface.fill(p.color, (x, y, 1, 1))
            else:
                surface.fill(p.color, (x - size // 2, y - size // 2, size, size))

    # Emitters
    def burst(self, x, y, color, count=16, speed=120, life=0.55, size=3,
              gravity=320.0, spread=math.tau):
        for _ in range(count):
            ang = random.uniform(0, spread)
            spd = random.uniform(0.2, 1.0) * speed
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                life * random.uniform(0.6, 1.2), random.uniform(0.6, 1.0) * size,
                color, gravity=gravity))

    def block_explosion(self, rect: pygame.Rect, color) -> None:
        cx, cy = rect.center
        self.burst(cx, cy, color, count=16, speed=120, life=0.5, size=3,
                   gravity=320.0)
        for _ in range(5):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(40, 130)
            self.particles.append(Particle(
                cx, cy, math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(0.35, 0.7), random.uniform(1, 2),
                (255, 255, 255), gravity=260.0))

    def spark(self, x, y, color, count=6) -> None:
        self.burst(x, y, color, count=count, speed=90, life=0.28, size=2,
                   gravity=160.0)

    def trail_puff(self, x, y, color) -> None:
        self.particles.append(Particle(
            x + random.uniform(-1, 1), y + random.uniform(-1, 1),
            random.uniform(-8, 8), random.uniform(-8, 8),
            0.35, random.uniform(1, 2), color, gravity=0.0, drag=0.9))

    def confetti(self, color=None) -> None:
        x = random.uniform(0, C.WIDTH)
        col = color or (random.randint(120, 255), random.randint(120, 255),
                        random.randint(120, 255))
        self.particles.append(Particle(
            x, -4, random.uniform(-14, 14), random.uniform(24, 70),
            random.uniform(1.5, 3.0), random.uniform(1, 3), col,
            gravity=46.0, drag=0.99, glow=False))

    def clear(self) -> None:
        self.particles.clear()
