# Game states: menu, play, pause, transition, game-over, victory.
from __future__ import annotations

import math
import random

import pygame

import config as C
from ball import Ball
from block import Block
from hud import HUD
from laser import Laser
from level import generate_level
from paddle import Paddle
from particle import ParticleSystem
from powerup import POWERUP_TYPES, PowerUp, choose_powerup_type
from utils import (circle_rect_hit, clamp, draw_glow, draw_text,
                   draw_text_outlined, ease_out_back, ease_out_cubic, lighten)


class State:
    def __init__(self, game):
        self.game = game
        self.time = 0.0

    def on_enter(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        self.time += dt

    def draw(self, surface):
        pass


# Menu
class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.options = ["PLAY", "MUTE: OFF", "QUIT"]
        self.index = 0
        self._demo = [[random.uniform(0, C.WIDTH), random.uniform(0, C.HEIGHT),
                       random.uniform(-1, 1), random.uniform(-1, 1),
                       random.choice([C.NEON_BLUE, C.NEON_PINK, C.NEON_GREEN,
                                      C.NEON_YELLOW, C.NEON_PURPLE])]
                      for _ in range(5)]

    def on_enter(self):
        self.options[1] = f"MUTE: {'ON' if self.game.sound.muted else 'OFF'}"

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.options)
                self.game.sound.play("move")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.options)
                self.game.sound.play("move")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._activate()
            elif event.key == pygame.K_m:
                self._toggle_mute()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._activate()

    def _toggle_mute(self):
        muted = self.game.sound.toggle_mute()
        self.options[1] = f"MUTE: {'ON' if muted else 'OFF'}"
        self.game.sound.play("select")

    def _activate(self):
        self.game.sound.play("select")
        opt = self.options[self.index]
        if opt == "PLAY":
            self.game.start_new_game()
        elif opt.startswith("MUTE"):
            self._toggle_mute()
        elif opt == "QUIT":
            self.game.quit()

    def update(self, dt):
        super().update(dt)
        for s in self._demo:
            s[0] += s[2] * 22 * dt
            s[1] += s[3] * 22 * dt
            if s[0] < 0 or s[0] > C.WIDTH:
                s[2] = -s[2]
            if s[1] < 0 or s[1] > C.HEIGHT:
                s[3] = -s[3]
            s[0] = clamp(s[0], 0, C.WIDTH)
            s[1] = clamp(s[1], 0, C.HEIGHT)

    def draw(self, surface):
        self.game.draw_background(surface, self.time)
        for x, y, _, _, col in self._demo:
            draw_glow(surface, (x, y), 5, col)
            surface.fill(col, (int(x) - 1, int(y) - 1, 3, 3))

        cx = C.WIDTH // 2
        bob = int(math.sin(self.time * 2.0) * 2)
        draw_text_outlined(surface, "BREAKOUT", 4, C.NEON_BLUE, center=(cx, 52 + bob))
        draw_text(surface, "N E O N   P I X E L", 1, C.NEON_PINK, center=(cx, 78))

        for i, opt in enumerate(self.options):
            y = 116 + i * 22
            if i == self.index:
                col = C.NEON_YELLOW if int(self.time * 6) % 2 == 0 else C.WHITE
                draw_text_outlined(surface, f"> {opt} <", 2, col, center=(cx, y))
            else:
                draw_text(surface, opt, 2, C.GREY, center=(cx, y))

        draw_text(surface, f"HIGH SCORE  {self.game.highscore:,}", 1,
                  C.NEON_YELLOW, center=(cx, 196))
        draw_text(surface, "ARROWS / WASD OR MOUSE TO MOVE", 1, C.GREY, center=(cx, 214))
        draw_text(surface, "SPACE / CLICK LAUNCH   P PAUSE   M MUTE   C CRT", 1,
                  C.GREY, center=(cx, 226))


