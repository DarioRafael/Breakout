# Persistent high-score (JSON file next to this script).
from __future__ import annotations

import json
import os

import config as C

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), C.HIGHSCORE_FILE)


def load_highscore() -> int:
    try:
        with open(_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return int(data.get("highscore", 0))
    except (OSError, ValueError, TypeError):
        return 0


def save_highscore(score: int) -> bool:
    try:
        with open(_PATH, "w", encoding="utf-8") as fh:
            json.dump({"highscore": int(score)}, fh)
        return True
    except OSError:
        return False
