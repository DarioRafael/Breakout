# Procedural SFX + chiptune music (no external files).
from __future__ import annotations

import math

import numpy as np
import pygame

SAMPLE_RATE = 44100


# Waveforms (return float arrays in [-1, 1])
def _t(duration: float) -> np.ndarray:
    return np.linspace(0.0, duration, int(SAMPLE_RATE * duration), endpoint=False)


def _sine(freq, dur):
    return np.sin(2 * np.pi * freq * _t(dur))


def _square(freq, dur, duty=0.5):
    ph = (_t(dur) * freq) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def _saw(freq, dur):
    ph = (_t(dur) * freq) % 1.0
    return 2.0 * ph - 1.0


def _triangle(freq, dur):
    ph = (_t(dur) * freq) % 1.0
    return 2.0 * np.abs(2.0 * ph - 1.0) - 1.0


def _noise(dur):
    n = int(SAMPLE_RATE * dur)
    return np.random.uniform(-1.0, 1.0, n)


def _env(signal, attack=0.005, release=0.08, sustain=1.0):
    # attack/sustain/release envelope
    n = len(signal)
    if n == 0:
        return signal
    env = np.full(n, sustain, dtype=np.float64)
    a = min(int(SAMPLE_RATE * attack), n)
    r = min(int(SAMPLE_RATE * release), n)
    if a > 0:
        env[:a] *= np.linspace(0.0, 1.0, a)
    if r > 0:
        env[-r:] *= np.linspace(1.0, 0.0, r)
    return signal * env


def _freq_sweep(f0, f1, dur, kind="sine"):
    t = _t(dur)
    if dur <= 0:
        return t
    inst = f0 + (f1 - f0) * (t / dur)
    phase = 2 * np.pi * np.cumsum(inst) / SAMPLE_RATE
    if kind == "square":
        return np.where((phase / (2 * np.pi)) % 1.0 < 0.5, 1.0, -1.0)
    if kind == "saw":
        return 2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0
    return np.sin(phase)


_NOTE_BASE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
              "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def _note_freq(name: str) -> float:
    if name == "R":
        return 0.0
    pitch = name[:-1]
    octave = int(name[-1])
    semitone = _NOTE_BASE[pitch] + (octave - 4) * 12
    return 440.0 * (2.0 ** ((semitone - 9) / 12.0))