# Play
class PlayState(State):
    def __init__(self, game):
        super().__init__(game)
        self.hud = HUD()
        self.particles = ParticleSystem()
        self.paddle = Paddle()

        self.score = 0
        self.lives = C.START_LIVES
        self.level = 1
        self.level_name = ""
        self.blocks: list[Block] = []
        self.balls: list[Ball] = []
        self.powerups: list[PowerUp] = []
        self.lasers: list[Laser] = []
        self.effects: dict[str, float] = {}

        self.combo = 0
        self.combo_timer = 0.0
        self.laser_timer = 0.0
        self.fire_held = False

        self.base_speed = C.BALL_BASE_SPEED
        self.speed_mult = 1.0
        self.use_mouse = False
        self.banner = ""
        self.banner_timer = 0.0

    def start_level(self, level: int):
        self.level = level
        self.blocks, self.level_name = generate_level(level)
        self.base_speed = clamp(C.BALL_BASE_SPEED + (level - 1) * C.BALL_SPEED_PER_LEVEL,
                                C.BALL_BASE_SPEED, C.BALL_MAX_SPEED)
        self.powerups.clear()
        self.lasers.clear()
        self.effects.clear()
        self.speed_mult = 1.0
        self.paddle.set_width(C.PADDLE_WIDTH)
        self.paddle.width = C.PADDLE_WIDTH
        self.paddle.reversed = False
        self.combo = 0
        self.balls.clear()
        self._spawn_serve_ball()
        self.banner = f"LEVEL {level}"
        self.banner_timer = 2.4

    def _spawn_serve_ball(self):
        ball = Ball(self.paddle.x, self.paddle.y - self.paddle.height,
                    self.current_speed())
        ball.stuck = True
        ball.stuck_offset = 0.0
        self.balls.append(ball)

    def current_speed(self) -> float:
        return clamp(self.base_speed * self.speed_mult,
                     C.BALL_BASE_SPEED * 0.5, C.BALL_MAX_SPEED)

    # Input
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.use_mouse = True
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_p, pygame.K_ESCAPE):
                self.game.sound.play("select")
                self.game.set_state(PauseState(self.game, self))
            elif event.key == pygame.K_m:
                self.game.sound.toggle_mute()
            elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                self._launch_or_fire()
                self.fire_held = True
        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                self.fire_held = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._launch_or_fire()
            self.fire_held = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.fire_held = False

    def _launch_or_fire(self):
        launched = False
        for ball in self.balls:
            if ball.stuck:
                ball.launch_from_paddle(ball.stuck_offset)
                launched = True
        if launched:
            self.game.sound.play("serve")
            return
        if "LASER" in self.effects:
            self._fire_laser()

    def _fire_laser(self):
        if self.laser_timer > 0:
            return
        self.laser_timer = C.LASER_COOLDOWN
        r = self.paddle.rect
        self.lasers.append(Laser(r.left + 3, r.top - 2))
        self.lasers.append(Laser(r.right - 3, r.top - 2))
        self.game.sound.play("laser")

    # Update
    def update(self, dt):
        super().update(dt)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT] or keys[pygame.K_a] or keys[pygame.K_d]:
            self.use_mouse = False
        mouse_x = pygame.mouse.get_pos()[0] / C.PIXEL_SCALE
        self.paddle.update(dt, keys, mouse_x, self.use_mouse)

        self._update_effects(dt)
        if self.laser_timer > 0:
            self.laser_timer -= dt
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0
        if self.banner_timer > 0:
            self.banner_timer -= dt

        if "LASER" in self.effects and self.fire_held:
            self._fire_laser()

        target = self.current_speed()
        for ball in self.balls:
            ball.speed = target

        self._update_balls(dt)
        self._update_powerups(dt)
        self._update_lasers(dt)
        for b in self.blocks:
            b.update(dt)
        self.particles.update(dt)

        if not any(b.breakable for b in self.blocks):
            self._level_cleared()
            return
        if not self.balls:
            self._lose_life()

    def _update_effects(self, dt):
        expired = []
        for kind in list(self.effects.keys()):
            self.effects[kind] -= dt
            if self.effects[kind] <= 0:
                expired.append(kind)
        for kind in expired:
            del self.effects[kind]
            self._revert_effect(kind)

    def _revert_effect(self, kind):
        if kind in ("EXPAND", "SHRINK"):
            self.paddle.set_width(C.PADDLE_WIDTH)
        elif kind in ("SLOW", "FAST"):
            self.speed_mult = 1.0
        elif kind == "PIERCE":
            for ball in self.balls:
                ball.pierce = False
        elif kind == "REVERSE":
            self.paddle.reversed = False

    # Ball physics with sub-stepping
    def _update_balls(self, dt):
        survivors = []
        for ball in self.balls:
            if ball.stuck:
                ball.x = clamp(self.paddle.x + ball.stuck_offset * (self.paddle.width / 2),
                               ball.radius, C.WIDTH - ball.radius)
                ball.y = self.paddle.y - self.paddle.height / 2 - ball.radius - 1
                ball.push_trail()
                survivors.append(ball)
                continue

            dist = ball.speed * dt
            steps = max(1, int(dist / C.BALL_SUBSTEP_PX) + 1)
            sub_dt = dt / steps
            alive = True
            for _ in range(steps):
                ball.step(sub_dt)
                self._collide_walls(ball)
                self._collide_paddle(ball)
                self._collide_blocks(ball)
                if ball.y - ball.radius > C.HEIGHT:
                    alive = False
                    break
            if alive:
                ball.push_trail()
                if random.random() < 0.4:
                    self.particles.trail_puff(ball.x, ball.y,
                                              C.NEON_PURPLE if ball.pierce else ball.color)
                survivors.append(ball)
        self.balls = survivors

    def _collide_walls(self, ball):
        if ball.x - ball.radius < 0:
            ball.x = ball.radius
            ball.reflect(1.0, 0.0)
            self.game.sound.play("wall")
        elif ball.x + ball.radius > C.WIDTH:
            ball.x = C.WIDTH - ball.radius
            ball.reflect(-1.0, 0.0)
            self.game.sound.play("wall")
        if ball.y - ball.radius < C.HUD_HEIGHT:
            ball.y = C.HUD_HEIGHT + ball.radius
            ball.reflect(0.0, 1.0)
            self.game.sound.play("wall")

    def _collide_paddle(self, ball):
        if ball.vy <= 0:
            return
        prect = self.paddle.rect.inflate(0, 4)
        if not ball.rect.colliderect(prect):
            return
        if ball.y > self.paddle.y + self.paddle.height:
            return
        offset = self.paddle.offset_for(ball.x)
        if "CATCH" in self.effects:
            ball.stuck = True
            ball.stuck_offset = clamp(offset, -0.95, 0.95)
            ball.y = self.paddle.y - self.paddle.height / 2 - ball.radius - 1
        else:
            ball.y = self.paddle.y - self.paddle.height / 2 - ball.radius - 1
            ball.launch_from_paddle(offset)
        self.paddle.flash()
        self.combo = 0
        self.game.sound.play("paddle")
        self.particles.spark(ball.x, self.paddle.y - self.paddle.height,
                             self.paddle.color, count=5)

    def _collide_blocks(self, ball):
        best = None
        best_pen = -1.0
        for block in self.blocks:
            hit = circle_rect_hit(ball.x, ball.y, ball.radius, block.rect)
            if hit and hit[2] > best_pen:
                best = (block, hit)
                best_pen = hit[2]
        if best is None:
            return
        block, (nx, ny, pen) = best

        if block.unbreakable:
            ball.x += nx * pen
            ball.y += ny * pen
            ball.reflect(nx, ny)
            block.hit()
            self.game.add_shake(C.SHAKE_HARD)
            self.game.sound.play("hard")
            self.particles.spark(ball.x, ball.y, (180, 190, 210), count=4)
            return

        if ball.pierce:
            block.hp = 0
            destroyed = True
        else:
            destroyed = block.hit()

        if destroyed:
            self._destroy_block(block)
        else:
            self.score += C.SCORE_PER_HIT
            self.game.sound.play("hard")
            self.particles.spark(block.rect.centerx, block.rect.centery,
                                 lighten(block.color, 0.2), count=4)

        if not ball.pierce:
            ball.x += nx * pen
            ball.y += ny * pen
            ball.reflect(nx, ny)

    def _destroy_block(self, block):
        try:
            self.blocks.remove(block)
        except ValueError:
            return
        self.combo += 1
        self.combo_timer = 2.5
        gain = C.SCORE_PER_BLOCK + (self.combo - 1) * C.COMBO_STEP
        self.score += gain
        self.particles.block_explosion(block.rect, block.color)
        self.game.add_shake(C.SHAKE_BLOCK)
        self.game.sound.play("break")
        if self.combo >= 3:
            self.game.add_popup(block.rect.centerx, block.rect.centery,
                                f"X{self.combo}", C.NEON_ORANGE)
        if random.random() < C.POWERUP_DROP_CHANCE:
            kind = choose_powerup_type()
            self.powerups.append(PowerUp(block.rect.centerx, block.rect.centery, kind))

    # Power-ups & lasers
    def _update_powerups(self, dt):
        prect = self.paddle.rect.inflate(4, 4)
        for pu in self.powerups:
            pu.update(dt)
            if not pu.dead and pu.rect.colliderect(prect) and pu.y < C.HEIGHT:
                pu.dead = True
                self._apply_powerup(pu.kind)
        self.powerups = [p for p in self.powerups if not p.dead]

    def _apply_powerup(self, kind):
        meta = POWERUP_TYPES[kind]
        bad = meta["bad"]
        self.game.sound.play("powerdown" if bad else "powerup")
        col = meta["color"]
        self.game.add_popup(self.paddle.x, self.paddle.y - 12, meta["label"], col)
        self.particles.burst(self.paddle.x, self.paddle.y, col, count=12, speed=80)

        if meta["timed"]:
            self.effects[kind] = C.EFFECT_DURATION[kind]

        if kind == "MULTI":
            self._multiball()
        elif kind == "EXPAND":
            self.effects.pop("SHRINK", None)
            self.paddle.set_width(C.PADDLE_WIDTH_EXPAND)
        elif kind == "SHRINK":
            self.effects.pop("EXPAND", None)
            self.paddle.set_width(C.PADDLE_WIDTH_SHRINK)
        elif kind == "SLOW":
            self.effects.pop("FAST", None)
            self.speed_mult = C.SLOW_MULT
        elif kind == "FAST":
            self.effects.pop("SLOW", None)
            self.speed_mult = C.FAST_MULT
        elif kind == "LIFE":
            self.lives = min(C.MAX_LIVES, self.lives + 1)
            self.game.sound.play("life")
        elif kind == "PIERCE":
            for ball in self.balls:
                ball.pierce = True
        elif kind == "REVERSE":
            self.paddle.reversed = True

    def _multiball(self):
        if not self.balls:
            return
        new = []
        for ball in self.balls:
            if ball.stuck:
                ball.launch_from_paddle(ball.stuck_offset)
            for _ in range(2):
                if len(self.balls) + len(new) >= C.MAX_BALLS:
                    break
                ang = random.uniform(-1.0, 1.0)
                nb = Ball(ball.x, ball.y, ball.speed, dir_x=ang,
                          dir_y=-abs(ball.dir_y) - 0.2, color=ball.color)
                nb.stuck = False
                nb.pierce = ball.pierce
                new.append(nb)
        self.balls.extend(new)

    def _update_lasers(self, dt):
        for laser in self.lasers:
            laser.update(dt)
            if laser.dead:
                continue
            lrect = laser.rect
            for block in self.blocks:
                if lrect.colliderect(block.rect):
                    laser.dead = True
                    if block.unbreakable:
                        self.particles.spark(laser.x, laser.y, (180, 190, 210), count=3)
                        self.game.sound.play("hard")
                    else:
                        if block.hit():
                            self._destroy_block(block)
                        else:
                            self.score += C.SCORE_PER_HIT
                            self.particles.spark(laser.x, laser.y,
                                                 lighten(block.color, 0.2), count=3)
                            self.game.sound.play("hard")
                    break
        self.lasers = [l for l in self.lasers if not l.dead]

    # Life / level resolution
    def _lose_life(self):
        self.lives -= 1
        self.game.add_shake(C.SHAKE_LIFE)
        self.game.sound.play("loselife")
        self.combo = 0
        if self.lives < 0:
            self._game_over()
            return
        self.powerups.clear()
        self.lasers.clear()
        for kind in list(self.effects.keys()):
            self._revert_effect(kind)
        self.effects.clear()
        self.speed_mult = 1.0
        self.paddle.set_width(C.PADDLE_WIDTH)
        self.paddle.reversed = False
        self._spawn_serve_ball()
        self.banner = "READY"
        self.banner_timer = 1.4

    def _level_cleared(self):
        bonus = C.LEVEL_CLEAR_BONUS + self.lives * 250
        self.score += bonus
        self.game.add_shake(C.SHAKE_LEVEL)
        self.game.sound.play("level")
        self.game.update_highscore(self.score)
        if self.level >= C.MAX_LEVEL:
            self.game.set_state(VictoryState(self.game, self.score))
        else:
            self.game.set_state(TransitionState(self.game, self, self.level + 1, bonus))

    def _game_over(self):
        is_high = self.game.update_highscore(self.score)
        self.game.sound.play("gameover")
        self.game.set_state(GameOverState(self.game, self.score, is_high))

    # Render
    def effects_list(self):
        order = ["EXPAND", "SHRINK", "SLOW", "FAST", "LASER", "PIERCE", "CATCH", "REVERSE"]
        return [(k, self.effects[k]) for k in order if k in self.effects]

    def draw_scene(self, surface):
        self.game.draw_background(surface, self.time)
        for block in self.blocks:
            block.draw(surface)
        for pu in self.powerups:
            pu.draw(surface)
        for laser in self.lasers:
            laser.draw(surface)
        self.particles.draw(surface)
        self.paddle.draw(surface, "LASER" in self.effects, self.time)
        for ball in self.balls:
            ball.draw(surface, self.time)

    def draw(self, surface):
        self.draw_scene(surface)
        self.hud.draw(surface, self.score, self.game.highscore, self.lives,
                      self.level, self.level_name, self.combo,
                      self.effects_list(), self.time)
        self.game.draw_popups(surface)

        if any(b.stuck for b in self.balls):
            if int(self.time * 3) % 2 == 0:
                draw_text(surface, "SPACE / CLICK TO LAUNCH", 1, C.WHITE,
                          center=(C.WIDTH // 2, C.HEIGHT - 34))

        if self.banner_timer > 0:
            t = self.banner_timer
            alpha = clamp(t if t < 1 else (1.0 if t < 2 else (2.4 - t) / 0.4), 0, 1)
            scale = ease_out_back(clamp((2.4 - t) * 2.0, 0, 1))
            sc = max(2, int(2 + 2 * scale))
            band = pygame.Surface((C.WIDTH, 40), pygame.SRCALPHA)
            draw_text_outlined(band, self.banner, sc, C.NEON_YELLOW,
                               center=(C.WIDTH // 2, 14))
            if self.banner.startswith("LEVEL"):
                draw_text(band, self.level_name, 1, C.NEON_PINK,
                          center=(C.WIDTH // 2, 32))
            band.set_alpha(int(255 * alpha))
            surface.blit(band, (0, C.HEIGHT // 2 - 24))


# Pause
class PauseState(State):
    def __init__(self, game, play):
        super().__init__(game)
        self.play = play
        self.options = ["RESUME", "RESTART", "MUTE", "QUIT TO MENU"]
        self.index = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_p, pygame.K_ESCAPE):
                self._resume()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.index = (self.index - 1) % len(self.options)
                self.game.sound.play("move")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.index = (self.index + 1) % len(self.options)
                self.game.sound.play("move")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self._activate()
            elif event.key == pygame.K_m:
                self.game.sound.toggle_mute()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._activate()

    def _resume(self):
        self.game.sound.play("select")
        self.game.set_state(self.play)

    def _activate(self):
        self.game.sound.play("select")
        opt = self.options[self.index]
        if opt == "RESUME":
            self.game.set_state(self.play)
        elif opt == "RESTART":
            self.game.start_new_game()
        elif opt == "MUTE":
            self.game.sound.toggle_mute()
        elif opt == "QUIT TO MENU":
            self.game.go_to_menu()

    def draw(self, surface):
        self.play.draw(surface)
        veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 8, 20, 185))
        surface.blit(veil, (0, 0))

        cx = C.WIDTH // 2
        draw_text_outlined(surface, "PAUSED", 4, C.NEON_BLUE, center=(cx, 60))
        for i, opt in enumerate(self.options):
            y = 110 + i * 22
            label = opt
            if opt == "MUTE":
                label = f"MUTE: {'ON' if self.game.sound.muted else 'OFF'}"
            if i == self.index:
                draw_text_outlined(surface, f"> {label} <", 2, C.WHITE, center=(cx, y))
            else:
                draw_text(surface, label, 2, C.GREY, center=(cx, y))
        draw_text(surface, "P / ESC TO RESUME", 1, C.GREY, center=(cx, 215))


# Level transition
class TransitionState(State):
    DURATION = 2.6

    def __init__(self, game, play, next_level, bonus):
        super().__init__(game)
        self.play = play
        self.next_level = next_level
        self.bonus = bonus
        self._advanced = False

    def update(self, dt):
        super().update(dt)
        self.play.particles.update(dt)
        if self.time >= self.DURATION * 0.5 and not self._advanced:
            self.play.start_level(self.next_level)
            self._advanced = True
        if self.time >= self.DURATION:
            self.game.set_state(self.play)

    def draw(self, surface):
        self.play.draw(surface)
        half = self.DURATION / 2.0
        if self.time < half:
            f = ease_out_cubic(self.time / half)
        else:
            f = ease_out_cubic(1.0 - (self.time - half) / half)
        veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 8, 20, int(238 * f)))
        surface.blit(veil, (0, 0))

        cx = C.WIDTH // 2
        if 0.2 < self.time < self.DURATION - 0.2:
            draw_text_outlined(surface, "LEVEL CLEARED", 2, C.NEON_GREEN, center=(cx, 95))
            draw_text(surface, f"BONUS +{self.bonus:,}", 1, C.NEON_YELLOW, center=(cx, 120))
            draw_text(surface, f"NEXT: LEVEL {self.next_level}", 1, C.WHITE, center=(cx, 138))


# Game over
class GameOverState(State):
    def __init__(self, game, score, is_high):
        super().__init__(game)
        self.score = score
        self.is_high = is_high
        self.particles = ParticleSystem()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.game.go_to_menu()
            elif event.key == pygame.K_r:
                self.game.start_new_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.game.go_to_menu()

    def update(self, dt):
        super().update(dt)
        if self.is_high and len(self.particles) < 90:
            self.particles.confetti()
        self.particles.update(dt)

    def draw(self, surface):
        self.game.draw_background(surface, self.time)
        self.particles.draw(surface)
        cx = C.WIDTH // 2
        draw_text_outlined(surface, "GAME OVER", 4, C.NEON_RED, center=(cx, 62))
        draw_text(surface, f"SCORE  {self.score:,}", 2, C.WHITE, center=(cx, 108))
        if self.is_high:
            col = C.NEON_YELLOW if int(self.time * 6) % 2 == 0 else C.NEON_ORANGE
            draw_text_outlined(surface, "NEW HIGH SCORE!", 2, col, center=(cx, 138))
        else:
            draw_text(surface, f"BEST  {self.game.highscore:,}", 1, C.NEON_YELLOW,
                      center=(cx, 138))
        if int(self.time * 2) % 2 == 0:
            draw_text(surface, "ENTER / CLICK MENU      R RETRY", 1, C.GREY,
                      center=(cx, 180))


# Victory
class VictoryState(State):
    def __init__(self, game, score):
        super().__init__(game)
        self.score = score
        self.particles = ParticleSystem()
        self._played = False

    def on_enter(self):
        if not self._played:
            self.game.sound.play("victory")
            self._played = True

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.game.go_to_menu()
            elif event.key == pygame.K_r:
                self.game.start_new_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.game.go_to_menu()

    def update(self, dt):
        super().update(dt)
        for _ in range(2):
            self.particles.confetti()
        self.particles.update(dt)

    def draw(self, surface):
        self.game.draw_background(surface, self.time)
        self.particles.draw(surface)
        cx = C.WIDTH // 2
        bob = int(math.sin(self.time * 3) * 3)
        draw_text_outlined(surface, "VICTORY!", 4, C.NEON_YELLOW, center=(cx, 56 + bob))
        draw_text(surface, "YOU CLEARED EVERY LEVEL!", 1, C.NEON_GREEN, center=(cx, 100))
        draw_text(surface, f"FINAL SCORE  {self.score:,}", 2, C.WHITE, center=(cx, 124))
        if int(self.time * 2) % 2 == 0:
            draw_text(surface, "ENTER / CLICK TO CONTINUE", 1, C.GREY, center=(cx, 170))
