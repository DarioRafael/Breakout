# Procedural level generator: shape patterns + HP + colors scaling by level.
from __future__ import annotations

import math
import random

import pygame

import config as C
from block import Block
from utils import clamp, hsv


# Patterns: return a 2D 0/1 mask
def _grid(rows: int, cols: int, value: int = 0):
    return [[value] * cols for _ in range(rows)]


def _p_solid(rng, rows, cols, level):
    return _grid(rows, cols, 1)


def _p_rows_gaps(rng, rows, cols, level):
    g = _grid(rows, cols, 1)
    holes = rng.sample(range(cols), k=rng.randint(1, max(1, cols // 4)))
    for r in range(rows):
        for h in holes:
            if rng.random() < 0.6:
                g[r][h] = 0
    return g


def _p_checker(rng, rows, cols, level):
    g = _grid(rows, cols)
    parity = rng.randint(0, 1)
    for r in range(rows):
        for c in range(cols):
            if (r + c) % 2 == parity:
                g[r][c] = 1
    return g


def _p_pyramid(rng, rows, cols, level):
    g = _grid(rows, cols)
    centre = cols / 2.0
    invert = rng.random() < 0.5
    for r in range(rows):
        reach = (r + 1) if not invert else (rows - r)
        for c in range(cols):
            if abs(c + 0.5 - centre) <= reach:
                g[r][c] = 1
    return g


def _p_diamond(rng, rows, cols, level):
    g = _grid(rows, cols)
    cc = cols / 2.0
    rc = rows / 2.0
    radius = max(cc, rc) * 0.85
    for r in range(rows):
        for c in range(cols):
            if abs(c + 0.5 - cc) + abs(r + 0.5 - rc) <= radius:
                g[r][c] = 1
    return g


def _p_columns(rng, rows, cols, level):
    g = _grid(rows, cols)
    parity = rng.randint(0, 1)
    for c in range(cols):
        if c % 2 == parity:
            for r in range(rows):
                g[r][c] = 1
    return g


def _p_waves(rng, rows, cols, level):
    g = _grid(rows, cols)
    phase = rng.uniform(0, math.tau)
    freq = rng.uniform(0.4, 0.9)
    thickness = max(2, rows // 2)
    for c in range(cols):
        mid = (rows - 1) / 2.0 + math.sin(phase + c * freq) * (rows / 2.5)
        for r in range(rows):
            if abs(r - mid) <= thickness / 2.0:
                g[r][c] = 1
    return g


def _p_clusters(rng, rows, cols, level):
    g = _grid(rows, cols)
    seeds = rng.randint(3, 6)
    for _ in range(seeds):
        sr = rng.randint(0, rows - 1)
        sc = rng.randint(0, cols - 1)
        rad = rng.randint(1, 2)
        for r in range(max(0, sr - rad), min(rows, sr + rad + 1)):
            for c in range(max(0, sc - rad), min(cols, sc + rad + 1)):
                if abs(r - sr) + abs(c - sc) <= rad:
                    g[r][c] = 1
    return g


def _p_random(rng, rows, cols, level):
    g = _grid(rows, cols)
    p = rng.uniform(0.55, 0.8)
    for r in range(rows):
        for c in range(cols):
            g[r][c] = 1 if rng.random() < p else 0
    return g


def _p_border(rng, rows, cols, level):
    g = _grid(rows, cols)
    for r in range(rows):
        for c in range(cols):
            if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:
                g[r][c] = 1
    if rows >= 5 and rng.random() < 0.6:
        mid = rows // 2
        for c in range(1, cols - 1):
            g[mid][c] = 1
    return g


_EASY_PATTERNS = [_p_solid, _p_rows_gaps, _p_pyramid, _p_columns]
_ALL_PATTERNS = [
    _p_solid, _p_rows_gaps, _p_checker, _p_pyramid, _p_diamond,
    _p_columns, _p_waves, _p_clusters, _p_random, _p_border,
]
_PATTERN_NAMES = {
    _p_solid: "Solid Wall", _p_rows_gaps: "Broken Ranks", _p_checker: "Checkerboard",
    _p_pyramid: "Pyramid", _p_diamond: "Diamond", _p_columns: "Columns",
    _p_waves: "Waveform", _p_clusters: "Asteroids", _p_random: "Chaos",
    _p_border: "Fortress",
}


def _roll_hp(rng, max_tier: int, row: int, rows: int) -> int:
    # bias toward low HP; top rows a little tougher
    if max_tier <= 1:
        return 1
    base = (rng.random() ** 1.6)
    top_bonus = 0.22 * (rows - 1 - row) / max(1, rows - 1)
    hp = 1 + int(round((max_tier - 1) * clamp(base + top_bonus, 0.0, 1.0)))
    return int(clamp(hp, 1, max_tier))


def generate_level(level: int, seed: int | None = None):
    # returns (blocks, pattern_name)
    rng = random.Random(seed)

    cols = C.BLOCK_COLS
    rows = int(clamp(4 + level // 2, 4, C.BLOCK_ROWS_MAX))
    max_hp_tier = int(clamp(1 + level // 3, 1, C.BLOCK_MAX_HP))
    unbreak_chance = clamp(0.02 * (level - 1), 0.0, 0.14) if level >= 3 else 0.0

    patterns = _EASY_PATTERNS if level <= 2 else _ALL_PATTERNS
    pattern_fn = rng.choice(patterns)
    grid = pattern_fn(rng, rows, cols, level)

    if sum(sum(r) for r in grid) < cols:
        grid = _p_solid(rng, rows, cols, level)
        pattern_fn = _p_solid

    usable_w = C.WIDTH - 2 * C.BLOCK_SIDE_MARGIN
    block_w = (usable_w - (cols - 1) * C.BLOCK_GAP) / cols
    block_h = C.BLOCK_HEIGHT
    x0 = C.BLOCK_SIDE_MARGIN
    y0 = C.BLOCK_TOP_MARGIN

    base_hue = rng.uniform(0, 360)
    hue_step = rng.choice([14, 20, 26, 32, -20, -28])

    blocks: list[Block] = []
    breakable_count = 0
    for r in range(rows):
        for c in range(cols):
            if not grid[r][c]:
                continue
            rect = pygame.Rect(
                int(round(x0 + c * (block_w + C.BLOCK_GAP))),
                int(round(y0 + r * (block_h + C.BLOCK_GAP))),
                int(round(block_w)), block_h)

            if unbreak_chance and rng.random() < unbreak_chance:
                blocks.append(Block(c, r, rect, (96, 102, 120), hp=1, unbreakable=True))
                continue

            hp = _roll_hp(rng, max_hp_tier, r, rows)
            hue = base_hue + r * hue_step + c * 3.0
            sat = 0.78 + 0.04 * (hp - 1)
            val = 1.0 - 0.06 * (hp - 1)
            color = hsv(hue, clamp(sat, 0, 1), clamp(val, 0.6, 1.0))
            blocks.append(Block(c, r, rect, color, hp=hp))
            breakable_count += 1

    # ensure clearable
    if breakable_count == 0 and blocks:
        b = blocks[0]
        b.unbreakable = False
        b.hp = b.max_hp = 1
        b.color = hsv(base_hue, 0.8, 1.0)

    return blocks, _PATTERN_NAMES.get(pattern_fn, "Stage")
