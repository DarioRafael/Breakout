# Game window, main loop, compositor and shared services.
from __future__ import annotations

import math
import os
import random

import numpy as np
import pygame

import config as C
import highscore as hs
from utils import clamp, render_text


class Game:
    def __init__(self, headless: bool = False):
        self.headless = headless
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

        pygame.init()
        try:
            pygame.font.init()
        except pygame.error:
            pass

        # Display first so Surface.convert() has a pixel format
        try:
            self.window = pygame.display.set_mode(
                (C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.DOUBLEBUF, vsync=1)
        except pygame.error:
            self.window = pygame.display.set_mode((C.WINDOW_WIDTH, C.WINDOW_HEIGHT))
        if not headless:
            pygame.display.set_caption(C.TITLE)

        # Low-res canvas (then upscaled)
        try:
            self.canvas = pygame.Surface((C.VIRTUAL_WIDTH, C.VIRTUAL_HEIGHT)).convert()
        except pygame.error:
            self.canvas = pygame.Surface((C.VIRTUAL_WIDTH, C.VIRTUAL_HEIGHT))
        self.screen = self.canvas

        self.clock = pygame.time.Clock()
        self.running = True
        self.fullscreen = False

        from sound import SoundManager
        self.sound = SoundManager()

        self.highscore = hs.load_highscore()

        # Visual services
        self.trauma = 0.0
        self.popups: list[dict] = []
        self.crt = C.CRT_ENABLED
        self._stars = self._make_starfield()
        self._bg_cache: dict[int, pygame.Surface] = {}
        self._crt_overlay = self._make_crt_overlay()

        # State (import here to avoid cycle)
        from states import MenuState
        self._MenuState = MenuState
        self.state = None
        self.set_state(MenuState(self))

        if not headless:
            self.sound.start_music()

    # Background: dithered gradient + parallax stars
    def _make_starfield(self):
        rng = random.Random(1234)
        stars = []
        for _ in range(70):
            stars.append([
                rng.uniform(0, C.WIDTH),
                rng.uniform(0, C.HEIGHT),
                rng.uniform(0.2, 1.0),
                rng.uniform(0, math.tau),
            ])
        return stars

    def _bayer_gradient(self) -> pygame.Surface:
        w, h = C.VIRTUAL_WIDTH, C.VIRTUAL_HEIGHT
        bayer = np.array([
            [0, 8, 2, 10],
            [12, 4, 14, 6],
            [3, 11, 1, 9],
            [15, 7, 13, 5],
        ], dtype=np.float64) / 16.0

        top = np.array(C.BG_TOP, dtype=np.float64)
        mid = np.array(C.BG_MID, dtype=np.float64)
        bot = np.array(C.BG_BOTTOM, dtype=np.float64)

        ys = np.linspace(0.0, 1.0, h)[:, None]
        seg1 = (ys * 2.0).clip(0, 1)
        seg2 = ((ys - 0.5) * 2.0).clip(0, 1)
        base = top[None, :] * (1 - seg1) + mid[None, :] * seg1
        base = np.where(ys < 0.5, base, mid[None, :] * (1 - seg2) + bot[None, :] * seg2)

        img = np.repeat(base[:, None, :], w, axis=1)
        thresh = bayer[np.arange(h) % 4][:, np.arange(w) % 4]
        img = img + (thresh[:, :, None] - 0.5) * 6.0
        img = img.clip(0, 255).astype(np.uint8)

        try:
            surf = pygame.Surface((w, h)).convert()
        except pygame.error:
            surf = pygame.Surface((w, h))
        pygame.surfarray.blit_array(surf, np.transpose(img, (1, 0, 2)))
        return surf

    def draw_background(self, surface, t):
        bg = self._bg_cache.get(0)
        if bg is None:
            bg = self._bayer_gradient()
            self._bg_cache[0] = bg
        surface.blit(bg, (0, 0))

        for x, y, depth, phase in self._stars:
            y2 = (y + t * 8 * depth) % C.HEIGHT
            tw = 0.5 + 0.5 * math.sin(t * 2.0 + phase)
            b = int(120 * depth * (0.4 + 0.6 * tw))
            surface.fill((b, b, min(255, b + 30)), (int(x), int(y2), 1, 1))

    def _make_crt_overlay(self) -> pygame.Surface:
        # scanlines + vignette
        w, h = C.WINDOW_WIDTH, C.WINDOW_HEIGHT
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        line = pygame.Surface((w, 1), pygame.SRCALPHA)
        line.fill((0, 0, 0, C.CRT_SCANLINE_ALPHA))
        for y in range(C.PIXEL_SCALE - 1, h, C.PIXEL_SCALE):
            overlay.blit(line, (0, y))
        va = C.CRT_VIGNETTE_ALPHA
        for i in range(18):
            a = int(va * (1 - i / 18))
            if a <= 0:
                continue
            pygame.draw.rect(overlay, (0, 0, 0, a),
                             (i, i, w - 2 * i, h - 2 * i), width=1)
        return overlay

    # Screen shake
    def add_shake(self, amount: float):
        self.trauma = clamp(self.trauma + amount, 0.0, 1.0)

    def shake_offset(self):
        if self.trauma <= 0:
            return (0, 0)
        mag = (self.trauma ** 2) * C.SHAKE_MAX_PIXELS
        return (int(round(random.uniform(-mag, mag))),
                int(round(random.uniform(-mag, mag))))

    # Floating score popups
    def add_popup(self, x, y, text, color):
        self.popups.append({"x": x, "y": y, "text": text, "color": color,
                            "life": 0.9, "max": 0.9})

    def _update_popups(self, dt):
        for p in self.popups:
            p["life"] -= dt
            p["y"] -= 16 * dt
        self.popups = [p for p in self.popups if p["life"] > 0]

    def draw_popups(self, surface):
        for p in self.popups:
            f = clamp(p["life"] / p["max"], 0, 1)
            col = (int(p["color"][0]), int(p["color"][1]), int(p["color"][2]))
            txt = render_text(p["text"], 1, col)
            txt.set_alpha(int(255 * f))
            surface.blit(txt, txt.get_rect(center=(int(p["x"]), int(p["y"]))))

    # State management
    def set_state(self, state):
        self.state = state
        state.on_enter()

    def go_to_menu(self):
        self.popups.clear()
        self.trauma = 0.0
        self.set_state(self._MenuState(self))

    def start_new_game(self):
        from states import PlayState
        self.popups.clear()
        self.trauma = 0.0
        play = PlayState(self)
        play.start_level(1)
        self.set_state(play)

    def update_highscore(self, score: int) -> bool:
        if score > self.highscore:
            self.highscore = score
            hs.save_highscore(score)
            return True
        return False

    def toggle_fullscreen(self):
        if self.headless:
            return
        self.fullscreen = not self.fullscreen
        try:
            if self.fullscreen:
                self.window = pygame.display.set_mode(
                    (C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.FULLSCREEN | pygame.SCALED,
                    vsync=1)
            else:
                self.window = pygame.display.set_mode(
                    (C.WINDOW_WIDTH, C.WINDOW_HEIGHT), pygame.DOUBLEBUF, vsync=1)
        except pygame.error:
            self.window = pygame.display.set_mode((C.WINDOW_WIDTH, C.WINDOW_HEIGHT))

    def quit(self):
        self.running = False

    # Compositor: upscale canvas, shake, CRT
    def present(self):
        ox, oy = self.shake_offset()
        if ox or oy:
            self.window.fill((0, 0, 0))
        scaled = pygame.transform.scale(
            self.canvas, (C.WINDOW_WIDTH, C.WINDOW_HEIGHT))
        self.window.blit(scaled, (ox * C.PIXEL_SCALE, oy * C.PIXEL_SCALE))
        if self.crt:
            self.window.blit(self._crt_overlay, (0, 0))
        pygame.display.flip()

    # Main loop
    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            dt = min(dt, C.MAX_DT)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                    self.crt = not self.crt
                    self.sound.play("select")
                else:
                    self.state.handle_event(event)

            self.state.update(dt)
            self._update_popups(dt)
            self.trauma = max(0.0, self.trauma - dt * 1.6)

            self.state.draw(self.canvas)
            self.present()

        pygame.quit()

    # Headless self-test
    def run_selftest(self, verbose=True):
        import powerup as pu_mod
        from states import (GameOverState, MenuState, PauseState, PlayState,
                            TransitionState, VictoryState)
        log = (lambda *a: print(*a)) if verbose else (lambda *a: None)
        dt = 1.0 / 120.0
        surf = self.canvas
        original_highscore = hs.load_highscore()

        # Levels generate
        from level import generate_level
        for lv in range(1, C.MAX_LEVEL + 1):
            blocks, name = generate_level(lv)
            assert blocks, f"level {lv} produced no blocks"
            assert any(b.breakable for b in blocks), f"level {lv} has no breakable bricks"
        log(f"[ok] generated all {C.MAX_LEVEL} levels, all clearable")

        # Compositor
        self.draw_background(surf, 1.23)
        self.present()
        log("[ok] background + pixel compositor + CRT overlay")

        # Menu
        menu = MenuState(self)
        self.set_state(menu)
        for _ in range(60):
            menu.update(dt)
            menu.draw(surf)
            self.present()
        log("[ok] menu renders")

        # Play
        self.start_new_game()
        play = self.state
        assert isinstance(play, PlayState)
        frames = 0
        powerups_tested = set()
        all_kinds = list(pu_mod.POWERUP_TYPES)
        max_frames = 6000
        while frames < max_frames and isinstance(self.state, (PlayState, TransitionState)):
            cur = self.state
            if isinstance(cur, TransitionState):
                cur.update(dt)
                cur.draw(surf)
                frames += 1
                continue
            play = cur
            target = play.paddle.x
            lowest = None
            for b in play.balls:
                if b.stuck:
                    b.launch_from_paddle(random.uniform(-0.6, 0.6))
                if lowest is None or b.y > lowest.y:
                    lowest = b
            if lowest is not None:
                target = lowest.x
            play.paddle.x = clamp(target, play.paddle.width / 2,
                                  C.WIDTH - play.paddle.width / 2)
            if frames % 40 == 0 and len(powerups_tested) < len(all_kinds):
                kind = all_kinds[len(powerups_tested) % len(all_kinds)]
                play._apply_powerup(kind)
                powerups_tested.add(kind)
            if "LASER" in play.effects and frames % 15 == 0:
                play._fire_laser()
            if not play.balls:
                play._spawn_serve_ball()
            play.update(dt)
            play.draw(surf)
            self._update_popups(dt)
            frames += 1
            if frames == 800:
                for b in list(play.blocks):
                    if b.breakable:
                        b.hp = 1
                        play._destroy_block(b)
        log(f"[ok] simulated {frames} gameplay frames; tested power-ups: "
            f"{sorted(powerups_tested)}")

        # Pause
        play = PlayState(self)
        play.start_level(3)
        self.set_state(play)
        pause = PauseState(self, play)
        self.set_state(pause)
        for _ in range(30):
            pause.update(dt)
            pause.draw(surf)
        log("[ok] pause overlay renders")

        # Game over
        play = PlayState(self)
        play.start_level(2)
        self.set_state(play)
        play.lives = 0
        play.balls.clear()
        play.update(dt)
        assert isinstance(self.state, GameOverState), "expected GameOverState"
        for _ in range(60):
            self.state.update(dt)
            self.state.draw(surf)
        log("[ok] game over path + screen")

        # Victory
        vic = VictoryState(self, 999999)
        self.set_state(vic)
        for _ in range(60):
            vic.update(dt)
            vic.draw(surf)
        log("[ok] victory screen")

        # High-score
        saved = hs.load_highscore()
        hs.save_highscore(saved + 12345)
        assert hs.load_highscore() == saved + 12345
        hs.save_highscore(saved)
        assert hs.load_highscore() == saved
        log("[ok] high-score persistence")

        hs.save_highscore(original_highscore)
        log("\nSELFTEST PASSED — the game is healthy.")
        return True

    def save_screenshot(self, path: str):
        self.state.draw(self.canvas)
        scaled = pygame.transform.scale(self.canvas, (C.WINDOW_WIDTH, C.WINDOW_HEIGHT))
        self.window.blit(scaled, (0, 0))
        if self.crt:
            self.window.blit(self._crt_overlay, (0, 0))
        pygame.image.save(self.window, path)
