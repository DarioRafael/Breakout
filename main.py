# Entry point.
# Usage:
#   python main.py             # play
#   python main.py --selftest  # headless verification
from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Breakout — Neon Pixel Edition")
    parser.add_argument("--selftest", action="store_true",
                        help="run a headless self-test and exit")
    parser.add_argument("--quiet", action="store_true",
                        help="less verbose self-test output")
    args = parser.parse_args(argv)

    from game import Game

    if args.selftest:
        game = Game(headless=True)
        try:
            game.run_selftest(verbose=not args.quiet)
        finally:
            import pygame
            pygame.quit()
        return 0

    Game(headless=False).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
