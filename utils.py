"""Reusable helpers: math, easing, colour, and **pixel-art** text / bloom.

Text uses the hand-built bitmap font in :mod:`pixelfont`; "size" everywhere is
expressed as an integer *pixel scale* (1 = the 5x7 base font, 2 = doubled, ...).
Glows are hard-stepped pixel blooms (no smooth gradients) so they fit the look.
"""
from __future__ import annotations

import colorsys
import math

import pygame

import config as C
import pixelfont

# --------------------------------------------------------------------------- #
#  Maths / easing
# --------------------------------------------------------------------------- #
def clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def move_toward(current: float, target: float, max_delta: float) -> float:
    if abs(target - current) <= max_delta:
        return target
    return current + math.copysign(max_delta, target - current)


def length(x: float, y: float) -> float:
    return math.hypot(x, y)


def normalize(x: float, y: float) -> tuple[float, float]:
    d = math.hypot(x, y)
    if d == 0.0:
        return 0.0, 0.0
    return x / d, y / d


def ease_out_cubic(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3


def ease_in_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_out_back(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    c1, c3 = 1.70158, 2.70158
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


# --------------------------------------------------------------------------- #
#  Colour
# --------------------------------------------------------------------------- #
def clamp_color(c) -> tuple[int, int, int]:
    return (int(clamp(c[0], 0, 255)), int(clamp(c[1], 0, 255)), int(clamp(c[2], 0, 255)))


def lerp_color(a, b, t: float) -> tuple[int, int, int]:
    return (int(lerp(a[0], b[0], t)), int(lerp(a[1], b[1], t)), int(lerp(a[2], b[2], t)))


def lighten(c, amount: float) -> tuple[int, int, int]:
    return clamp_color((c[0] + 255 * amount, c[1] + 255 * amount, c[2] + 255 * amount))


def darken(c, amount: float) -> tuple[int, int, int]:
    return clamp_color((c[0] * (1.0 - amount), c[1] * (1.0 - amount), c[2] * (1.0 - amount)))


def scale_color(c, f: float) -> tuple[int, int, int]:
    return clamp_color((c[0] * f, c[1] * f, c[2] * f))


def hsv(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb((h % 360) / 360.0, clamp(s, 0, 1), clamp(v, 0, 1))
    return (int(r * 255), int(g * 255), int(b * 255))


# --------------------------------------------------------------------------- #
#  Pixel text
# --------------------------------------------------------------------------- #
def render_text(text: str, scale: int, color) -> pygame.Surface:
    return pixelfont.render(text, scale, color)


def text_width(text: str, scale: int) -> int:
    return pixelfont.text_width(str(text).upper(), max(1, int(scale)))


def _anchor(surf, center, topleft, midtop, midleft, midright, topright,
            bottomleft, midbottom):
    rect = surf.get_rect()
    if center is not None:
        rect.center = center
    elif topleft is not None:
        rect.topleft = topleft
    elif midtop is not None:
        rect.midtop = midtop
    elif midleft is not None:
        rect.midleft = midleft
    elif midright is not None:
        rect.midright = midright
    elif topright is not None:
        rect.topright = topright
    elif bottomleft is not None:
        rect.bottomleft = bottomleft
    elif midbottom is not None:
        rect.midbottom = midbottom
    return rect


def draw_text(surface, text, scale, color, center=None, topleft=None,
              midtop=None, midleft=None, midright=None, topright=None,
              bottomleft=None, midbottom=None, shadow=False):
    """Blit pixel text with a flexible anchor (optional 1px drop shadow)."""
    surf = render_text(text, scale, color)
    rect = _anchor(surf, center, topleft, midtop, midleft, midright, topright,
                   bottomleft, midbottom)
    if shadow:
        sh = render_text(text, scale, C.OUTLINE)
        surface.blit(sh, rect.move(max(1, int(scale)), max(1, int(scale))))
        surface.blit(surf, rect)
    else:
        surface.blit(surf, rect)
    return rect


def draw_text_outlined(surface, text, scale, color, center=None, midtop=None,
                       topleft=None, outline=None):
    """Pixel text with a full 1px (scaled) outline — bold and readable."""
    outline = outline or C.OUTLINE
    main = render_text(text, scale, color)
    out = render_text(text, scale, outline)
    rect = _anchor(main, center, topleft, midtop, None, None, None, None, None)
    s = max(1, int(scale))
    for dx, dy in ((-s, 0), (s, 0), (0, -s), (0, s),
                   (-s, -s), (s, -s), (-s, s), (s, s)):
        surface.blit(out, rect.move(dx, dy))
    surface.blit(main, rect)
    return rect


# Backwards-compatible alias used by older call sites.
def draw_text_glow(surface, text, scale, color, center, glow=2, bold=True):
    return draw_text_outlined(surface, text, scale, color, center=center)


# --------------------------------------------------------------------------- #
#  Hard pixel bloom (additive)
# --------------------------------------------------------------------------- #
_glow_cache: dict[tuple[int, tuple[int, int, int]], pygame.Surface] = {}


def glow_surface(radius: int, color) -> pygame.Surface:
    """Cached additive bloom built from a few hard brightness steps."""
    radius = max(1, int(radius))
    color = clamp_color(color)
    key = (radius, color)
    surf = _glow_cache.get(key)
    if surf is not None:
        return surf
    size = radius * 2 + 1
    surf = pygame.Surface((size, size))
    surf.fill((0, 0, 0))
    # Outer (dim) -> inner (bright), hard steps, no smoothing.
    for frac, inten in ((1.0, 0.16), (0.66, 0.34), (0.34, 0.62)):
        r = max(1, int(radius * frac))
        pygame.draw.circle(surf, scale_color(color, inten), (radius, radius), r)
    _glow_cache[key] = surf
    return surf


def draw_glow(surface, center, radius, color) -> None:
    surf = glow_surface(radius, color)
    surface.blit(surf, (int(center[0]) - radius, int(center[1]) - radius),
                 special_flags=pygame.BLEND_RGB_ADD)


def draw_pixel_rect(surface, rect, fill, outline=None, highlight=None, shadow=None):
    """A blocky bevelled rectangle: fill + 1px outline + top/left highlight +
    bottom/right shadow.  All hard pixels."""
    r = pygame.Rect(rect)
    surface.fill(fill, r)
    if highlight is not None:
        surface.fill(highlight, (r.left, r.top, r.width, 1))
        surface.fill(highlight, (r.left, r.top, 1, r.height))
    if shadow is not None:
        surface.fill(shadow, (r.left, r.bottom - 1, r.width, 1))
        surface.fill(shadow, (r.right - 1, r.top, 1, r.height))
    if outline is not None:
        pygame.draw.rect(surface, outline, r, width=1)


# --------------------------------------------------------------------------- #
#  Collision
# --------------------------------------------------------------------------- #
def circle_rect_hit(cx: float, cy: float, r: float, rect: pygame.Rect):
    """Resolve a circle vs axis-aligned rectangle overlap.

    Returns ``(nx, ny, penetration)`` (unit normal out of the rect toward the
    circle centre, plus overlap depth) or ``None`` if there's no overlap.
    """
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    dx = cx - closest_x
    dy = cy - closest_y
    dist_sq = dx * dx + dy * dy
    if dist_sq > r * r:
        return None
    if dist_sq > 1e-9:
        dist = math.sqrt(dist_sq)
        return dx / dist, dy / dist, r - dist
    left = cx - rect.left
    right = rect.right - cx
    top = cy - rect.top
    bottom = rect.bottom - cy
    m = min(left, right, top, bottom)
    if m == left:
        return -1.0, 0.0, r + left
    if m == right:
        return 1.0, 0.0, r + right
    if m == top:
        return 0.0, -1.0, r + top
    return 0.0, 1.0, r + bottom