class SoundManager:
    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_array = None
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(24)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            return
        self._build_all()

    def _make(self, signal: np.ndarray, volume: float = 0.5) -> "pygame.mixer.Sound":
        sig = np.clip(signal, -1.0, 1.0) * volume
        audio = (sig * 32767).astype(np.int16)
        stereo = np.column_stack((audio, audio))
        return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))

    def _build_all(self) -> None:
        # Ball bounce
        bounce = _env(_square(520, 0.07, 0.5) * 0.6 + _sine(780, 0.07) * 0.4,
                      attack=0.002, release=0.05)
        self.sfx["bounce"] = self._make(bounce, 0.35)

        # Paddle hit
        paddle = _env(_square(300, 0.08, 0.4) * 0.6 + _sine(440, 0.08) * 0.4,
                      attack=0.002, release=0.06)
        self.sfx["paddle"] = self._make(paddle, 0.4)

        # Wall
        wall = _env(_sine(660, 0.04), attack=0.001, release=0.035)
        self.sfx["wall"] = self._make(wall, 0.22)

        # Brick break
        brk = _env(_noise(0.18) * 0.5 + _freq_sweep(900, 200, 0.18, "saw") * 0.5,
                   attack=0.001, release=0.12)
        self.sfx["break"] = self._make(brk, 0.4)

        # Hard brick clink
        clink = _env(_sine(880, 0.05) * 0.5 + _square(1200, 0.05, 0.3) * 0.5,
                     attack=0.001, release=0.04)
        self.sfx["hard"] = self._make(clink, 0.3)

        # Power-up (rising arpeggio)
        up = np.concatenate([_env(_square(f, 0.06, 0.5), 0.002, 0.04)
                             for f in (523, 659, 784, 1047)])
        self.sfx["powerup"] = self._make(up, 0.4)

        # Power-down (descending buzz)
        down = np.concatenate([_env(_square(f, 0.07, 0.5), 0.002, 0.05)
                               for f in (440, 349, 277, 220)])
        self.sfx["powerdown"] = self._make(down, 0.38)

        # Laser
        laser = _env(_freq_sweep(1400, 500, 0.12, "square"), 0.001, 0.08)
        self.sfx["laser"] = self._make(laser, 0.25)

        # Extra life
        life = np.concatenate([_env(_sine(f, 0.1), 0.003, 0.07)
                               for f in (659, 784, 988, 1319)])
        self.sfx["life"] = self._make(life, 0.4)

        # Lose life
        loselife = _env(_freq_sweep(440, 110, 0.5, "saw"), 0.01, 0.3)
        self.sfx["loselife"] = self._make(loselife, 0.4)

        # Level clear
        clear = np.concatenate([_env(_square(f, 0.12, 0.5), 0.004, 0.08)
                                for f in (523, 659, 784, 1047, 1319)])
        self.sfx["level"] = self._make(clear, 0.4)

        # Game over
        over = np.concatenate([_env(_saw(f, 0.28) * 0.5 + _square(f, 0.28, 0.4) * 0.5,
                                     0.01, 0.2)
                               for f in (392, 330, 262, 196)])
        self.sfx["gameover"] = self._make(over, 0.4)

        # Victory
        win = np.concatenate([_env(_square(f, 0.13, 0.5) * 0.6 + _sine(f * 2, 0.13) * 0.4,
                                   0.004, 0.08)
                              for f in (523, 659, 784, 1047, 1319, 1568)])
        self.sfx["victory"] = self._make(win, 0.42)

        # Serve
        serve = _env(_freq_sweep(300, 700, 0.12, "sine"), 0.002, 0.07)
        self.sfx["serve"] = self._make(serve, 0.3)

        # UI
        self.sfx["select"] = self._make(_env(_square(700, 0.05, 0.5), 0.002, 0.04), 0.3)
        self.sfx["move"] = self._make(_env(_sine(500, 0.03), 0.001, 0.025), 0.2)

        self._build_music()

    def _build_music(self) -> None:
        # 16-step lead in A minor + bass + drums
        bpm = 132
        beat = 60.0 / bpm
        step = beat / 2.0

        lead = ["A4", "R", "C5", "E5", "A4", "R", "E5", "D5",
                "C5", "R", "E5", "G5", "A5", "G5", "E5", "C5",
                "A4", "R", "C5", "E5", "F5", "R", "E5", "D5",
                "C5", "B4", "C5", "D5", "E5", "R", "A4", "R"]
        bass = ["A2", "A2", "A2", "A2", "F2", "F2", "F2", "F2",
                "C3", "C3", "C3", "C3", "G2", "G2", "G2", "G2",
                "A2", "A2", "A2", "A2", "F2", "F2", "F2", "F2",
                "C3", "C3", "G2", "G2", "A2", "A2", "E2", "E2"]

        total = np.zeros(int(SAMPLE_RATE * step * len(lead)), dtype=np.float64)

        def place(arr, idx, signal):
            start = int(idx * step * SAMPLE_RATE)
            end = min(start + len(signal), len(arr))
            arr[start:end] += signal[:end - start]

        for i, name in enumerate(lead):
            f = _note_freq(name)
            if f > 0:
                note = _env(_square(f, step * 0.95, 0.5) * 0.5
                            + _triangle(f, step * 0.95) * 0.25,
                            attack=0.004, release=0.05)
                place(total, i, note * 0.5)
        for i, name in enumerate(bass):
            f = _note_freq(name)
            if f > 0:
                note = _env(_square(f, step * 0.95, 0.5) * 0.4
                            + _sine(f, step * 0.95) * 0.4,
                            attack=0.004, release=0.05)
                place(total, i, note * 0.45)

        # Kick + hat
        for i in range(len(lead)):
            if i % 2 == 0:
                kick = _env(_freq_sweep(160, 50, 0.12, "sine"), 0.001, 0.1)
                place(total, i, kick * 0.5)
            else:
                hat = _env(_noise(0.05), 0.001, 0.04)
                place(total, i, hat * 0.12)

        peak = np.max(np.abs(total)) or 1.0
        total = total / peak * 0.85
        self._music_array = total

    # Playback (no-ops when disabled / muted)
    def play(self, name: str, volume: float = 1.0) -> None:
        if not self.enabled or self.muted:
            return
        snd = self.sfx.get(name)
        if snd is None:
            return
        try:
            ch = pygame.mixer.find_channel(True)
            if ch is not None:
                ch.set_volume(volume)
                ch.play(snd)
        except pygame.error:
            pass

    def start_music(self, volume: float = 0.45) -> None:
        if not self.enabled or self._music_array is None:
            return
        try:
            arr = (np.clip(self._music_array, -1, 1) * 32767).astype(np.int16)
            stereo = np.ascontiguousarray(np.column_stack((arr, arr)))
            self._music_sound = pygame.sndarray.make_sound(stereo)
            self._music_channel = pygame.mixer.Channel(0)
            self._music_channel.set_volume(0.0 if self.muted else volume)
            self._music_channel.play(self._music_sound, loops=-1)
            self._music_volume = volume
        except (pygame.error, AttributeError):
            pass

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        try:
            ch = getattr(self, "_music_channel", None)
            if ch is not None:
                ch.set_volume(0.0 if muted else getattr(self, "_music_volume", 0.45))
        except pygame.error:
            pass

    def toggle_mute(self) -> bool:
        self.set_muted(not self.muted)
        return self.muted
