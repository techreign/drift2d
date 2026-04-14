"""Drift Pokemon — a Pokemon-style RPG built with Drift2D."""

import sys
from pathlib import Path

engine_src = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(engine_src))
sys.path.insert(0, str(Path(__file__).parent))

from drift2d import Game
from scenes.title import TitleScene

game = Game.from_project(".")
game.scenes.register("title", TitleScene())
game.run("title")
